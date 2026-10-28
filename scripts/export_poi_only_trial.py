"""Export the CV-selected POIsOnly learner from a trusted comparison ZIP."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import joblib,numpy as np,pandas as pd,sklearn,xgboost
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import VarianceThreshold
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor
from castravolt.features import RULES,RULE_HASH,extract_counts
from castravolt.local_pois import load_snapshot,query_snapshot

def export(archive,output,booster=None):
    output=Path(output)
    if output.exists():raise ValueError('Preserve existing output before exporting a new candidate.')
    with zipfile.ZipFile(archive) as z:
        names=[n for n in z.namelist() if n.endswith('/run_metadata.json')]
        assert len(names)==1
        prefix=names[0].rsplit('/',1)[0]+'/'
        raw={name:z.read(prefix+name) for name in ['run_metadata.json','prepared_sites.csv','holdout_assignments.csv','holdout_predictions.csv','comparison_summary.csv']}
    metadata=json.loads(raw['run_metadata.json'])
    assert metadata['run_mode']=='full' and metadata['poi_radius_metres']==1000 and metadata['use_adoption'] is False
    assert metadata['source_hashes']['updated_mevnet.csv']=='d7bb8091af92f416ca212d35772a75f0e98c088a26ca02b56a0616bf39ea9458'
    runtime={'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,'xgboost':xgboost.__version__}
    assert runtime=={k:metadata['versions'][k] for k in runtime}
    read=lambda name:pd.read_csv(io.BytesIO(raw[name]))
    scores=read('comparison_summary.csv')
    choice=scores[(scores.feature_set=='POIsOnly')&np.isclose(scores.train_fraction,.8)].sort_values('training_cv_MAE_mean').iloc[0]
    assert choice.model=='XGBoost'
    params=json.loads(choice.parameters)
    features=list(RULES);assert features==metadata['feature_sets']['POIsOnly']
    data=read('prepared_sites.csv');splits=read('holdout_assignments.csv');splits=splits[np.isclose(splits.train_fraction,.8)]
    train=data[data._source_row.isin(splits.loc[splits.partition=='train','source_row'])]
    test=data[data._source_row.isin(splits.loc[splits.partition=='test','source_row'])]
    assert len(train)==1522 and len(test)==380
    assert set(train._coordinate_group).isdisjoint(test._coordinate_group)
    snapshot=load_snapshot();assert snapshot['_snapshot_sha256']=='d56e00cebd86a4f9d6b24158f43f84c8e5af07afd508cb9162c215e4a5f9bdb6'
    for index in [0,50,150,800,1100,1800]:
        row=data.iloc[index];lat,lon=map(float,row._coordinate_group.split('|'))
        assert extract_counts(query_snapshot(snapshot,lat,lon),lat,lon)=={key:int(row[key]) for key in features}
    numeric=Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True))])
    preprocessing=Pipeline([('columns',ColumnTransformer([('numeric',numeric,features)],remainder='drop')),('remove_constants',VarianceThreshold())])
    pipeline=Pipeline([('preprocess',preprocessing),('model',XGBRegressor(objective='reg:squarederror',random_state=42,n_jobs=1,tree_method='hist'))]).set_params(**params)
    pipeline.fit(train[features],train.total_planned_chargers)
    saved=read('holdout_predictions.csv');saved=saved[(saved.feature_set=='POIsOnly')&(saved.model=='XGBoost')&np.isclose(saved.train_fraction,.8)].set_index('source_row').loc[test._source_row]
    assert len(saved)==380 and saved.index.is_unique
    if booster is not None:pipeline.named_steps['model'].load_model(booster)
    prediction=pipeline.predict(test[features]);difference=float(np.max(np.abs(prediction-saved.raw_prediction.to_numpy())))
    print("Reconstruction maximum raw difference:",difference,flush=True)
    assert difference<1e-7
    assert np.array_equal(np.maximum(1,np.floor(prediction+.5)).astype(int),saved.displayed_count.to_numpy())
    assert np.array_equal(test.total_planned_chargers.to_numpy(),saved.actual.to_numpy())
    output.mkdir(parents=True)
    bundle_metadata={**metadata,'selected_feature_set':'POIsOnly','selected_model':'XGBoost','selected_parameters':params}
    joblib.dump({'pipeline':pipeline,'features':features,'metadata':bundle_metadata},output/'evaluated_pipeline.joblib',compress=3)
    sha=hashlib.sha256((output/'evaluated_pipeline.joblib').read_bytes()).hexdigest()
    manifest={'status':'prediction_parity_verified','serving_profile':'poi_only_xgb','selected_model':'XGBoost','features':features,
        'use_adoption':False,'poi_radius_metres':1000,'poi_rule_sha256':RULE_HASH,'poi_snapshot_sha256':snapshot['_snapshot_sha256'],
        'runtime':runtime,'selected_parameters':params,'model_sha256':sha,'training_dataset_sha256':metadata['source_hashes']['updated_mevnet.csv'],
        'portable_booster_sha256':hashlib.sha256(Path(booster).read_bytes()).hexdigest() if booster else None,
        'source_archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),'source_files':{k:hashlib.sha256(v).hexdigest() for k,v in raw.items()},
        'train_sites':len(train),'test_sites':len(test),'maximum_prediction_difference':difference,'training_cv_MAE':float(choice.training_cv_MAE_mean),
        'metrics':{k:float(choice[k]) for k in ['test_MAE','test_RMSE','test_R2','test_rounded_MAE']},
        'selection_basis':'lowest training-CV MAE among POIsOnly candidates at 80/20; not lowest heldout error',
        'limitations':['POI-only experimental trial; worse MAE than always-three baseline','previously examined test sites; not a fresh final test','zero mapped POIs does not establish zero capacity']}
    fixtures=[]
    for position in np.linspace(0,len(test)-1,10,dtype=int):
        row=test.iloc[position]
        fixtures.append({**{k:float(row[k]) for k in features},'expected_raw_prediction':float(saved.iloc[position].raw_prediction),'expected_half_up_count':int(saved.iloc[position].displayed_count)})
    if booster is not None:(output/'verified_booster.json').write_bytes(Path(booster).read_bytes())
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'prediction_fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n',encoding='utf-8')
    print('POI-only XGBoost restored; all 380 saved predictions matched. Maximum difference:',difference)
    print('Training CV MAE:',choice.training_cv_MAE_mean,'| test MAE:',choice.test_MAE)
    print('Model SHA256:',sha)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,default=Path('model/verified_poi_only_xgb80_cv10'));parser.add_argument('--booster',type=Path);args=parser.parse_args();export(args.archive,args.output,args.booster)
