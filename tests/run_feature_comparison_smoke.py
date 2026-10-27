"""Execute every cell of the feature-comparison notebook in smoke mode."""
import json,os,sys,hashlib,re,io,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root);os.environ['MPLBACKEND']='Agg'
optional=root/'tmp/ml_validation_packages'
if optional.exists():sys.path.append(str(optional))
notebook=json.loads((root/'notebooks/CastraVolt_Feature_Comparison.ipynb').read_text(encoding='utf-8'))
assert re.sub(r' \(\d+\)(?=\.csv$)','','updated_mevnet (3).csv')=='updated_mevnet.csv'
model=root/'model/verified_poi_state_rf80_cv10/evaluated_pipeline.joblib'
original=hashlib.sha256(model.read_bytes()).hexdigest()
namespace={}
for index,cell in enumerate(notebook['cells']):
    if cell['cell_type']!='code':continue
    source=''.join(cell['source'])
    if "RUN_MODE = 'full'" in source:
        source=source.replace("RUN_MODE = 'full'","RUN_MODE = 'smoke'").replace("DATA_SOURCE = 'upload'","DATA_SOURCE = 'local'")
        source+="\nOUTPUT_DIR=Path('tmp/feature_comparison_smoke');OUTPUT_DIR.mkdir(parents=True,exist_ok=True)\nPERMUTATION_REPEATS=3\nBOOTSTRAP_REPEATS=200\nAUTO_DOWNLOAD=False\n"
    print('Executing cell',index,flush=True)
    exec(compile(source,f'notebook-cell-{index}','exec'),namespace)
    if index==1:namespace['display']=lambda *args:None
assert len(namespace['scores'])==16
assert len(namespace['predictions'])==16*380
assert set(namespace['models'])=={(.8,v,m) for v in namespace['FEATURE_SETS'] for m in ['RandomForest','XGBoost']}
assert namespace['source_hashes']==namespace['KNOWN_HASHES']
assert hashlib.sha256(model.read_bytes()).hexdigest()==original
with zipfile.ZipFile('C:/Users/User/Downloads/poi_category_state_1km_full.zip') as original_export:
    pd=namespace['pd']
    expected=pd.read_csv(io.BytesIO(original_export.read('poi_category_state_1km_full/holdout_assignments.csv')))
    expected=expected[expected.train_fraction==.8]
    actual=pd.DataFrame(namespace['assignments'])
    assert expected.sort_values('source_row').partition.tolist()==actual.sort_values('source_row').partition.tolist()
    expected_cv=pd.read_csv(io.BytesIO(original_export.read('poi_category_state_1km_full/cv_assignments.csv')))
    expected_cv=expected_cv[(expected_cv.experiment=='split_cv_80_10')&(expected_cv.stage=='tuning')]
    actual_cv=pd.DataFrame(namespace['cv_assignments'])
    assert expected_cv.sort_values('source_row').fold.tolist()==actual_cv.sort_values('source_row').fold.tolist()
print('All cells passed. 14 candidates + 2 baselines; 6,080 predictions. Original split/folds and serving model unchanged.',flush=True)
