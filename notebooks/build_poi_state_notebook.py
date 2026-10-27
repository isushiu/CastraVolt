"""Build the standalone Colab notebook from the established experiment cells."""
import hashlib
import json
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'ML Data'
provenance = ROOT / 'data' / 'updated_mevnet_source' / 'training_row_provenance_1km.csv'
groups = DATA_DIR / 'updated_mevnet_row_groups.csv'
shutil.copyfile(provenance, groups)
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA_DIR / 'updated_mevnet.csv', groups]}
original = json.loads((ROOT / 'notebooks' / 'CastraVolt_ML_Training.ipynb').read_text(encoding='utf-8'))
cells = []


def md(value):
    cells.append({'cell_type':'markdown', 'metadata':{}, 'source':textwrap.dedent(value).strip().splitlines(True)})


def code(value):
    cells.append({'cell_type':'code', 'metadata':{}, 'execution_count':None, 'outputs':[],
                  'source':textwrap.dedent(value).strip().splitlines(True)})


def old(index):
    return ''.join(original['cells'][index]['source'])


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f'Original notebook has changed: {before!r}')
    return source.replace(before, after)


md('''
# CastraVolt ML: 1 km POIs + site category + state

Run the cells in order in Google Colab. Upload **two CSV files** from `data/ML Data` together:

1. `updated_mevnet.csv` — the cleaned site data, 1 km POI counts and target.
2. `updated_mevnet_row_groups.csv` — the matching site coordinates used only to keep the same location together during splitting.

**Inputs:** eight nearby POI counts, host-site category and state. EV registrations are **not** a model input. The target is `total_planned_chargers` = existing + proposed, using the project's assumption that proposed means additional chargers. This assumption has not been independently verified. The model learns MEVnet's proposed totals, not independently proven optimal demand.

Some categories are inferred from map/site information and three sites are Unknown. The data uses the project's 25 October 2026 OSM snapshot and 1 km extraction rules. OSM completeness and inferred labels can affect results. Nearby sites may share facilities even when identical coordinates are kept together.

The default `smoke` run tests the workflow quickly. Set `RUN_MODE = 'full'` for the 11 agreed experiments and 30-candidate searches. Full tuning can take substantial time in Colab. The results from the 11 overlapping experiments are exploratory, not a fresh final test.
''')
code(old(1))
md('''
## 1. Settings and file upload

Select both CSVs together when prompted. Colab's automatic `(1)` suffix on a repeated upload is handled. For Drive, set `DATA_SOURCE = 'drive'` and update `DATA_DIR`. For local execution choose `local`. The files are checked against the prepared matching pair; use the exact versions in the project folder so row groups cannot silently attach to the wrong sites.
''')
code('''
SEED = 42
DATA_SOURCE = 'upload'  # upload | drive | local
DATA_DIR = Path('/content/drive/MyDrive/CastraVolt/data/ML Data')
RUN_MODE = 'smoke'  # Change to 'full' for actual experiments.
MIN_DISPLAY_COUNT = 1
N_SEARCH = 30
SEARCH_JOBS = -1
REFIT_MODEL_NAME = 'RandomForest'  # explicit, not selected from test scores
REFIT_PARAMS = None  # optional parameters chosen using training CV
OUTPUT_DIR = Path('castravolt_poi_category_state_results')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FILES = ['updated_mevnet.csv', 'updated_mevnet_row_groups.csv']
EXPECTED_HASHES = __HASHES__
POI = ['nearby_mall_count', 'nearby_petrol_count', 'nearby_hotel_count',
       'nearby_office_count', 'nearby_transit_count', 'nearby_university_count',
       'nearby_hospital_count', 'nearby_parking_count']
TARGET = 'total_planned_chargers'
assert RUN_MODE in {'smoke', 'full'}
'''.replace('__HASHES__', repr(hashes)))
code('''
if DATA_SOURCE == 'upload':
    from google.colab import files
    import re
    uploaded = files.upload()
    DATA_DIR = Path('/content/castravolt_poi_input')
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        matches = [key for key in uploaded if re.sub(r' \\(\\d+\\)(?=\\.csv$)', '', Path(key).name) == name]
        if len(matches) != 1:
            raise ValueError(f'Upload exactly one copy of each required CSV. Problem with {name}: {matches}')
        (DATA_DIR / name).write_bytes(uploaded[matches[0]])
elif DATA_SOURCE == 'drive':
    from google.colab import drive
    drive.mount('/content/drive')
elif DATA_SOURCE == 'local':
    DATA_DIR = Path('data/ML Data') if Path('data/ML Data').exists() else Path('../data/ML Data')
else:
    raise ValueError('Choose upload, drive, or local')
source_hashes = {}
for name in FILES:
    path = DATA_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f'Missing {path}. Upload both required CSVs.')
    source_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if source_hashes[name] != EXPECTED_HASHES[name]:
        raise ValueError(f'{name} differs from the matching dataset version. Use the two supplied files together.')
raw = pd.read_csv(DATA_DIR / FILES[0])
row_groups = pd.read_csv(DATA_DIR / FILES[1])
print('Loaded sites:', len(raw), '| Coordinate records:', len(row_groups))
''')
md('''
## 2. Audit and clean data

Inspect missing, unique and constant values. The prepared total is read directly; its components remain in the source audit rather than becoming features. Invalid targets or unsupported states are excluded and exported with reasons; invalid POI values become missing and are imputed **inside training folds**. Missing site category becomes `Unknown`. Do not delete sites merely because their model inputs happen to be identical. Coordinates and identifiers are for audit/splitting, never prediction features.
''')
code('''
def column_audit(frame, source):
    return pd.DataFrame({'source':source, 'column':frame.columns, 'dtype':frame.dtypes.astype(str).values,
                         'missing':frame.isna().sum().values,
                         'unique_nonmissing':frame.nunique(dropna=True).values,
                         'constant':frame.nunique(dropna=False).le(1).values})
column_audit(raw, FILES[0]).to_csv(OUTPUT_DIR / 'source_column_audit.csv', index=False)
display(column_audit(raw, FILES[0]))
required = set(POI + ['category', 'state', TARGET])
if not required.issubset(raw.columns):
    raise ValueError(f'Missing required columns: {sorted(required - set(raw.columns))}')
if not {'training_row','objectid','latitude','longitude','coordinate_group'}.issubset(row_groups.columns):
    raise ValueError('The coordinate provenance file has missing fields.')
if len(raw) != len(row_groups) or row_groups['training_row'].tolist() != list(range(len(raw))):
    raise ValueError('Site data and row-group provenance are not aligned.')
lat = pd.to_numeric(row_groups['latitude'], errors='coerce')
lon = pd.to_numeric(row_groups['longitude'], errors='coerce')
if not (lat.between(-90,90) & lon.between(-180,180)).all():
    raise ValueError('Invalid coordinates in row-group provenance.')
expected_groups = [f'{a:.7f}|{b:.7f}' for a,b in zip(lat,lon)]
if expected_groups != row_groups['coordinate_group'].tolist():
    raise ValueError('Coordinate group values do not match the supplied coordinates.')
sites = raw.copy()
sites['_source_row'] = np.arange(len(sites))
sites['_coordinate_group'] = row_groups['coordinate_group'].to_numpy()
for col in POI + [TARGET]:
    sites[col] = pd.to_numeric(sites[col], errors='coerce').replace([np.inf,-np.inf], np.nan)
for col in ['category','state']:
    sites[col] = sites[col].astype('string').str.strip().replace('', pd.NA)
sites['state'] = sites['state'].str.upper()
sites['category'] = sites['category'].fillna('Unknown')
bad_target = sites[TARGET].isna() | sites[TARGET].le(0) | sites[TARGET].mod(1).ne(0)
bad_state = ~sites['state'].isin(['SELANGOR','W.P. KUALA LUMPUR'])
excluded = sites.loc[bad_target | bad_state].copy()
excluded['invalid_target'] = bad_target[bad_target | bad_state]
excluded['invalid_state'] = bad_state[bad_target | bad_state]
excluded.to_csv(OUTPUT_DIR / 'excluded_site_rows.csv', index=False)
sites = sites.loc[~(bad_target | bad_state)].copy().reset_index(drop=True)
for col in POI:
    invalid = sites[col].lt(0) | sites[col].mod(1).ne(0)
    sites.loc[invalid, col] = np.nan
numeric_features = POI.copy()
categorical_features = ['category', 'state']
features = numeric_features + categorical_features
X, y = sites[features].copy(), sites[TARGET].astype(int).copy()
coordinate_groups = sites['_coordinate_group'].to_numpy()
if len(sites) < 20:
    raise ValueError('Not enough valid sites for the 10-fold experiments.')
sites.to_csv(OUTPUT_DIR / 'prepared_sites.csv', index=False)
column_audit(sites, 'prepared_sites').to_csv(OUTPUT_DIR / 'prepared_column_audit.csv', index=False)
print('Prepared sites:', len(sites), '| Coordinate groups:', len(set(coordinate_groups)))
print('Model features:', features)
print('Unknown categories:', int(sites['category'].eq('Unknown').sum()))
print('EV registrations are excluded from X.')
''')
md('''
## 3. Splits and models

Use seed 42. Random splits are approximately 50/50, 70/30 and 80/20. Exactly co-located sites stay in one group. This does not prevent nearby locations from sharing POIs across a split. Preprocessing is fitted within each training fold. Both models and the always-three and training-median baselines use the same evaluation rows.
''')
code(old(10))
models = old(11)
models = replace_once(models, 'np.ceil(np.asarray(pred))', 'np.floor(np.asarray(pred) + 0.5)')
models = models.replace('ceil_MAE', 'rounded_MAE')
code(models)
md('''
## 4. Run the 11 agreed experiments

Three split-only setups, two CV-only setups (5 and 10 folds), and six split-plus-CV setups. In split-plus-CV, tuning occurs only on the training portion. Full mode evaluates 30 sampled settings per model and setup. The MAE/RMSE/R² use raw predictions; rounded MAE uses nearest integer, halves upward, minimum one. CV standard deviation is variation across folds, not a confidence interval.
''')
experiment = old(13)
experiment = replace_once(experiment, "run_label = 'PROVISIONAL_' + RUN_MODE + ('_adoption' if USE_ADOPTION else '_no_adoption')",
                          "run_label = 'poi_category_state_1km_' + RUN_MODE")
