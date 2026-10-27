"""Build a standalone Colab notebook comparing all POI/category/state blocks."""
import json,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parent
old=json.loads((ROOT/'CastraVolt_POI_Category_State.ipynb').read_text(encoding='utf-8'))
cells=[]
def add(kind,source):
    cell={'cell_type':kind,'metadata':{},'source':(textwrap.dedent(source).strip()+'\n').splitlines(keepends=True)}
    if kind=='code':cell.update(execution_count=None,outputs=[])
    cells.append(cell)
def md(s):add('markdown',s)
def code(s):add('code',s)
def prev(i):return ''.join(old['cells'][i]['source'])
md('''
# CastraVolt: compare all feature combinations

Use the **same 1 km dataset** to test all seven nonempty combinations of three input blocks: **POIs, category and state**. POIs means the eight facility counts together, not every subset of individual POI columns. EV registrations are excluded.

Each feature set gets a separately tuned **Random Forest and XGBoost**: 14 candidates, plus always-three and training-median baselines. The default is the previous approximately **80/20 split**, **10-fold training CV**, seed **42**, and identical rows/folds for every candidate. Exactly co-located sites stay together; nearby sites can still share POIs.

**Run in Colab:** run cells in order, upload the two CSV files below, keep full mode, then download the results ZIP. Send back the ZIP, or the comparison_summary.csv, feature_added_value.csv and permutation_diagnostics.csv files.

Upload **updated_mevnet.csv** and **updated_mevnet_row_groups.csv** from data/ML Data. The second file supplies coordinate groups for reproducible splits; coordinates and identifiers never become model inputs. Do not upload registration files or API keys.

The target remains total planned charging points (existing + proposed under the agreed additional-proposed assumption). These test sites were already inspected previously: this comparison is exploratory, not a fresh independent final test. The notebook does not replace the app model.
''')
code(prev(1)+'''
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import cross_val_score
''')
md('''
## 1. Settings and upload

Full mode runs 30 sampled settings × 10 folds × 14 candidates = **4,200 validation fits**, plus refits. Allow a substantial Colab session. A GPU is not required. Progress is saved after each candidate. Smoke mode only checks the workflow and must not be reported as final training results.

Start with the 80/20 split. You can optionally add 50/50 and 70/30 below; that triples the work. This notebook compares input blocks rather than repeating all eleven earlier protocols. Existing Colab libraries are reused and exact versions are exported for reproducibility.
''')
code('''
SEED = 42
RUN_MODE = 'full'  # full | smoke
DATA_SOURCE = 'upload'  # upload | drive | local
DATA_DIR = Path('/content/drive/MyDrive/CastraVolt/data/ML Data')
FILES = ['updated_mevnet.csv','updated_mevnet_row_groups.csv']
KNOWN_HASHES = {
 'updated_mevnet.csv':'d7bb8091af92f416ca212d35772a75f0e98c088a26ca02b56a0616bf39ea9458',
 'updated_mevnet_row_groups.csv':'d22b39b3b3bb517934090d555add833c51cfbd391533310840c2e2edc4d6f203'}
REQUIRE_KNOWN_SOURCE_HASHES = True
TRAIN_FRACTIONS = [0.8]  # optionally [0.5,0.7,0.8]
PRIMARY_TRAIN_FRACTION = 0.8
CV_FOLDS = 10
N_SEARCH = 30
SEARCH_JOBS = 2  # reduce to 1 if workers or memory cause problems
PERMUTATION_REPEATS = 20
BOOTSTRAP_REPEATS = 1000
EXPORT_ALL_MODELS = False
AUTO_DOWNLOAD = True
TARGET = 'total_planned_chargers'
MIN_DISPLAY_COUNT = 1
POI = ['nearby_mall_count','nearby_petrol_count','nearby_hotel_count','nearby_office_count',
       'nearby_transit_count','nearby_university_count','nearby_hospital_count','nearby_parking_count']
FEATURE_SETS = {
 'POIsOnly':POI.copy(), 'CategoryOnly':['category'], 'StateOnly':['state'],
 'POIsCategory':POI+['category'], 'POIsState':POI+['state'],
 'CategoryState':['category','state'], 'POIsCategoryState':POI+['category','state']}
assert RUN_MODE in ['full','smoke'] and PRIMARY_TRAIN_FRACTION in TRAIN_FRACTIONS
assert all(0<value<1 for value in TRAIN_FRACTIONS) and CV_FOLDS>=2
run_label='feature_comparison_1km_'+RUN_MODE
run_stamp=time.strftime('%Y%m%d_%H%M%S',time.gmtime())+'UTC'
OUTPUT_DIR=Path('castravolt_feature_comparison_results')/(run_label+'_'+run_stamp)
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
''')
code(r'''
if DATA_SOURCE == 'upload':
    from google.colab import files
    import re
    uploaded={re.sub(r' \(\d+\)(?=\.csv$)','',name):content for name,content in files.upload().items()}
    DATA_DIR=Path('/content/castravolt_feature_inputs');DATA_DIR.mkdir(exist_ok=True)
    for name in FILES:
        if name not in uploaded:raise FileNotFoundError(f'Upload both required CSVs. Missing: {name}')
        (DATA_DIR/name).write_bytes(uploaded[name])
elif DATA_SOURCE == 'drive':
    from google.colab import drive
    drive.mount('/content/drive')
elif DATA_SOURCE == 'local':
    DATA_DIR=Path('data/ML Data') if Path('data/ML Data').exists() else Path('../data/ML Data')
else:raise ValueError('Choose upload, drive or local')
source_hashes={name:hashlib.sha256((DATA_DIR/name).read_bytes()).hexdigest() for name in FILES}
if REQUIRE_KNOWN_SOURCE_HASHES and source_hashes!=KNOWN_HASHES:
    raise ValueError('Use the current matching dataset/group pair from data/ML Data; source hashes differ.')
raw=pd.read_csv(DATA_DIR/FILES[0]);row_groups=pd.read_csv(DATA_DIR/FILES[1])
print('Dataset rows:',len(raw),'| Group rows:',len(row_groups))
''')
md('''
## 2. Audit and clean

Audit missing/constant/unique values, invalid targets/states and invalid POI counts. Imputation, encoding and constant-feature removal are fitted within training folds. Do not remove distinct sites merely because model inputs are identical. Missing category becomes Unknown; IDs, coordinates and target components never enter the model.
''')
code(prev(6).replace("print('Model features:', features)","print('Feature variants:', list(FEATURE_SETS))"))
md('''
## 3. Shared splits and pipelines

These split/fold functions are identical to the previous 1 km notebook. All variants use the same holdout sites and CV folds. Each variant has its own preprocessor and separately tuned hyperparameters. Test data does not fit preprocessing or choose settings.
''')
code(prev(8).split('holdouts =')[0]+'''
holdouts={ratio:random_group_holdout(coordinate_groups,1-ratio) for ratio in TRAIN_FRACTIONS}
folds={};assignments=[];cv_assignments=[]
for ratio,(train,test) in holdouts.items():
    assert_disjoint(train,test,coordinate_groups)
    folds[ratio]=random_group_folds(coordinate_groups[train],CV_FOLDS)
    seen=[]
    for fold,(inner_train,inner_valid) in enumerate(folds[ratio]):
        assert_disjoint(inner_train,inner_valid,coordinate_groups[train]);seen.extend(inner_valid.tolist())
        cv_assignments.extend({'train_fraction':ratio,'fold':fold,'source_row':int(sites.iloc[train[i]]['_source_row'])} for i in inner_valid)
    assert sorted(seen)==list(range(len(train)))
    for partition,indices in [('train',train),('test',test)]:
        assignments.extend({'train_fraction':ratio,'source_row':int(sites.iloc[i]['_source_row']),
            'coordinate_group':coordinate_groups[i],'partition':partition} for i in indices)
pd.DataFrame(assignments).to_csv(OUTPUT_DIR/'holdout_assignments.csv',index=False)
pd.DataFrame(cv_assignments).to_csv(OUTPUT_DIR/'cv_assignments.csv',index=False)
print({ratio:{'train':len(a),'test':len(b),'folds':len(folds[ratio])} for ratio,(a,b) in holdouts.items()})
''')
code('''
SEARCH_SPACES={
 'RandomForest':{'model__n_estimators':[300,600],'model__max_depth':[5,10,None],
     'model__min_samples_leaf':[1,2,5,10],'model__max_features':['sqrt',1.0]},
 'XGBoost':{'model__n_estimators':[100,300,600],'model__max_depth':[2,3,5],
     'model__learning_rate':[0.03,0.05,0.1],'model__subsample':[0.8,1.0],
     'model__colsample_bytree':[0.8,1.0],'model__reg_lambda':[1,5]}}

def build_model(name,feature_columns):
    numeric=[c for c in feature_columns if c in POI]
    categorical=[c for c in feature_columns if c not in POI]
    transformers=[]
    if numeric:
        transformers.append(('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True))]),numeric))
    if categorical:
        transformers.append(('categorical',Pipeline([('impute',SimpleImputer(strategy='constant',fill_value='Unknown')),
            ('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical))
    preprocessing=Pipeline([('columns',ColumnTransformer(transformers,remainder='drop')),('remove_constants',VarianceThreshold())])
    if name=='RandomForest':estimator=RandomForestRegressor(random_state=SEED,n_jobs=1)
    elif name=='XGBoost':estimator=XGBRegressor(objective='reg:squarederror',random_state=SEED,n_jobs=1,tree_method='hist')
    else:raise ValueError(name)
    return Pipeline([('preprocess',preprocessing),('model',estimator)])

def displayed_count(values):return np.maximum(MIN_DISPLAY_COUNT,np.floor(np.asarray(values)+0.5)).astype(int)
def metrics(actual,prediction):
    actual,prediction=np.asarray(actual),np.asarray(prediction)
    return {'MAE':float(mean_absolute_error(actual,prediction)),
        'RMSE':float(np.sqrt(mean_squared_error(actual,prediction))),'R2':float(r2_score(actual,prediction)),
        'rounded_MAE':float(mean_absolute_error(actual,displayed_count(prediction))),
        'exact_fraction':float(np.mean(displayed_count(prediction)==actual)),
        'within_1_fraction':float(np.mean(np.abs(displayed_count(prediction)-actual)<=1)),
        'within_2_fraction':float(np.mean(np.abs(displayed_count(prediction)-actual)<=2))}
def serialisable(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,Path):return str(value)
    raise TypeError(type(value).__name__)
for variant,columns in FEATURE_SETS.items():print(variant,':',columns)
''')
md('''
## 4. Train all feature combinations

Choose settings by **training CV MAE only**. Test columns describe the shared held-out sites, not CV means. Baseline medians are learned within their training folds. Each search and completed result is saved immediately. Re-running this training cell starts its comparisons again; after an interruption, the final download cell can still archive completed files.
''')
code('''
score_rows=[];prediction_rows=[];models={};model_records={};started=time.time()
def record(variant,name,ratio,actual,prediction,test,cv_mean,cv_std,params,elapsed):
    row={'feature_set':variant,'model':name,'train_fraction':ratio,'n_features':len(FEATURE_SETS.get(variant,[])),
        'n_train':len(holdouts[ratio][0]),'n_test':len(test),'training_cv_MAE_mean':float(cv_mean),
        'training_cv_MAE_std':float(cv_std),'parameters':json.dumps(params,sort_keys=True,default=serialisable),
        'elapsed_seconds':elapsed,**{'test_'+k:v for k,v in metrics(actual,prediction).items()}}
    score_rows.append(row)
    for i,a,p in zip(test,actual,prediction):
        prediction_rows.append({'feature_set':variant,'model':name,'train_fraction':ratio,'source_row':int(sites.iloc[i]['_source_row']),
            'coordinate_group':coordinate_groups[i],'actual':int(a),'raw_prediction':float(p),'displayed_count':int(displayed_count([p])[0])})
    pd.DataFrame(score_rows).to_csv(OUTPUT_DIR/'comparison_summary.csv',index=False)
    pd.DataFrame(prediction_rows).to_csv(OUTPUT_DIR/'holdout_predictions.csv',index=False)
    return row
for ratio,(train,test) in holdouts.items():
    cv=folds[ratio]
    for name,strategy,constant in [('AlwaysThree','constant',3),('TrainingMedian','median',None)]:
        estimator=DummyRegressor(strategy=strategy,**({'constant':constant} if constant is not None else {}))
        values=-cross_val_score(estimator,np.zeros((len(train),1)),y.iloc[train],cv=cv,scoring='neg_mean_absolute_error')
        estimator.fit(np.zeros((len(train),1)),y.iloc[train])
        record('Baseline',name,ratio,y.iloc[test].to_numpy(),estimator.predict(np.zeros((len(test),1))),test,values.mean(),values.std(),{'strategy':strategy},0)
    for variant,columns in FEATURE_SETS.items():
        for name in ['RandomForest','XGBoost']:
            task_started=time.time();print(f'Training {variant} / {name} / {ratio:.0%} training...',flush=True)
            space=SEARCH_SPACES[name] if RUN_MODE=='full' else {'model__n_estimators':[8,12],'model__max_depth':[2]}
            search=RandomizedSearchCV(build_model(name,columns),space,n_iter=N_SEARCH if RUN_MODE=='full' else 2,
                scoring='neg_mean_absolute_error',cv=cv,random_state=SEED,n_jobs=SEARCH_JOBS if RUN_MODE=='full' else 1,
                refit=True,error_score='raise',return_train_score=False)
            search.fit(sites.iloc[train][columns],y.iloc[train])
            best=search.best_estimator_;key=(ratio,variant,name);models[key]=best
            row=record(variant,name,ratio,y.iloc[test].to_numpy(),best.predict(sites.iloc[test][columns]),test,
                -search.best_score_,search.cv_results_['std_test_score'][search.best_index_],search.best_params_,time.time()-task_started)
            model_records[key]=row
            pd.DataFrame(search.cv_results_).to_csv(OUTPUT_DIR/f'{int(ratio*100)}_{variant}_{name}_search.csv',index=False)
            if EXPORT_ALL_MODELS:
                joblib.dump({'pipeline':best,'features':columns,'feature_set':variant,'model_name':name,'train_fraction':ratio},
                    OUTPUT_DIR/f'{int(ratio*100)}_{variant}_{name}.joblib',compress=3)
            print(f"  CV MAE={row['training_cv_MAE_mean']:.4f}; test MAE={row['test_MAE']:.4f}; {row['elapsed_seconds']/60:.1f} min",flush=True)
scores=pd.DataFrame(score_rows);predictions=pd.DataFrame(prediction_rows)
assert len(model_records)==len(TRAIN_FRACTIONS)*len(FEATURE_SETS)*2
for ratio in TRAIN_FRACTIONS:
    view=predictions[predictions.train_fraction==ratio]
    assert len({tuple(g.sort_values('source_row').source_row) for _,g in view.groupby(['feature_set','model'])})==1
print('Elapsed minutes:',round((time.time()-started)/60,2))
display(scores.sort_values(['train_fraction','training_cv_MAE_mean']).drop(columns=['parameters']))
if RUN_MODE=='smoke':print('SMOKE ONLY: workflow checks, not final research findings.')
''')
md('''
## 5. Does adding a feature block help?

Positive gain means **lower MAE** for the expanded feature set. Training-CV and test gains are separate. Paired intervals resample coordinate groups, not independent site rows. They are descriptive: these test sites have been reused and multiple comparisons are made. A small/uncertain gain is not proof of useful location sensitivity.
''')
code('''
ADDITIONS=[('CategoryOnly','POIsCategory','POIs'),('StateOnly','POIsState','POIs'),('CategoryState','POIsCategoryState','POIs'),
    ('POIsOnly','POIsCategory','Category'),('POIsState','POIsCategoryState','Category'),('POIsOnly','POIsState','State'),
    ('POIsCategory','POIsCategoryState','State'),('CategoryOnly','CategoryState','State')]
def paired_gain_interval(base,expanded,repeats=BOOTSTRAP_REPEATS):
    assert base.source_row.tolist()==expanded.source_row.tolist() and base.actual.tolist()==expanded.actual.tolist()
    gain=np.abs(base.actual.to_numpy()-base.raw_prediction.to_numpy())-np.abs(expanded.actual.to_numpy()-expanded.raw_prediction.to_numpy())
    grouped=pd.DataFrame({'group':base.coordinate_group.to_numpy(),'gain':gain}).groupby('group').gain.agg(['sum','size'])
    sample=np.random.default_rng(SEED).integers(0,len(grouped),size=(repeats,len(grouped)))
    boot=grouped['sum'].to_numpy()[sample].sum(axis=1)/grouped['size'].to_numpy()[sample].sum(axis=1)
    return float(gain.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))
added=[]
for ratio in TRAIN_FRACTIONS:
    for name in ['RandomForest','XGBoost']:
        for base_variant,expanded_variant,block in ADDITIONS:
            a=model_records[(ratio,base_variant,name)];b=model_records[(ratio,expanded_variant,name)]
            base=predictions[(predictions.train_fraction==ratio)&(predictions.model==name)&(predictions.feature_set==base_variant)].sort_values('source_row')
            expanded=predictions[(predictions.train_fraction==ratio)&(predictions.model==name)&(predictions.feature_set==expanded_variant)].sort_values('source_row')
            gain,low,high=paired_gain_interval(base,expanded)
            added.append({'train_fraction':ratio,'model':name,'base_features':base_variant,'expanded_features':expanded_variant,'added_block':block,
                'training_cv_MAE_gain':a['training_cv_MAE_mean']-b['training_cv_MAE_mean'],'test_MAE_gain':gain,
                'test_gain_95pct_low':low,'test_gain_95pct_high':high})
added=pd.DataFrame(added);added.to_csv(OUTPUT_DIR/'feature_added_value.csv',index=False)
display(added[added.added_block=='POIs'])
''')
md('''
## 6. Sensitivity and zero-POI highway scenarios

Joint POI shuffling checks whether a fitted model relies on POIs. Category/state shuffling checks those inputs separately. Zero-POI examples show the model's response, **not correct capacity**. Even POI-only models can give positive estimates with zero counts because training targets are positive. Model diversity alone is not accuracy.
''')
code('''
permutation_rows=[];scenario_rows=[];band_rows=[]
for (ratio,variant,name),estimator in models.items():
    train,test=holdouts[ratio];columns=FEATURE_SETS[variant]
    actual=y.iloc[test].to_numpy();base=sites.iloc[test][columns].copy();prediction=estimator.predict(base)
    base_mae=mean_absolute_error(actual,prediction)
    blocks={'POIs':[c for c in POI if c in columns],'Category':['category'] if 'category' in columns else [],'State':['state'] if 'state' in columns else []}
    for block,changed in blocks.items():
        if not changed:continue
        values=[]
        for seed in range(PERMUTATION_REPEATS):
            shuffled=base.copy();order=np.random.default_rng(SEED+seed).permutation(len(base))
            shuffled[changed]=base.iloc[order][changed].to_numpy()
            values.append(float(mean_absolute_error(actual,estimator.predict(shuffled))))
        permutation_rows.append({'train_fraction':ratio,'feature_set':variant,'model':name,'shuffled_block':block,
            'baseline_test_MAE':float(base_mae),'shuffled_MAE_mean':float(np.mean(values)),
            'shuffled_MAE_std':float(np.std(values)),'MAE_increase':float(np.mean(values)-base_mae)})
    for category in ['Highway','Petrol Station','Office','Shopping Mall']:
        for state in (['SELANGOR','W.P. KUALA LUMPUR'] if 'state' in columns else ['SELANGOR']):
            supplied={**{key:0 for key in POI},'category':category,'state':state}
            value=float(estimator.predict(pd.DataFrame([{key:supplied[key] for key in columns}],columns=columns))[0])
            scenario_rows.append({'train_fraction':ratio,'feature_set':variant,'model':name,'scenario':'all eight POI counts zero',
                'category_setting':category if 'category' in columns else 'not an input','state_setting':state if 'state' in columns else 'not an input',
                'raw_prediction':value,'displayed_count':int(displayed_count([value])[0])})
    for label,mask in [('1_to_4',actual<=4),('5_to_9',(actual>=5)&(actual<=9)),('10_plus',actual>=10)]:
        if mask.any():band_rows.append({'train_fraction':ratio,'feature_set':variant,'model':name,'actual_band':label,'n_sites':int(mask.sum()),**metrics(actual[mask],prediction[mask])})
permutations=pd.DataFrame(permutation_rows);permutations.to_csv(OUTPUT_DIR/'permutation_diagnostics.csv',index=False)
pd.DataFrame(scenario_rows).drop_duplicates().to_csv(OUTPUT_DIR/'zero_poi_scenarios.csv',index=False)
pd.DataFrame(band_rows).to_csv(OUTPUT_DIR/'errors_by_target_band.csv',index=False)
train,_=holdouts[PRIMARY_TRAIN_FRACTION]
category_stats=sites.iloc[train].groupby('category')[TARGET].agg(['size','mean','median','min','max']).reset_index()
category_stats.to_csv(OUTPUT_DIR/'training_category_target_summary.csv',index=False)
print('Highway training examples:');display(category_stats[category_stats.category.eq('Highway')])
print('POI reliance for POIs + category:')
display(permutations[(permutations.feature_set=='POIsCategory')&(permutations.shuffled_block=='POIs')])
''')
md('''
## 7. Plots and a training-CV-selected candidate

The exported candidate is selected using training CV on the primary split. Test scores are descriptive. Do not choose a model just because it wins a previously inspected test set. Check whether POIs improve category-only predictions and whether errors for larger sites remain acceptable.
''')
code('''
view=scores[(scores.train_fraction==PRIMARY_TRAIN_FRACTION)&(scores.feature_set!='Baseline')]
fig,axes=plt.subplots(1,2,figsize=(16,6));order=list(FEATURE_SETS);positions=np.arange(len(order));width=.36
for ax,metric,title in [(axes[0],'training_cv_MAE_mean','Training CV MAE (selection)'),(axes[1],'test_MAE','Previously examined holdout MAE (descriptive)')]:
    for offset,name in [(-width/2,'RandomForest'),(width/2,'XGBoost')]:
        rows=view[view.model==name].set_index('feature_set').loc[order]
        ax.bar(positions+offset,rows[metric],width,label=name)
    for _,baseline in scores[(scores.train_fraction==PRIMARY_TRAIN_FRACTION)&(scores.feature_set=='Baseline')].iterrows():
        ax.axhline(baseline[metric],linestyle='--',linewidth=1,label=baseline['model'])
    ax.set_xticks(positions,order,rotation=40,ha='right');ax.set_ylabel('MAE (charging points)');ax.set_title(title);ax.legend(fontsize=8)
fig.suptitle(f'Feature comparison — {RUN_MODE.upper()} — identical site splits')
fig.tight_layout();fig.savefig(OUTPUT_DIR/'feature_comparison.png',dpi=160,bbox_inches='tight');plt.show()
selected=view.sort_values(['training_cv_MAE_mean','feature_set','model']).iloc[0]
selected_key=(PRIMARY_TRAIN_FRACTION,selected['feature_set'],selected['model'])
candidate=models[selected_key];chosen_features=FEATURE_SETS[selected['feature_set']]
print('Selected by training CV:',selected['feature_set'],selected['model'])
print('CV MAE:',selected['training_cv_MAE_mean'],'| held-out MAE:',selected['test_MAE'])
print('Research candidate only; the app model has not been changed.')
''')
md('''
## 8. Save reproducibility metadata and candidate

The candidate is the fitted evaluated model, not an untested all-data refit. The original source hashes, schemas, exact assignments, search spaces and library versions are saved. Joblib files must only be loaded from trusted sources with compatible versions.
''')
code('''
metadata={'run_mode':RUN_MODE,'seed':SEED,'source_hashes':source_hashes,'target':TARGET,
 'target_assumption':'MEVnet existing + additional proposed; not independently validated optimal capacity',
 'feature_sets':FEATURE_SETS,'poi_radius_metres':1000,'use_adoption':False,'train_fractions':TRAIN_FRACTIONS,
 'primary_train_fraction':PRIMARY_TRAIN_FRACTION,'cv_folds':CV_FOLDS,'n_search':N_SEARCH if RUN_MODE=='full' else 2,
 'search_spaces':SEARCH_SPACES if RUN_MODE=='full' else {name:{'model__n_estimators':[8,12],'model__max_depth':[2]} for name in ['RandomForest','XGBoost']},
 'permutation_repeats':PERMUTATION_REPEATS,'bootstrap_repeats':BOOTSTRAP_REPEATS,'search_jobs':SEARCH_JOBS if RUN_MODE=='full' else 1,
 'split_method':'same seeded coordinate-group holdout and balanced group folds as earlier notebook',
 'selection_rule':'lowest training-CV MAE on primary split; test scores not used for selection',
 'selected_feature_set':selected['feature_set'],'selected_model':selected['model'],'selected_parameters':json.loads(selected['parameters']),
 'rounding':'nearest_half_up_minimum_1','versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
 'sklearn':sklearn.__version__,'xgboost':xgboost.__version__,'joblib':joblib.__version__},
 'limitations':['previously examined test sites: exploratory, not fresh final validation','inferred host categories; planned totals do not establish optimal capacity',
 'nearby sites can share POIs','tuning CV is not nested outer validation','bootstrap/permutation diagnostics are descriptive; no multiple-comparison correction'],
 'elapsed_minutes':(time.time()-started)/60}
(OUTPUT_DIR/'run_metadata.json').write_text(json.dumps(metadata,indent=2,default=serialisable),encoding='utf-8')
joblib.dump({'pipeline':candidate,'features':chosen_features,'metadata':metadata},OUTPUT_DIR/'training_cv_selected_candidate.joblib',compress=3)
''')
md('''
## 9. Download the result ZIP

Send back the ZIP. At minimum send comparison_summary.csv, feature_added_value.csv, permutation_diagnostics.csv and run_metadata.json. The final cell can also download whatever files were completed if a long run was interrupted; incomplete output is not a complete comparison.
''')
code('''
manifest={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in OUTPUT_DIR.iterdir() if path.is_file() and path.name!='output_hashes.json'}
(OUTPUT_DIR/'output_hashes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=Path(shutil.make_archive(str(OUTPUT_DIR),'zip',root_dir=OUTPUT_DIR.parent,base_dir=OUTPUT_DIR.name))
print('Results ZIP:',archive.resolve())
if RUN_MODE=='smoke':print('SMOKE ONLY: do not report these as final training results.')
if AUTO_DOWNLOAD and DATA_SOURCE!='local':
    from google.colab import files
    files.download(str(archive))
''')
notebook={'cells':cells,'metadata':{'colab':{'provenance':[]},'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}},'nbformat':4,'nbformat_minor':5}
for index,cell in enumerate(cells):
    cell['id']=f'feature-comparison-{index:02d}'
    if cell['cell_type']=='code':compile(''.join(cell['source']),f'cell-{index}','exec')
path=ROOT/'CastraVolt_Feature_Comparison.ipynb'
path.write_text(json.dumps(notebook,indent=1,ensure_ascii=False)+'\n',encoding='utf-8')
print('Created',path.name,'with',len(cells),'cells')
