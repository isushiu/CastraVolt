"""Restore the validation-selected POIs+category RF from the comparison export."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import joblib,numpy as np,pandas as pd,sklearn
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_selection import VarianceThreshold
from sklearn.ensemble import RandomForestRegressor
from castravolt.features import RULES,RULE_HASH
from castravolt.local_pois import load_snapshot

def export(archive,output):
    output=Path(output)
    if output.exists():raise ValueError('Output already exists; preserve it before restoring another artifact.')
    with zipfile.ZipFile(archive) as z:
        prefix=next(n.rsplit('/',1)[0]+'/' for n in z.namelist() if n.endswith('/run_metadata.json'))
        raw={name:z.read(prefix+name) for name in ['run_metadata.json','comparison_summary.csv','prepared_sites.csv','holdout_assignments.csv','holdout_predictions.csv']}
    metadata=json.loads(raw['run_metadata.json']);assert metadata['run_mode']=='full' and metadata['poi_radius_metres']==1000 and metadata['use_adoption'] is False
    read=lambda name:pd.read_csv(io.BytesIO(raw[name]))
    scores=read('comparison_summary.csv');choice=scores[(scores.feature_set=='POIsCategory')&np.isclose(scores.train_fraction,.8)].sort_values('training_cv_MAE_mean').iloc[0]
    assert choice.model=='RandomForest'
    params=json.loads(choice.parameters)
    expected={'model__n_estimators':600,'model__max_depth':5,'model__min_samples_leaf':10,'model__max_features':1.0}
    assert params==expected
    runtime={'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__};assert runtime=={k:metadata['versions'][k] for k in runtime}
    features=list(RULES)+['category'];assert features==metadata['feature_sets']['POIsCategory']
    data=read('prepared_sites.csv');assign=read('holdout_assignments.csv');assign=assign[np.isclose(assign.train_fraction,.8)]
    train=data[data._source_row.isin(assign.loc[assign.partition=='train','source_row'])]
    test=data[data._source_row.isin(assign.loc[assign.partition=='test','source_row'])]
    assert len(train)==1522 and len(test)==380 and set(train._coordinate_group).isdisjoint(test._coordinate_group)
    numeric=Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True))])
    category=Pipeline([('impute',SimpleImputer(strategy='constant',fill_value='Unknown')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
    prep=Pipeline([('columns',ColumnTransformer([('numeric',numeric,list(RULES)),('categorical',category,['category'])],remainder='drop')),('remove_constants',VarianceThreshold())])
    model=Pipeline([('preprocess',prep),('model',RandomForestRegressor(random_state=42,n_jobs=1))]).set_params(**params)
    model.fit(train[features],train.total_planned_chargers.astype(int))
    saved=read('holdout_predictions.csv');saved=saved[(saved.feature_set=='POIsCategory')&(saved.model=='RandomForest')&np.isclose(saved.train_fraction,.8)].set_index('source_row').loc[test._source_row]
    prediction=model.predict(test[features]);difference=float(np.max(abs(prediction-saved.raw_prediction.to_numpy())))
    assert len(saved)==380 and saved.index.is_unique and difference<1e-8
    assert np.array_equal(np.maximum(1,np.floor(prediction+.5)).astype(int),saved.displayed_count.to_numpy())
    snapshot=load_snapshot();assert snapshot['_snapshot_sha256']=='d56e00cebd86a4f9d6b24158f43f84c8e5af07afd508cb9162c215e4a5f9bdb6'
    assert metadata['source_hashes']['updated_mevnet.csv']=='d7bb8091af92f416ca212d35772a75f0e98c088a26ca02b56a0616bf39ea9458'
    output.mkdir(parents=True)
    joblib.dump({'pipeline':model,'features':features,'metadata':{**metadata,'selected_feature_set':'POIsCategory','selected_model':'RandomForest','selected_parameters':params}},output/'evaluated_pipeline.joblib',compress=3)
    manifest={'status':'prediction_parity_verified','serving_profile':'poi_category_rf','selected_model':'RandomForest','features':features,'use_adoption':False,'poi_radius_metres':1000,
        'poi_rule_sha256':RULE_HASH,'poi_snapshot_sha256':snapshot['_snapshot_sha256'],'runtime':runtime,'selected_parameters':params,
        'model_sha256':hashlib.sha256((output/'evaluated_pipeline.joblib').read_bytes()).hexdigest(),
        'source_archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),'source_hashes':{k:hashlib.sha256(v).hexdigest() for k,v in raw.items()},
        'training_dataset_sha256':metadata['source_hashes']['updated_mevnet.csv'],'train_sites':1522,'test_sites':380,'maximum_prediction_difference':difference,
        'training_cv_MAE':float(choice.training_cv_MAE_mean),'metrics':{k:float(choice[k]) for k in ['test_MAE','test_RMSE','test_R2','test_rounded_MAE']},
        'selection_basis':'lowest training-CV MAE among POIsCategory candidates; test scores not used for selection',
        'limitations':['category dominated; no reliable gain from POIs demonstrated','previously examined holdout sites','planned total is not established optimal capacity']}
    fixtures=[]
    for position in np.linspace(0,len(test)-1,10,dtype=int):
        row=test.iloc[position]
        fixtures.append({**{k:float(row[k]) for k in RULES},'category':str(row.category),'expected_raw_prediction':float(saved.iloc[position].raw_prediction),'expected_half_up_count':int(saved.iloc[position].displayed_count)})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'prediction_fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n',encoding='utf-8')
    print('Restored POIs+category RF; all 380 predictions matched. Maximum difference:',difference)
    print('CV MAE:',choice.training_cv_MAE_mean,'| test MAE:',choice.test_MAE)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,default=Path('model/verified_poi_category_rf80_cv10'));args=parser.parse_args();export(args.archive,args.output)
