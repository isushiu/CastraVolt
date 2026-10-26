"""Exercise the notebook's actual upload branch with Colab-style returned names."""
import json
import sys
import types
import tempfile
from pathlib import Path

nb = json.loads(Path('notebooks/CastraVolt_ML_Training.ipynb').read_text(encoding='utf-8'))
source = next(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code'
              and "uploaded = files.upload()" in ''.join(c['source']))
source = source.split('elif DATA_SOURCE')[0]
names = ['mevnet_ev_charging_demand_labelled_dataset.csv','ev_registration2024.csv',
         'ev_registration2025.csv','vehicles_2026.csv']
with tempfile.TemporaryDirectory(dir=Path('tmp').resolve()) as tmp:
    source = source.replace("Path('/content/castravolt_input')",'destination')
    for suffix in ['', ' (3)', ' (12)']:
        payload = {Path(n).stem+suffix+'.csv':n.encode() for n in names}
        fake = types.ModuleType('google.colab')
        fake.files = types.SimpleNamespace(upload=lambda: payload)
        sys.modules['google.colab'] = fake
        ns = {'DATA_SOURCE':'upload','FILES':names,'Path':Path,'destination':Path(tmp)}
        exec(source,ns)
        for name in names:
            assert (Path(tmp)/name).read_bytes()==name.encode()
    payload = {n:n.encode() for n in names[1:]}
    try:
        exec(source,ns)
        raise AssertionError('Missing file was accepted')
    except FileNotFoundError:
        pass
    payload = {n:n.encode() for n in names}
    payload['ev_registration2024 (3).csv'] = b'ambiguous'
    try:
        exec(source,ns)
        raise AssertionError('Ambiguous file was accepted')
    except ValueError:
        pass
print('PASS: original and repeated-upload names; missing and ambiguous uploads rejected')
