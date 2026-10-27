"""Descriptive POI-signal checks on the trusted reconstructed Colab experiments."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'model/poi_category_state_1km_full'
OUT=ROOT/'model/verified_poi_state_rf80_cv10'


def main():
    data=pd.read_csv(SOURCE/'prepared_sites.csv').sort_values('_source_row')
    bundle=joblib.load(OUT/'evaluated_pipeline.joblib')
    features=bundle['features'];rf=bundle['pipeline']
    assignment=pd.read_csv(SOURCE/'holdout_assignments.csv')
    split=assignment[np.isclose(assignment.train_fraction,.8)]
    training=data[data._source_row.isin(split[split.partition=='train'].source_row)].reset_index(drop=True)
    test=data[data._source_row.isin(split[split.partition=='test'].source_row)]
    Xtest=test[features];target=test.total_planned_chargers.to_numpy()
    foldmap=pd.read_csv(SOURCE/'cv_assignments.csv')
    foldmap=foldmap[(foldmap.experiment=='split_cv_80_10')&(foldmap.stage=='tuning')].set_index('source_row').fold
    fold_ids=foldmap.loc[training._source_row].to_numpy()
    rows=[]
    for label,keep in [('category_state_only',features[8:]),('POIs_only',features[:8])]:
        predictions=np.empty(len(training))
        for fold in range(10):
            train=np.flatnonzero(fold_ids!=fold);valid=np.flatnonzero(fold_ids==fold)
            pipeline=clone(rf)
            columns=pipeline.named_steps['preprocess'].named_steps['columns']
            columns.transformers=[(name,transform,[key for key in keys if key in keep])
                for name,transform,keys in columns.transformers if any(key in keep for key in keys)]
            pipeline.fit(training.iloc[train][features],training.iloc[train].total_planned_chargers)
            pred=pipeline.predict(training.iloc[valid][features]);predictions[valid]=pred
            rows.append({'configuration':label,'fold':fold,'MAE':float(mean_absolute_error(training.iloc[valid].total_planned_chargers,pred))})
        print(label,'OOF MAE',mean_absolute_error(training.total_planned_chargers,predictions),flush=True)
    summary=pd.DataFrame(rows).groupby('configuration').MAE.agg(['mean','std']).to_dict('index')
    selected_scores=pd.read_csv(SOURCE/'selected_hyperparameters.csv')
    full_score=selected_scores[(selected_scores.experiment=='split_cv_80_10')&(selected_scores.model=='RandomForest')].iloc[0].training_cv_MAE
    summary['POIs_category_state_selected']={'mean':float(full_score),'source':'saved training-CV score'}
    results={}
    models={'RandomForest':rf}
    # XGBoost is optional for the diagnostic; install the exported version first.
    try:
        import xgboost
    except ImportError:
        xgboost=None
    if xgboost is not None:
        assert xgboost.__version__=='3.4.1'
        selected=pd.read_csv(SOURCE/'selected_hyperparameters.csv')
        row=selected[(selected.experiment=='split_cv_80_10')&(selected.model=='XGBoost')].iloc[0]
        params={key.removeprefix('model__'):value for key,value in json.loads(row.parameters).items()}
        estimator=xgboost.XGBRegressor(**params,objective='reg:squarederror',random_state=42,n_jobs=1,tree_method='hist')
        xgb=clone(rf).set_params(model=estimator)
        xgb.fit(training[features],training.total_planned_chargers)
        saved=pd.read_csv(SOURCE/'holdout_predictions.csv')
        saved=saved[(saved.experiment=='split_cv_80_10')&(saved.model=='XGBoost')].set_index('source_row')
        difference=float(np.max(np.abs(xgb.predict(Xtest)-saved.loc[test._source_row].raw_prediction)))
        assert difference<1e-6,difference
        models['XGBoost']=xgb
    for label,model in models.items():
        base=float(mean_absolute_error(target,model.predict(Xtest)))
        permutation={}
        for block,columns in [('all_POIs',features[:8]),('category',['category']),('state',['state'])]:
            values=[]
            for seed in range(20):
                shuffled=Xtest.copy();order=np.random.default_rng(seed).permutation(len(shuffled))
                shuffled[columns]=Xtest.iloc[order][columns].to_numpy()
                values.append(float(mean_absolute_error(target,model.predict(shuffled))))
            permutation[block]={'mean_MAE':float(np.mean(values)),
                'mean_increase_over_original':float(np.mean(values)-base),'std_MAE':float(np.std(values))}
        results[label]={'original_test_MAE':base,'repeated_block_permutation':permutation}
    report={'training_cv_ablation':summary,'heldout_permutation':results,
        'method':'Same saved 80% training set and CV10 folds; ablations retain RF selected parameters. Held-out feature blocks jointly shuffled over 20 deterministic seeds.',
        'limitations':'Exploratory diagnosis after test inspection, not independent final selection; correlated features and inferred categories limit interpretation.'}
    pd.DataFrame(rows).to_csv(OUT/'training_feature_ablation.csv',index=False)
    (OUT/'poi_signal_diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
