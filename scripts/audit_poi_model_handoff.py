"""Verify the owner's Colab result archive and export its evaluated 1 km RF model.

Use the exported sklearn/numpy/pandas/xgboost versions. Load only the trusted
candidate produced by the project notebook. Never deploy the default candidate
as though it were the tuned, held-out evaluated pipeline.
"""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'model/poi_category_state_1km_full'
OUTPUT=ROOT/'model/verified_poi_state_rf80_cv10'
EXPERIMENT='split_cv_80_10'


def rounded(values):
    values=np.asarray(values)
    if not np.isfinite(values).all():raise ValueError('Nonfinite predictions')
    return np.maximum(1,np.floor(values+.5)).astype(int)


def metrics(actual,pred):
    return {'MAE':float(mean_absolute_error(actual,pred)),
            'RMSE':float(np.sqrt(mean_squared_error(actual,pred))),
            'R2':float(r2_score(actual,pred)),
            'rounded_MAE':float(mean_absolute_error(actual,rounded(pred)))}


def main():
    meta=json.loads((SOURCE/'run_metadata.json').read_text())
    expected_runtime={name:meta['versions'][name] for name in ['sklearn','numpy','pandas']}
    runtime={'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}
    if runtime!=expected_runtime:raise RuntimeError(f'Use exported runtime: {expected_runtime}')
    assert meta['run_mode']=='full' and meta['use_adoption'] is False and meta['poi_radius_metres']==1000
    for name,expected in meta['source_hashes'].items():
        assert hashlib.sha256((ROOT/'data/ML Data'/name).read_bytes()).hexdigest()==expected
    data=pd.read_csv(SOURCE/'prepared_sites.csv').sort_values('_source_row')
    current=pd.read_csv(ROOT/'data/ML Data/updated_mevnet.csv')
    features=meta['features']
    assert len(features)==10 and 'state_ev_registrations' not in features
    assert data._source_row.tolist()==list(range(len(current)))
    pd.testing.assert_frame_equal(data[features+['total_planned_chargers']].reset_index(drop=True),
                                  current[features+['total_planned_chargers']],check_dtype=False)
    assignments=pd.read_csv(SOURCE/'holdout_assignments.csv')
    predictions=pd.read_csv(SOURCE/'holdout_predictions.csv')
    scores=pd.read_csv(SOURCE/'evaluation_scores.csv')
    selected=pd.read_csv(SOURCE/'selected_hyperparameters.csv')
    folds=pd.read_csv(SOURCE/'cv_assignments.csv')
    assert len(scores)==96 and scores[['experiment','model']].drop_duplicates().shape[0]==44
    assert predictions[['experiment','model','source_row']].duplicated().sum()==0
    actual_by_row=data.set_index('_source_row').total_planned_chargers
    assert np.array_equal(predictions.actual,actual_by_row.loc[predictions.source_row])
    assert np.array_equal(predictions.displayed_count,rounded(predictions.raw_prediction))
    for row in scores.itertuples():
        p=predictions[(predictions.experiment==row.experiment)&(predictions.model==row.model)&(predictions.fold==row.fold)]
        assert len(p)==row.n_test
        for key,value in metrics(p.actual,p.raw_prediction).items():
            assert np.isclose(value,getattr(row,key),atol=1e-6,rtol=0),(row.experiment,row.model,key)
    for fraction in [.5,.7,.8]:
        split=assignments[np.isclose(assignments.train_fraction,fraction)]
        assert split.source_row.is_unique and set(split.source_row)==set(data._source_row)
        assert not set(split[split.partition=='train'].coordinate_group)&set(split[split.partition=='test'].coordinate_group)
        for suffix in ['5','10']:
            exp=f'split_cv_{int(fraction*100)}_{suffix}'
            tuning=folds[(folds.experiment==exp)&(folds.stage=='tuning')]
            assert set(tuning.source_row)==set(split[split.partition=='train'].source_row)
            assert tuning.source_row.is_unique
            g=data.set_index('_source_row').loc[tuning.source_row,'_coordinate_group'].to_numpy()
            assert pd.DataFrame({'group':g,'fold':tuning.fold.to_numpy()}).groupby('group').fold.nunique().max()==1
    for row in selected.itertuples():
        search=pd.read_csv(SOURCE/f'{row.experiment}_{row.model}_search.csv')
        assert np.isclose(-search.mean_test_score.max(),row.training_cv_MAE,atol=1e-10)
    print('Verified dataset identity, metrics, rounding, split groups and training-only tuning.',flush=True)

    # Selection is based on training-CV MAE within the chosen 80/20 + CV10
    # protocol. All test outcomes were already inspected: do not claim a new
    # untouched final selection test or compare train/test fractions as candidates.
    comparison=selected[selected.experiment==EXPERIMENT].sort_values('training_cv_MAE')
    assert comparison.iloc[0].model=='RandomForest'
    params=json.loads(comparison.iloc[0].parameters)
    bundle=joblib.load(SOURCE/'candidate_model.joblib')
    assert bundle['features']==features and list(bundle['pipeline'].feature_names_in_)==features
    original_matches=all(bundle['pipeline'].get_params()[key]==value for key,value in params.items())
    split=assignments[np.isclose(assignments.train_fraction,.8)]
    train=data._source_row.isin(split[split.partition=='train'].source_row)
    test=data._source_row.isin(split[split.partition=='test'].source_row)
    test_rows=data.loc[test,'_source_row']
    pipeline=clone(bundle['pipeline']).set_params(**params)
    pipeline.fit(data.loc[train,features],data.loc[train,'total_planned_chargers'])
    pred=pipeline.predict(data.loc[test,features])
    saved=predictions[(predictions.experiment==EXPERIMENT)&(predictions.model=='RandomForest')].set_index('source_row')
    expected=saved.loc[test_rows,'raw_prediction'].to_numpy()
    max_diff=float(np.max(np.abs(pred-expected)))
    if max_diff>1e-8:raise RuntimeError(f'RF reconstruction does not match: {max_diff}')
    target=data.loc[test,'total_planned_chargers'].to_numpy()
    result=data.loc[test,['_source_row',*features,'total_planned_chargers']].copy()
    result['raw_prediction']=pred;result['displayed_count']=rounded(pred)
    result['absolute_error']=np.abs(target-pred)
    result['rounded_absolute_error']=np.abs(target-rounded(pred))
    OUTPUT.mkdir(exist_ok=True)
    artifact_metadata={**meta,'artifact_role':'evaluated 80%-training model reconstructed from saved selected parameters',
                       'selection_basis':'training-CV MAE within split_cv_80_10; test scores already inspected',
                       'selected_parameters':params}
    joblib.dump({'pipeline':pipeline,'features':features,'metadata':artifact_metadata},OUTPUT/'evaluated_pipeline.joblib')
    positions=np.linspace(0,len(pred)-1,10).round().astype(int)
    chosen=np.argsort(pred)[positions]
    fixtures=result.iloc[chosen][['_source_row',*features]].copy()
    fixtures['expected_raw_prediction']=pred[chosen]
    fixtures['expected_half_up_count']=rounded(pred[chosen])
    fixtures.to_json(OUTPUT/'prediction_fixtures.json',orient='records',indent=2)
    result.to_csv(OUTPUT/'heldout_site_errors.csv',index=False)
    cv=selected.pivot(index='experiment',columns='model',values='training_cv_MAE')
    errors={}
    for label,mask in [('1_to_4',target<=4),('5_to_9',(target>=5)&(target<=9)),('10_plus',target>=10)]:
        errors[label]={'sites':int(mask.sum()),**metrics(target[mask],pred[mask])}
    frequency=pd.Series(rounded(pred)).value_counts().sort_index().to_dict()
    # Descriptive, not a model-selection criterion: held-out sensitivity of the
    # fixed model to jointly shuffled POIs, category and state.
    permutation={};rng=np.random.default_rng(42);X=data.loc[test,features].copy()
    for label,columns in [('all_POIs',features[:8]),('category',['category']),('state',['state'])]:
        shuffled=X.copy();order=rng.permutation(len(X))
        shuffled[columns]=X.iloc[order][columns].to_numpy()
        permutation[label]=float(mean_absolute_error(target,pipeline.predict(shuffled)))
    preparation=json.loads((ROOT/'data/updated_mevnet_source/preparation_manifest.json').read_text())
    report={'status':'prediction_parity_verified','features':features,'use_adoption':False,'poi_radius_metres':1000,
        'poi_rule_sha256':preparation['rule_sha256'],'poi_snapshot_sha256':preparation['snapshot_sha256'],
        'training_dataset_sha256':meta['source_hashes']['updated_mevnet.csv'],
        'selected_experiment':EXPERIMENT,'selected_model':'RandomForest','selected_parameters':params,
        'selection_basis':'lower training-CV MAE within the 80/20 + 10-fold protocol; not best test split',
        'training_cv_MAE':float(comparison.iloc[0].training_cv_MAE),
        'xgboost_training_cv_MAE':float(comparison.iloc[1].training_cv_MAE),
        'rf_wins_training_cv_setups':int((cv.RandomForest<cv.XGBoost).sum()),
        'original_candidate_matches_selected_parameters':original_matches,
        'original_candidate_parameters':{k:bundle['pipeline'].get_params()[k] for k in params},
        'train_sites':int(train.sum()),'test_sites':int(test.sum()),'maximum_prediction_difference':max_diff,
        'metrics':metrics(target,pred),'error_by_target_band':errors,
        'rounded_prediction_frequency':{str(k):int(v) for k,v in frequency.items()},
        'rounded_exact_fraction':float(np.mean(rounded(pred)==target)),
        'rounded_within_1_fraction':float(np.mean(np.abs(rounded(pred)-target)<=1)),
        'rounded_within_2_fraction':float(np.mean(np.abs(rounded(pred)-target)<=2)),
        'permuted_heldout_MAE':permutation,'runtime':runtime,
        'model_sha256':hashlib.sha256((OUTPUT/'evaluated_pipeline.joblib').read_bytes()).hexdigest(),
        'source_hashes':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in
                         ['candidate_model.joblib','prepared_sites.csv','holdout_predictions.csv','selected_hyperparameters.csv']},
        'limitations':meta['limitations']+['selected after inspecting overlapping experiments; no fresh final test',
                                          'research prototype; capacity accuracy remains limited']}
    (OUTPUT/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