experiment = experiment.replace('ceil_MAE', 'rounded_MAE')
code(experiment)
md('''
## 5. Charts, model candidate and results

The graph compares models and baselines on the same 80/20 split and shows the Random Forest's displayed prediction distribution against the actual targets. This helps spot repeated outputs, but it is not proof of accuracy at unseen locations. The saved candidate is refitted on all cleaned sites with the explicitly configured model and parameters; it is not a fresh independent test. Smoke candidates are only for workflow testing. No app model is replaced here.
''')
code('''
view = scores[scores['experiment']=='split_only_80_none']
predictions = pd.DataFrame(prediction_rows)
rf_predictions = predictions[(predictions['experiment']=='split_only_80_none') & (predictions['model']=='RandomForest')]
fig, axes = plt.subplots(1,2,figsize=(14,5))
axes[0].bar(view['model'],view['MAE'])
axes[0].set(title='80/20 split: raw MAE (lower is better)',xlabel='Model or baseline',ylabel='MAE (charging points)')
axes[0].tick_params(axis='x',rotation=25)
axes[1].hist([rf_predictions['actual'],rf_predictions['displayed_count']],bins=np.arange(0, max(25, int(rf_predictions['actual'].max())+2)),
             label=['Actual MEVnet total','Random Forest rounded prediction'],alpha=.6)
axes[1].set(title='80/20 split: actual vs predicted counts',xlabel='Total charging points',ylabel='Sites')
axes[1].legend(); fig.tight_layout(); fig.savefig(run_dir/'overview.png',dpi=160); plt.show()
metadata = {'run_mode':RUN_MODE,'seed':SEED,'target':TARGET,'target_formula':'existing + proposed',
 'target_assumption':'proposed means additional chargers; not independently verified',
 'features':features,'use_adoption':False,'source_hashes':source_hashes,
 'poi_radius_metres':1000,'poi_snapshot_date':'2026-10-25','split_method':'random coordinate groups',
 'minimum_display_count':MIN_DISPLAY_COUNT,'rounding':'nearest_half_up',
 'fixed_random_forest':FIXED_RF,'fixed_xgboost':FIXED_XGB,
 'versions':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,
             'sklearn':sklearn.__version__,'xgboost':xgboost.__version__},
 'limitations':['inferred host-site categories','target meaning is an assumption',
                'nearby sites can share POIs','11 experiments reuse test records',
                'app currently uses a different radius and model']}
(run_dir/'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
candidate = build_model(REFIT_MODEL_NAME)
if REFIT_PARAMS is not None: candidate.set_params(**REFIT_PARAMS)
candidate.fit(X,y)
joblib.dump({'pipeline':candidate,'features':features,'metadata':metadata},run_dir/'candidate_model.joblib')
print('Saved a candidate model; its full-data refit has no independent test score.')
for diagnostic in OUTPUT_DIR.glob('*.csv'):
    shutil.copy2(diagnostic,run_dir/diagnostic.name)
archive = shutil.make_archive(str(run_dir),'zip',root_dir=OUTPUT_DIR,base_dir=run_dir.name)
print('Results archive:',archive)
''')
md('''
## 6. Test a prepared site

Enter the eight genuine 1 km POI counts, the confirmed host-site category, and state. This function does not fetch POIs or receive EV registrations. A new app model requires separately updating its 3 km feature preparation to 1 km and verifying compatibility. Never load an untrusted joblib file.
''')
code('''
def predict_prepared_site(feature_values):
    if set(feature_values) != set(features):
        raise ValueError(f'Provide exactly these inputs: {features}')
    frame = pd.DataFrame([feature_values])[features]
    for col in numeric_features:
        frame[col] = pd.to_numeric(frame[col],errors='raise')
        if frame[col].isna().any() or frame[col].lt(0).any() or frame[col].mod(1).ne(0).any():
            raise ValueError(f'Invalid POI count: {col}')
    if frame['state'].iloc[0] not in {'SELANGOR','W.P. KUALA LUMPUR'}:
        raise ValueError('Unsupported state')
    prediction = float(candidate.predict(frame)[0])
    return {'raw_estimate':prediction,'total_planned_chargers':int(displayed_count([prediction])[0]),
            'run_mode':RUN_MODE}

# Download results in Colab after the run:
# from google.colab import files
# files.download(archive)
''')

notebook = {'nbformat':4, 'nbformat_minor':5,
            'metadata':{'colab':{'name':'CastraVolt_POI_Category_State.ipynb','provenance':[]},
                        'kernelspec':{'name':'python3','display_name':'Python 3'},
                        'language_info':{'name':'python','version':'3.11'}}, 'cells':cells}
for i, cell in enumerate(cells):
    cell['id'] = f'poi-state-{i:03}'
destination = ROOT / 'notebooks' / 'CastraVolt_POI_Category_State.ipynb'
destination.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding='utf-8')
print(destination)
