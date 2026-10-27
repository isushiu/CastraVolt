"""Restore the selected evaluated RF from the trusted user-provided Colab export.

Usage: python scripts/restore_verified_model.py path/to/poi_category_state_1km_full.zip
Only run this against an export you trust: joblib contains executable Python objects.
"""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
import joblib,numpy as np,pandas as pd,sklearn
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from castravolt.features import ModelFeatures,RULE_HASH,extract_counts
from castravolt.local_pois import load_snapshot,query_snapshot

EXPECTED_SNAPSHOT='d56e00cebd86a4f9d6b24158f43f84c8e5af07afd508cb9162c215e4a5f9bdb6'
EXPECTED_DATASET='d7bb8091af92f416ca212d35772a75f0e98c088a26ca02b56a0616bf39ea9458'
PARAMETERS={'model__n_estimators':600,'model__max_depth':5,'model__min_samples_leaf':10,'model__max_features':1.0}


def restore(archive,output):
    output=Path(output)
    if output.exists():raise ValueError('Output folder already exists; preserve it before restoring another copy.')
    with zipfile.ZipFile(archive) as zipped:
        prefix='poi_category_state_1km_full/'
        names=['candidate_model.joblib','prepared_sites.csv','holdout_assignments.csv','holdout_predictions.csv','selected_hyperparameters.csv','run_metadata.json']
        raw={name:zipped.read(prefix+name) for name in names}
    meta=json.loads(raw['run_metadata.json'])
    assert meta['run_mode']=='full' and meta['poi_radius_metres']==1000 and meta['use_adoption'] is False
    assert meta['source_hashes']['updated_mevnet.csv']==EXPECTED_DATASET
    features=meta['features'];assert features==list(ModelFeatures.model_fields)
    runtime={'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}
    assert runtime=={k:meta['versions'][k] for k in runtime},'Install the locked model-validation dependency group.'
    snapshot=load_snapshot();assert snapshot['_snapshot_sha256']==EXPECTED_SNAPSHOT
    data=pd.read_csv(io.BytesIO(raw['prepared_sites.csv']))
    assignments=pd.read_csv(io.BytesIO(raw['holdout_assignments.csv']))
    predictions=pd.read_csv(io.BytesIO(raw['holdout_predictions.csv']))
    selected=pd.read_csv(io.BytesIO(raw['selected_hyperparameters.csv']))
    chosen=selected[(selected.experiment=='split_cv_80_10')&(selected.model=='RandomForest')]
    assert len(chosen)==1 and json.loads(chosen.iloc[0].parameters)==PARAMETERS
    assert len(data)==1902 and data._source_row.is_unique
    split=assignments[np.isclose(assignments.train_fraction,.8)]
    train=data[data._source_row.isin(split.loc[split.partition=='train','source_row'])]
    test=data[data._source_row.isin(split.loc[split.partition=='test','source_row'])]
    assert len(train)==1522 and len(test)==380 and set(train._source_row).isdisjoint(test._source_row)
    assert set(train._coordinate_group).isdisjoint(test._coordinate_group)
    # Check that the current map query reproduces source feature vectors before
    # declaring it compatible with this evaluated artifact.
    for index in [0,50,150,800,1100,1800]:
        row=data.iloc[index];lat,lon=map(float,row._coordinate_group.split('|'))
        counts=extract_counts(query_snapshot(snapshot,lat,lon),lat,lon)
        assert counts=={key:int(row[key]) for key in features[:8]},'Source POI parity differs.'
    candidate=joblib.load(io.BytesIO(raw['candidate_model.joblib']))
    pipeline=clone(candidate['pipeline']).set_params(**PARAMETERS,model__n_jobs=1)
    pipeline.fit(train[features],train[meta['target']])
    expected=predictions[(predictions.experiment=='split_cv_80_10')&(predictions.model=='RandomForest')&(predictions.evaluation=='holdout')].set_index('source_row')
    assert len(expected)==380 and expected.index.is_unique
    expected=expected.loc[test._source_row]
    actual=pipeline.predict(test[features])
    maximum=float(np.max(np.abs(actual-expected.raw_prediction.to_numpy())))
    assert maximum<1e-8,'Reconstruction does not reproduce the evaluated model.'
    rounded=np.maximum(1,np.floor(actual+.5)).astype(int)
    assert np.array_equal(rounded,expected.displayed_count.to_numpy())
    assert np.array_equal(test[meta['target']].to_numpy(),expected.actual.to_numpy())
    fixtures=[]
    for position in np.linspace(0,len(test)-1,10,dtype=int):
        row=test.iloc[position]
        values={key:(float(row[key]) if key in features[:8] else str(row[key])) for key in features}
        values.update(expected_raw_prediction=float(expected.iloc[position].raw_prediction),expected_half_up_count=int(expected.iloc[position].displayed_count))
        fixtures.append(values)
    output.mkdir(parents=True)
    joblib.dump({'pipeline':pipeline,'features':features,'metadata':meta},output/'evaluated_pipeline.joblib',compress=3)
    sha=hashlib.sha256((output/'evaluated_pipeline.joblib').read_bytes()).hexdigest()
    target=test[meta['target']].to_numpy()
    manifest={'status':'prediction_parity_verified','features':features,'use_adoption':False,'poi_radius_metres':1000,'selected_experiment':'split_cv_80_10','selected_model':'RandomForest','selected_parameters':PARAMETERS,
        'selection_basis':'selected evaluated RF using training CV; reconstructed from original export and verified on all saved holdout predictions',
        'runtime':runtime,'model_sha256':sha,'poi_rule_sha256':RULE_HASH,'poi_snapshot_sha256':EXPECTED_SNAPSHOT,
        'training_dataset_sha256':EXPECTED_DATASET,'train_sites':len(train),'test_sites':len(test),'maximum_prediction_difference':maximum,
        'source_archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        'source_hashes':{name:hashlib.sha256(value).hexdigest() for name,value in raw.items()},
        'metrics':{'MAE':float(mean_absolute_error(target,actual)),'RMSE':float(np.sqrt(mean_squared_error(target,actual))),'R2':float(r2_score(target,actual)),'rounded_MAE':float(mean_absolute_error(target,rounded))},
        'limitations':['research prototype; category-dominated predictions','larger sites have higher errors','many inferred site categories','no independent final test; previously inspected experiments']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'prediction_fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n',encoding='utf-8')
    print(f'Restored {len(features)}-input RF; all {len(test)} saved predictions matched. Maximum raw difference: {maximum:.3g}')
    print('Model SHA256:',sha)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--output',type=Path,default=Path('model/verified_poi_state_rf80_cv10'));args=parser.parse_args()
    restore(args.archive,args.output)
