"""Load the trusted evaluated pipeline and verify its serving contract before use."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib,json,math,io
from pathlib import Path


def display_count(raw):
    if not math.isfinite(raw):raise ValueError('Non-finite prediction')
    return max(1,math.floor(raw+.5))


@dataclass(frozen=True)
class VerifiedModel:
    pipeline:object
    features:tuple
    sha256:str
    version:str
    radius_metres:int
    rule_sha256:str
    snapshot_sha256:str
    profile:str

    def predict(self,values):
        import pandas as pd
        if set(values)!=set(self.features):raise ValueError('Model input schema differs')
        raw=float(self.pipeline.predict(pd.DataFrame([values],columns=self.features))[0])
        display_count(raw)
        return raw


def load_model(settings):
    folder=Path(settings.model_directory).resolve()
    paths=[folder/'evaluated_pipeline.joblib',folder/'manifest.json',folder/'prediction_fixtures.json']
    hashes=tuple(hashlib.sha256(path.read_bytes()).hexdigest() for path in paths)
    return _load(str(folder),hashes)


@lru_cache(maxsize=2)
def _load(directory,hashes):
    import joblib,numpy as np,pandas as pd,sklearn
    from castravolt.features import ModelFeatures,RADIUS,RULE_HASH,RULES
    from castravolt.local_pois import load_snapshot
    folder=Path(directory)
    raw_files=[(folder/name).read_bytes() for name in ['evaluated_pipeline.joblib','manifest.json','prediction_fixtures.json']]
    if tuple(hashlib.sha256(raw).hexdigest() for raw in raw_files)!=hashes:raise ValueError('Artifact changed during startup')
    manifest=json.loads(raw_files[1])
    if manifest['model_sha256']!=hashes[0] or manifest['status']!='prediction_parity_verified':raise ValueError('Artifact checksum/status differs')
    profile=manifest.get('serving_profile','poi_category_state_rf')
    if profile not in {'poi_category_state_rf','poi_only_xgb','poi_category_rf'}:raise ValueError('Unsupported serving profile')
    runtime={'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__}
    if profile=='poi_only_xgb':
        import xgboost
        runtime['xgboost']=xgboost.__version__
    if runtime!=manifest['runtime']:raise ValueError('Model runtime is incompatible')
    expected_features=(list(RULES) if profile=='poi_only_xgb' else list(RULES)+['category'] if profile=='poi_category_rf' else list(ModelFeatures.model_fields))
    if manifest['features']!=expected_features:raise ValueError('Model feature schema differs')
    snapshot=load_snapshot()
    if (manifest.get('poi_radius_metres')!=RADIUS or manifest.get('use_adoption') is not False
        or manifest.get('poi_rule_sha256')!=RULE_HASH
        or manifest.get('poi_snapshot_sha256')!=snapshot['_snapshot_sha256']):
        raise ValueError('Model extraction contract differs from the installed 1 km source')
    expected=({'model__n_estimators':100,'model__max_depth':3,'model__learning_rate':0.03,'model__subsample':1.0,
        'model__colsample_bytree':0.8,'model__reg_lambda':5} if profile=='poi_only_xgb' else
        {'model__n_estimators':600,'model__max_depth':5,'model__min_samples_leaf':10,'model__max_features':1.0})
    if manifest['selected_parameters']!=expected:raise ValueError('This is not the selected evaluated model')
    # Never deserialize until trusted source metadata and the file checksum agree.
    bundle=joblib.load(io.BytesIO(raw_files[0]));pipeline=bundle['pipeline']
    if bundle['features']!=manifest['features'] or list(pipeline.feature_names_in_)!=manifest['features']:raise ValueError('Artifact inputs differ')
    if any(pipeline.get_params()[key]!=value for key,value in expected.items()):raise ValueError('Fitted pipeline parameters differ')
    if profile=='poi_only_xgb':
        from xgboost import XGBRegressor
        if not isinstance(pipeline.named_steps['model'],XGBRegressor):raise ValueError('Model family differs')
    else:
        from sklearn.ensemble import RandomForestRegressor
        if not isinstance(pipeline.named_steps['model'],RandomForestRegressor):raise ValueError('Model family differs')
    metadata=bundle['metadata']
    if metadata.get('poi_radius_metres')!=RADIUS or metadata.get('use_adoption') is not False or metadata.get('rounding') not in {'nearest_half_up','nearest_half_up_minimum_1'}:raise ValueError('Artifact context/rounding differs')
    pipeline.set_params(model__n_jobs=1)
    prefix=('xgb-poi-only-80-cv10-1km-' if profile=='poi_only_xgb' else 'rf-poi-category-80-cv10-1km-' if profile=='poi_category_rf' else 'rf80-cv10-1km-')
    model=VerifiedModel(pipeline,tuple(manifest['features']),hashes[0],prefix+hashes[0][:12],
                        RADIUS,RULE_HASH,snapshot['_snapshot_sha256'],profile)
    fixtures=json.loads(raw_files[2])
    if len(fixtures)!=10:raise ValueError('Parity fixtures are incomplete')
    for row in fixtures:
        raw=model.predict({key:row[key] for key in model.features})
        if not math.isclose(raw,row['expected_raw_prediction'],rel_tol=0,abs_tol=1e-8) or display_count(raw)!=row['expected_half_up_count']:
            raise ValueError('Serving predictions do not match verified fixtures')
    return model
