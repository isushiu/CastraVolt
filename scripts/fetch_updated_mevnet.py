"""Export public MEVnet attributes for Selangor and Kuala Lumpur without imputation."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from castravolt.network import tls_context

ROOT = Path(__file__).resolve().parents[1]
LAYER = 'https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/MEVnet_EVCB/FeatureServer/0'
WHERE = "UPPER(state) LIKE '%SELANGOR%' OR UPPER(state) LIKE '%KUALA LUMPUR%'"


def fetch(path='', **params):
    url = LAYER + path + '?' + urlencode({'f': 'json', **params})
    with urlopen(Request(url, headers={'User-Agent': 'CastraVolt research dataset export'}),
                 context=tls_context(), timeout=60) as response:
        data = json.load(response)
    if 'error' in data:
        raise RuntimeError(data['error'])
    return data


def main():
    metadata = fetch()
    oid = metadata['objectIdField']
    identifiers = sorted(fetch('/query', where=WHERE, returnIdsOnly='true')['objectIds'])
    if not identifiers or len(identifiers) != len(set(identifiers)):
        raise RuntimeError('Missing or duplicated source object IDs')
    features = []
    # Keep GET URLs below the GIS web server's request-length limit.
    for offset in range(0, len(identifiers), 100):
        batch = identifiers[offset:offset + 100]
        response = fetch('/query', objectIds=','.join(map(str, batch)), outFields='*',
                         returnGeometry='true', outSR=4326)
        if response.get('exceededTransferLimit'):
            raise RuntimeError('Source response was truncated')
        if sorted(row['attributes'][oid] for row in response['features']) != batch:
            raise RuntimeError('Source IDs do not match downloaded batch')
        features.extend(response['features'])
    if sorted(fetch('/query', where=WHERE, returnIdsOnly='true')['objectIds']) != identifiers:
        raise RuntimeError('Source membership changed during download; retry')
    features.sort(key=lambda row: row['attributes'][oid])
    rows = [row['attributes'] for row in features]
    allowed = {'SELANGOR', 'W.P. KUALA LUMPUR', 'KUALA LUMPUR',
               'WILAYAH PERSEKUTUAN KUALA LUMPUR'}
    if any(str(row.get('state', '')).strip().upper() not in allowed for row in rows):
        raise RuntimeError('Unexpected state label; inspect before exporting')
    folder = ROOT / 'data' / 'updated_mevnet_source'
    folder.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'data' / 'ML Data' / 'updated_mevnet.csv'
    fields = [field['name'] for field in metadata['fields']]
    with output.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)
    (folder / 'layer_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    (folder / 'features.json').write_text(json.dumps(features, ensure_ascii=False), encoding='utf-8')
    manifest = {
        'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_page': 'https://www.planmalaysia.gov.my/mevnet/',
        'source_layer': LAYER, 'where': WHERE, 'rows': len(rows), 'columns': len(fields),
        'states': dict(Counter(row['state'] for row in rows)),
        'statuses': dict(Counter(row.get('status') for row in rows)),
        'null_counts': {key: sum(row.get(key) is None for row in rows) for key in fields},
        'csv_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'processing': 'Original attributes and nulls preserved; all statuses retained; state filter only.',
        'poi_features': 'Not present in this official layer; must be generated consistently with the app.',
    }
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with output.open(encoding='utf-8-sig', newline='') as handle:
        exported = list(csv.DictReader(handle))
    assert len(exported) == len(identifiers)
    assert len({row[oid] for row in exported}) == len(identifiers)
    assert all(exported[i][key] == ('' if row.get(key) is None else str(row[key]))
               for i, row in enumerate(rows) for key in fields)
    print(json.dumps({key: manifest[key] for key in ['rows', 'columns', 'states', 'statuses', 'csv_sha256']}, indent=2))
    print(output)


if __name__ == '__main__':
    main()
