"""Build the self-contained Colab notebook using standard-library JSON."""
import json
import textwrap
from pathlib import Path

cells = []
def md(s):
    cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': textwrap.dedent(s).strip().splitlines(True)})
def code(s):
    cells.append({'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                  'source': textwrap.dedent(s).strip().splitlines(True)})

md('''
# CastraVolt: site charging-point capacity experiments

Run cells in order in Google Colab (CPU is sufficient). This notebook uses the four files in **data/ML Data**. Upload them together or mount Google Drive. It does not fetch new POIs from OpenStreetMap.

**Target assumption:** total planned points = existing + proposed, interpreting proposed as outstanding additions as authorised by the project owner. MEVnet field labels alone do not verify this interpretation. These experiments predict this constructed planning target, not observed optimal demand or waiting times.

**Data limitations:** the current POI extraction provenance is unknown. Configuring a 1 km radius does not retroactively establish how the supplied counts were collected. Regenerate or verify extraction before final claims. State registrations are new registrations, not fleet stock; excluding Rakan Niaga limits coverage.

The default run is a small smoke test. Change RUN_MODE to `full` for the agreed 11 setups and 30-combination tuning. A full run can take substantial time. Outputs are saved after each completed experiment.
''')
code('''
import sys, subprocess, importlib.util
# Install into the active Colab runtime only when required; source files are never edited.
packages = {'pandas': 'pandas>=2.2,<4', 'numpy': 'numpy>=1.26,<3',
            'sklearn': 'scikit-learn>=1.4,<2', 'xgboost': 'xgboost>=2,<4',
            'matplotlib': 'matplotlib>=3.8,<4', 'joblib': 'joblib>=1.3,<2'}
missing = [package for module, package in packages.items() if importlib.util.find_spec(module) is None]
if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *missing])
import json, hashlib, platform, warnings, time, shutil
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sklearn, xgboost, joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_selection import VarianceThreshold
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
from IPython.display import display
''')
md('''
## 1. Configuration

`upload`: select all four CSVs from ML Data. `drive`: set DATA_DIR to the actual Drive folder. `local`: use the repository folder when running locally.

Adoption is off by default until an indicator/year match is justified. Optional `fixed_period_context` repeats one selected year's state total for all sites; it is explicitly a retrospective context experiment, not historical evidence of adoption's effect. Optional `prior_calendar_year` uses the complete preceding year's registrations, only if `data_as` can defensibly represent proposal timing. Missing historical coverage causes an error, not invented zero adoption.

The agreed 1 km rules and facility deduplication must be used when regenerating POIs. Missing category becomes Unknown. Other missing feature values are imputed inside training folds. Constant features are removed inside folds. IDs and direct charger-count components are excluded explicitly, rather than indiscriminately dropping every unique-valued column.
''')
code('''
SEED = 42
DATA_SOURCE = 'upload'  # upload | drive | local
DATA_DIR = Path('/content/drive/MyDrive/CastraVolt/data/ML Data')
RUN_MODE = 'smoke'  # smoke | full
ALLOW_PROVISIONAL_POI = True  # True permits an exploratory run with an explicit warning
POI_RADIUS_METRES = 1000  # agreed future extraction; NOT verified provenance for supplied CSV
USE_ADOPTION = False
ADOPTION_MODE = 'fixed_period_context'  # fixed_period_context | prior_calendar_year
ADOPTION_REFERENCE_YEAR = 2025
MIN_DISPLAY_COUNT = 1  # configurable recommended default; not an agreed scientific threshold
N_SEARCH = 30
SEARCH_JOBS = -1
REFIT_MODEL_NAME = 'RandomForest'  # predefined; do not silently choose by best test score
REFIT_PARAMS = None  # optionally paste training-CV-selected model__ parameters here
OUTPUT_DIR = Path('castravolt_results')
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
FILES = ['mevnet_ev_charging_demand_labelled_dataset.csv',
         'ev_registration2024.csv', 'ev_registration2025.csv', 'vehicles_2026.csv']
POI = ['nearby_mall_count', 'nearby_petrol_count', 'nearby_hotel_count',
       'nearby_office_count', 'nearby_transit_count', 'nearby_university_count',
       'nearby_hospital_count', 'nearby_parking_count']
TARGET = 'total_planned_chargers'
EXISTING = 'number_of_existing_ev_charger_s'
PROPOSED = 'number_of_proposed_ev_charger__'
assert RUN_MODE in {'smoke', 'full'}
assert MIN_DISPLAY_COUNT >= 0
''')
code('''
if DATA_SOURCE == 'upload':
    from google.colab import files
    import re
    uploaded = files.upload()
    DATA_DIR = Path('/content/castravolt_input')
    DATA_DIR.mkdir(exist_ok=True)
    for name in FILES:
        # Colab can return renamed keys on repeated uploads: filename (3).csv.
        matches = [key for key in uploaded if
                   re.sub(r' \\(\\d+\\)(?=\\.csv$)', '', Path(key).name) == name]
        if not matches:
            raise FileNotFoundError(f'Upload all four required CSVs. Missing: {name}')
        if len(matches) != 1:
            raise ValueError(f'Multiple uploads match {name}: {matches}. Select one copy of each file.')
        (DATA_DIR / name).write_bytes(uploaded[matches[0]])
elif DATA_SOURCE == 'drive':
    from google.colab import drive
    drive.mount('/content/drive')
elif DATA_SOURCE == 'local':
    DATA_DIR = Path('data/ML Data') if Path('data/ML Data').exists() else Path('../data/ML Data')
else:
    raise ValueError('Choose upload, drive, or local')
for name in FILES:
    if not (DATA_DIR / name).is_file():
        raise FileNotFoundError(DATA_DIR / name)
source_hashes = {name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest() for name in FILES}
raw = pd.read_csv(DATA_DIR / FILES[0])
registrations = {year: pd.read_csv(DATA_DIR / name) for year, name in zip([2024, 2025, 2026], FILES[1:])}
print('Loaded sites:', len(raw))
print('Registration rows:', {year: len(frame) for year, frame in registrations.items()})
''')
md('## 2. Audit sources and prepare registration summaries')
code('''
def column_audit(frame, source):
    return pd.DataFrame({'source': source, 'column': frame.columns,
                         'dtype': frame.dtypes.astype(str).values,
                         'missing': frame.isna().sum().values,
                         'unique_nonmissing': frame.nunique(dropna=True).values})
audit = pd.concat([column_audit(raw, FILES[0])] +
                  [column_audit(frame, str(year)) for year, frame in registrations.items()], ignore_index=True)
audit.to_csv(OUTPUT_DIR / 'source_column_audit.csv', index=False)
display(audit[audit['source'] == FILES[0]])
monthly_parts, annual_parts, coverage_parts = [], [], []
for year, frame in registrations.items():
    required = {'date_reg', 'type', 'fuel', 'state'}
    if not required.issubset(frame.columns):
        raise ValueError(f'{year}: missing registration columns')
    # Preserve repeated rows: these can represent different vehicles.
    frame = frame.copy()
    date_text = frame['date_reg'].astype('string').str.strip()
    iso = date_text.str.match(r'^\\d{4}-\\d{2}-\\d{2}$').fillna(False)
    frame['date'] = pd.to_datetime(date_text.where(iso), format='%Y-%m-%d', errors='coerce')
    frame.loc[~iso,'date'] = pd.to_datetime(date_text[~iso], format='%d/%m/%Y', errors='coerce')
    if frame['date'].isna().any() or not frame['date'].dt.year.eq(year).all():
        raise ValueError(f'{year}: invalid dates or wrong-year records')
    if not (frame['fuel'].eq('electric') & frame['type'].eq('motokar') &
            frame['state'].isin(['Selangor', 'W.P. Kuala Lumpur'])).all():
        raise ValueError(f'{year}: input is not the agreed filtered electric-motokar dataset')
    if 'category' in frame and not frame['category'].eq('car').all():
        raise ValueError('2026 input contains non-car categories')
    frame['state'] = frame['state'].str.upper()
    frame['month'] = frame['date'].dt.to_period('M').astype(str)
    end_month = 9 if year == 2026 else 12
    if frame['date'].max().month > end_month:
        raise ValueError('Source coverage changed: update coverage assumptions explicitly')
    index = pd.MultiIndex.from_product([['SELANGOR', 'W.P. KUALA LUMPUR'],
             pd.period_range(f'{year}-01', f'{year}-{end_month:02}', freq='M').astype(str)], names=['state','month'])
    monthly = frame.groupby(['state','month']).size().reindex(index, fill_value=0).rename('new_registrations').reset_index()
    monthly_parts.append(monthly)
    annual = frame.groupby('state').size().rename('new_registrations').reset_index()
    annual['year'], annual['months_covered'] = year, end_month
    annual_parts.append(annual)
    coverage_parts.append({'year': year, 'first_record': str(frame['date'].min().date()),
                           'last_record': str(frame['date'].max().date()), 'months_covered': end_month,
                           'repeated_rows_retained': int(frame.duplicated(subset=list(required)).sum())})
monthly_registration = pd.concat(monthly_parts, ignore_index=True)
annual_registration = pd.concat(annual_parts, ignore_index=True)
monthly_registration.to_csv(OUTPUT_DIR / 'monthly_ev_registrations.csv', index=False)
annual_registration.to_csv(OUTPUT_DIR / 'annual_ev_registrations.csv', index=False)
pd.DataFrame(coverage_parts).to_csv(OUTPUT_DIR / 'registration_coverage.csv', index=False)
display(annual_registration)
print('2026 is January–September only. Excluded Rakan Niaga records are not represented.')
''')
md('''
## 3. Clean sites and build the feature matrix

Blank/constant columns are audited; model features are explicitly allowlisted. Missing target components or invalid coordinates are excluded with reasons. Exact repeated site rows are removed; distinct facilities at identical coordinates are retained and grouped during evaluation. No POI outliers are deleted merely because their counts are large.
''')
code('''
required = set(POI + ['latitude', 'longitude', 'state', 'category', EXISTING, PROPOSED])
if not required.issubset(raw.columns):
    raise ValueError(f'Missing site columns: {sorted(required - set(raw.columns))}')
if not ALLOW_PROVISIONAL_POI:
    raise ValueError('Verify/regenerate POIs using documented 1 km rules, then explicitly enable this run.')
warnings.warn('PROVISIONAL: supplied POI radius/tags/deduplication have not been verified. No final spatial claims.')
sites = raw.copy()
sites['_source_row'] = np.arange(len(sites))
for col in POI + ['latitude','longitude',EXISTING,PROPOSED]:
    sites[col] = pd.to_numeric(sites[col], errors='coerce').replace([np.inf,-np.inf], np.nan)
for col in ['state','category']:
    sites[col] = sites[col].astype('string').str.strip().replace('', pd.NA)
sites['state'] = sites['state'].str.upper()
sites['category'] = sites['category'].fillna('Unknown')
invalid_target = sites[[EXISTING,PROPOSED]].isna().any(axis=1)
for col in [EXISTING,PROPOSED]:
    invalid_target |= sites[col].lt(0) | sites[col].mod(1).ne(0)
invalid_location = ~sites['latitude'].between(-90,90) | ~sites['longitude'].between(-180,180)
invalid_state = ~sites['state'].isin(['SELANGOR','W.P. KUALA LUMPUR'])
invalid = invalid_target | invalid_location | invalid_state
excluded = sites.loc[invalid].copy()
excluded['invalid_target'] = invalid_target[invalid]
excluded['invalid_location'] = invalid_location[invalid]
excluded['invalid_state'] = invalid_state[invalid]
excluded.to_csv(OUTPUT_DIR / 'excluded_site_rows.csv', index=False)
sites = sites.loc[~invalid].copy()
duplicate = sites.duplicated(subset=[col for col in raw.columns if col != TARGET])
sites.loc[duplicate].to_csv(OUTPUT_DIR / 'exact_duplicate_sites_removed.csv', index=False)
sites = sites.loc[~duplicate].reset_index(drop=True)
computed = sites[EXISTING] + sites[PROPOSED]
if TARGET in sites:
    supplied = pd.to_numeric(sites[TARGET], errors='coerce')
    if not np.allclose(supplied, computed, equal_nan=False):
        raise ValueError('Saved total target disagrees with existing + proposed; investigate before training')
sites[TARGET] = computed.astype(int)
for col in POI:
    # Invalid negative/noninteger counts become missing, not silently rounded.
    bad = sites[col].lt(0) | sites[col].mod(1).ne(0)
    sites.loc[bad, col] = np.nan
sites['_coordinate_group'] = (sites['latitude'].round(7).astype(str) + '|' + sites['longitude'].round(7).astype(str))
numeric_features = POI.copy()
categorical_features = ['category','state']
adoption_lookup = annual_registration.set_index(['state','year'])['new_registrations'].to_dict()
if USE_ADOPTION:
    if ADOPTION_MODE == 'fixed_period_context':
        warnings.warn('Fixed-period adoption is retrospective state context; two state values do not identify growth effects.')
        years = pd.Series(ADOPTION_REFERENCE_YEAR, index=sites.index)
    elif ADOPTION_MODE == 'prior_calendar_year':
        if 'data_as' not in sites:
            raise ValueError('Date-aligned adoption needs data_as and a justified proposal-date interpretation')
        dates = pd.to_datetime(sites['data_as'], format='mixed', dayfirst=True, errors='coerce')
        years = dates.dt.year - 1
        if dates.isna().any():
            raise ValueError('Cannot align registration periods to invalid site dates')
    else:
        raise ValueError('Unknown adoption mode')
    if years.eq(2026).any():
        raise ValueError('2026 is partial-year; do not use as a complete calendar-year feature')
    sites['state_ev_registrations'] = [adoption_lookup.get((state,int(year)), np.nan) for state,year in zip(sites['state'],years)]
    if sites['state_ev_registrations'].isna().any():
        raise ValueError('Missing registration-year coverage. Supply historical data or disable adoption; do not invent zeros.')
    numeric_features.append('state_ev_registrations')
features = numeric_features + categorical_features
X = sites[features].copy()
y = sites[TARGET].copy()
coordinate_groups = sites['_coordinate_group'].to_numpy()
sites.to_csv(OUTPUT_DIR / 'prepared_sites.csv', index=False)
column_audit(sites, 'prepared_sites').to_csv(OUTPUT_DIR / 'prepared_column_audit.csv', index=False)
print('Prepared sites:',len(sites),'coordinate groups:',len(set(coordinate_groups)))
print('Features:', features)
print('Target range:', int(y.min()), int(y.max()))
''')
md('''
## 4. Random splits that keep identical coordinates together

This is random coordinate-group allocation, not geographical grid evaluation. Nearby distinct sites can still overlap. Fold assignments are saved. Ratios are approximate because colocated records must remain together. CV-only uses fixed settings; split-plus-CV tunes only inside training data.
''')
code('''
def random_group_folds(groups, n_splits, seed=SEED):
    groups = np.asarray(groups)
    unique, counts = np.unique(groups, return_counts=True)
    if len(unique) < n_splits:
        raise ValueError(f'Need at least {n_splits} coordinate groups')
    order = np.random.default_rng(seed).permutation(len(unique))
    # Shuffle ties and balance by site count without inspecting target values.
    order = sorted(order, key=lambda i: -counts[i])
    assigned, loads = {}, np.zeros(n_splits, dtype=int)
    for i in order:
        fold = int(np.argmin(loads)); assigned[unique[i]] = fold; loads[fold] += counts[i]
    fold_ids = np.array([assigned[g] for g in groups])
    return [(np.flatnonzero(fold_ids != k), np.flatnonzero(fold_ids == k)) for k in range(n_splits)]

def random_group_holdout(groups, fraction, seed=SEED):
    groups = np.asarray(groups)
    unique, counts = np.unique(groups, return_counts=True)
    if len(unique) < 2:
        raise ValueError('Need at least two coordinate groups')
    order = np.random.default_rng(seed).permutation(len(unique))
    cutoff = int(np.argmin(np.abs(np.cumsum(counts[order])[:-1] - fraction * len(groups)))) + 1
    test_groups = unique[order[:cutoff]]
    mask = np.isin(groups, test_groups)
    return np.flatnonzero(~mask), np.flatnonzero(mask)

def assert_disjoint(train, test, groups):
    assert not set(np.asarray(groups)[train]) & set(np.asarray(groups)[test])

holdouts = {ratio: random_group_holdout(coordinate_groups, 1-ratio) for ratio in [0.5,0.7,0.8]}
assignments = []
for ratio,(train,test) in holdouts.items():
    assert_disjoint(train,test,coordinate_groups)
    for partition,indices in [('train',train),('test',test)]:
        for i in indices:
            assignments.append({'train_fraction':ratio,'source_row':int(sites.iloc[i]['_source_row']),
                                'coordinate_group':coordinate_groups[i], 'partition':partition})
pd.DataFrame(assignments).to_csv(OUTPUT_DIR / 'holdout_assignments.csv', index=False)
print({ratio: {'train':len(t),'test':len(v)} for ratio,(t,v) in holdouts.items()})
''')
code('''
def preprocessing():
    numeric = Pipeline([('impute', SimpleImputer(strategy='median', keep_empty_features=True))])
    categorical = Pipeline([('impute',SimpleImputer(strategy='constant', fill_value='Unknown')),
                           ('encode',OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    return Pipeline([('columns',ColumnTransformer([('numeric',numeric,numeric_features),
                                                   ('categorical',categorical,categorical_features)])),
                     ('remove_constants',VarianceThreshold())])

# Explicit fixed configurations for split-only and CV-only experiments.
# These are implementation defaults within the approved ranges, not tuned optimal settings.
FIXED_RF = dict(n_estimators=300, max_depth=10, min_samples_leaf=2, max_features=1.0)
FIXED_XGB = dict(n_estimators=300, max_depth=3, learning_rate=0.05,
                 subsample=0.8, colsample_bytree=0.8, reg_lambda=1)
SEARCH_SPACES = {
    'RandomForest': {'model__n_estimators':[300,600], 'model__max_depth':[5,10,None],
                     'model__min_samples_leaf':[2,5,10], 'model__max_features':['sqrt',1.0]},
    'XGBoost': {'model__n_estimators':[100,300,600], 'model__max_depth':[2,3,5],
                'model__learning_rate':[0.03,0.05,0.1], 'model__subsample':[0.8,1.0],
                'model__colsample_bytree':[0.8,1.0], 'model__reg_lambda':[1,5]}}
def build_model(name):
    if name == 'RandomForest':
        params = FIXED_RF.copy()
        if RUN_MODE == 'smoke': params.update(n_estimators=12, max_depth=3)
        model = RandomForestRegressor(**params, random_state=SEED, n_jobs=1)
    elif name == 'XGBoost':
        params = FIXED_XGB.copy()
        if RUN_MODE == 'smoke': params.update(n_estimators=12,max_depth=2)
        model = XGBRegressor(**params, objective='reg:squarederror', random_state=SEED, n_jobs=1, tree_method='hist')
    else:
        raise ValueError(name)
    return Pipeline([('preprocess',preprocessing()), ('model',model)])

def displayed_count(pred):
    return np.maximum(MIN_DISPLAY_COUNT, np.ceil(np.asarray(pred))).astype(int)

def metrics(actual, pred):
    pred = np.asarray(pred)
    return {'MAE':float(mean_absolute_error(actual,pred)),
            'RMSE':float(np.sqrt(mean_squared_error(actual,pred))),
            'R2':float(r2_score(actual,pred)) if len(actual)>1 else float('nan'),
            'ceil_MAE':float(mean_absolute_error(actual,displayed_count(pred)))}
''')
md('''
## 5. Execute the 11 setups

Both baselines are evaluated on exactly the same held-out rows as the models. The median baseline uses only the corresponding training portion. CV fold standard deviations describe fold variation, not confidence intervals.

Full mode runs 3 split-only + 2 CV-only + 6 split-plus-CV setups for each model. All setups run in smoke mode too, with tiny tree counts and two tuning candidates to verify the workflow. Smoke results must not be used as FYP findings. The 11-way comparison reuses records across experiments: do not select the luckiest test split or claim a fresh unbiased final test after choosing by these results.
''')
code('''
run_label = 'PROVISIONAL_' + RUN_MODE + ('_adoption' if USE_ADOPTION else '_no_adoption')
run_dir = OUTPUT_DIR / run_label
run_dir.mkdir(exist_ok=True)
experiments = [('split_only',r,None) for r in [0.5,0.7,0.8]] + [('cv_only',None,k) for k in [5,10]] + [('split_cv',r,k) for r in [0.5,0.7,0.8] for k in [5,10]]
score_rows, prediction_rows, selected_rows, fold_assignments = [], [], [], []

def record_result(exp, name, actual, pred, test_idx, n_train, fold=None, evaluation='holdout'):
    values = metrics(actual,pred)
    score_rows.append(dict(experiment=exp,model=name,fold=fold,evaluation=evaluation,
                           n_train=n_train,n_test=len(test_idx),**values))
    for i,a,p in zip(test_idx,actual,pred):
        prediction_rows.append({'experiment':exp,'model':name,'fold':fold,'evaluation':evaluation,
             'source_row':int(sites.iloc[i]['_source_row']),'actual':int(a),
             'raw_prediction':float(p),'displayed_count':int(displayed_count([p])[0])})

def save_progress():
    pd.DataFrame(score_rows).to_csv(run_dir/'evaluation_scores.csv',index=False)
    pd.DataFrame(prediction_rows).to_csv(run_dir/'holdout_predictions.csv',index=False)
    pd.DataFrame(selected_rows).to_csv(run_dir/'selected_hyperparameters.csv',index=False)
    pd.DataFrame(fold_assignments).to_csv(run_dir/'cv_assignments.csv',index=False)

start = time.time()
for kind, ratio, k in experiments:
    exp = f'{kind}_{int(ratio*100) if ratio else "all"}_{k or "none"}'
    print('Running',exp,flush=True)
    if kind == 'cv_only':
        outer = random_group_folds(coordinate_groups,k)
    else:
        outer = [holdouts[ratio]]
    for fold,(train,test) in enumerate(outer):
        assert_disjoint(train,test,coordinate_groups)
        for i in test:
            fold_assignments.append({'experiment':exp,'stage':'evaluation','fold':fold,
                                     'source_row':int(sites.iloc[i]['_source_row'])})
        cv = None
        if kind == 'split_cv':
            cv = random_group_folds(coordinate_groups[train],k)
            for inner,(it,iv) in enumerate(cv):
                assert_disjoint(it,iv,coordinate_groups[train])
                for i in train[iv]:
                    fold_assignments.append({'experiment':exp,'stage':'tuning','fold':inner,
                                             'source_row':int(sites.iloc[i]['_source_row'])})
        for name in ['RandomForest','XGBoost']:
            estimator = build_model(name)
            if cv is not None:
                space = SEARCH_SPACES[name]
                if RUN_MODE == 'smoke':
                    space = {'model__n_estimators':[8,12], 'model__max_depth':[2]}
                search = RandomizedSearchCV(estimator,space,n_iter=2 if RUN_MODE=='smoke' else N_SEARCH,
                         scoring='neg_mean_absolute_error',cv=cv,random_state=SEED,
                         n_jobs=1 if RUN_MODE=='smoke' else SEARCH_JOBS,refit=True,error_score='raise',return_train_score=False)
                search.fit(X.iloc[train],y.iloc[train])
                estimator = search.best_estimator_
                selected_rows.append({'experiment':exp,'model':name,'training_cv_MAE':-search.best_score_,
                                       'parameters':json.dumps(search.best_params_)})
                pd.DataFrame(search.cv_results_).to_csv(run_dir/f'{exp}_{name}_search.csv',index=False)
            else:
                estimator.fit(X.iloc[train],y.iloc[train])
            pred = estimator.predict(X.iloc[test])
            record_result(exp,name,y.iloc[test].to_numpy(),pred,test,len(train),fold,
                          'cv_fold' if kind=='cv_only' else 'holdout')
        for name,value in [('AlwaysThree',3),('TrainingMedian',float(y.iloc[train].median()))]:
            record_result(exp,name,y.iloc[test].to_numpy(),np.full(len(test),value),test,len(train),fold,
                          'cv_fold' if kind=='cv_only' else 'holdout')
    save_progress()
print('Elapsed minutes:',round((time.time()-start)/60,2))
scores = pd.DataFrame(score_rows)
summary = scores.groupby(['experiment','model','evaluation'])[['MAE','RMSE','R2','ceil_MAE']].agg(['mean','std']).reset_index()
summary.columns = ['_'.join(c).strip('_') if isinstance(c,tuple) else c for c in summary.columns]
summary.to_csv(run_dir/'summary_metrics.csv',index=False)
display(summary)
assert len(scores[['experiment','model']].drop_duplicates()) == 44  # 11 setups x 2 models + 2 baselines
if RUN_MODE == 'smoke': print('SMOKE TEST ONLY: do not use these scores as final research findings.')
''')
md('## 6. Visualise and export')
code('''
fig, axes = plt.subplots(1,2,figsize=(14,5))
monthly_registration.pivot(index='month',columns='state',values='new_registrations').plot(ax=axes[0])
axes[0].set(title='Monthly new electric motokar registrations',xlabel='Registration month',ylabel='New registrations (vehicles)')
axes[0].tick_params(axis='x',rotation=70)
view = scores[scores['experiment']=='split_only_80_none']
axes[1].bar(view['model'],view['MAE'])
axes[1].set(title=f'80/20 random split: raw prediction MAE ({run_label})',xlabel='Model or baseline',ylabel='MAE (charging points)')
axes[1].tick_params(axis='x',rotation=25)
fig.tight_layout(); fig.savefig(run_dir/'overview.png',dpi=160); plt.show()

metadata = {'run_mode':RUN_MODE,'seed':SEED,'target':TARGET,
 'target_formula':f'{EXISTING} + {PROPOSED}',
 'target_assumption':'proposed means outstanding additional chargers; not independently verified',
 'features':features,'use_adoption':USE_ADOPTION,'adoption_mode':ADOPTION_MODE,
 'adoption_reference_year':ADOPTION_REFERENCE_YEAR,'source_hashes':source_hashes,
 'poi_provenance':'unverified supplied counts; exploratory results only',
 'planned_poi_radius_metres':POI_RADIUS_METRES,'split_method':'random coordinate groups',
 'minimum_display_count':MIN_DISPLAY_COUNT,'rounding':'ceiling',
 'fixed_random_forest':FIXED_RF,'fixed_xgboost':FIXED_XGB,
 'versions':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,
             'sklearn':sklearn.__version__,'xgboost':xgboost.__version__},
 'limitations':['nearby distinct sites may share POIs','2026 registrations cover Jan-Sep only',
               'Rakan Niaga excluded','repeated test inspection is not a fresh final evaluation']}
(run_dir/'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

# A refitted deployment candidate has no independent test score after seeing all sites.
# Selection is explicit configuration, never the luckiest test split.
candidate = build_model(REFIT_MODEL_NAME)
if REFIT_PARAMS is not None: candidate.set_params(**REFIT_PARAMS)
candidate.fit(X,y)
joblib.dump({'pipeline':candidate,'features':features,'metadata':metadata},run_dir/'deployment_candidate.joblib')
print('Saved deployment candidate; not an independently evaluated final model.')
for diagnostic in OUTPUT_DIR.glob('*.csv'):
    shutil.copy2(diagnostic,run_dir/diagnostic.name)
archive = shutil.make_archive(str(run_dir),'zip',root_dir=OUTPUT_DIR,
                            base_dir=run_dir.name)
print('Results archive:',archive)
''')
md('''
## 7. Prediction interface and next steps

The application must convert the pin to the same eight POI counts, state, and confirmed site category. The notebook cannot recover these from a pin alone. If adoption is enabled, supply its stored state value using the same definition as training.

Run the following function only on genuine features prepared using matching extraction rules. Saved models are deployment candidates; a smoke-trained model is not suitable for deployment. Do not load joblib files from untrusted sources.

Before final reporting: verify or regenerate POIs; validate target semantics; justify adoption alignment; run full experiments; compare against both baselines; discuss the limitations of random splitting and the derived planning target. Do not equate the best R² across different splits with proven optimal infrastructure sizing.
''')
code('''
def predict_prepared_site(feature_values):
    missing = set(features) - set(feature_values)
    if missing: raise ValueError(f'Missing prepared inputs: {sorted(missing)}')
    frame = pd.DataFrame([feature_values])[features]
    for col in numeric_features:
        frame[col] = pd.to_numeric(frame[col],errors='raise')
        if frame[col].isna().any() or frame[col].lt(0).any():
            raise ValueError(f'Invalid prepared feature: {col}')
    if frame['state'].iloc[0] not in {'SELANGOR','W.P. KUALA LUMPUR'}:
        raise ValueError('Unsupported state')
    prediction = float(candidate.predict(frame)[0])
    return {'raw_estimate':prediction,'total_planned_chargers':int(displayed_count([prediction])[0]),
            'provisional':True,'run_mode':RUN_MODE}

# To download the archive in Colab, uncomment:
# from google.colab import files
# files.download(archive)
''')

notebook = {'nbformat':4,'nbformat_minor':5,
            'metadata':{'colab':{'name':'CastraVolt_ML_Training.ipynb','provenance':[]},
                        'kernelspec':{'name':'python3','display_name':'Python 3'},
                        'language_info':{'name':'python','version':'3.11'}}, 'cells':cells}
for i,cell in enumerate(cells): cell['id'] = f'castravolt-{i:03}'
destination = Path(__file__).with_name('CastraVolt_ML_Training.ipynb')
destination.write_text(json.dumps(notebook,indent=1,ensure_ascii=False),encoding='utf-8')
print(destination)
