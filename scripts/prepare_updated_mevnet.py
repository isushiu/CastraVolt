"""Engineer the fresh MEVnet export using the application's exact OSM feature code."""
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from castravolt.features import RULES, RULE_VERSION, extract_counts
from castravolt.local_pois import load_snapshot, query_snapshot
from castravolt.locations import resolve_state

ROOT = Path(__file__).resolve().parents[1]
RADIUS = 1000
RULE_HASH = hashlib.sha256(json.dumps({'tags':RULES,'method':RULE_VERSION,'radius':RADIUS},sort_keys=True).encode()).hexdigest()
TRAINING_FIELDS = [*RULES, 'category', 'state', 'total_planned_chargers']


def prepare(source, snapshot):
    row = dict(source)
    row.update({key: None for key in RULES})
    issues = []
    existing = row.get('number_of_existing_ev_charger_s')
    proposed = row.get('number_of_proposed_ev_charger__')
    valid_counts = all(type(v) is int and v >= 0 for v in [existing, proposed])
    row['total_planned_chargers'] = existing + proposed if valid_counts else None
    if not valid_counts:
        issues.append('invalid_or_missing_charger_count')
    elif existing + proposed == 0:
        issues.append('zero_total_outside_positive_capacity_scope')
    state = str(row.get('state', '')).strip().upper()
    row.update(poi_radius_metres=RADIUS, poi_rule_version=RULE_VERSION, poi_rule_sha256=RULE_HASH,
               poi_snapshot_sha256=snapshot['_snapshot_sha256'], poi_source_timestamp=snapshot['source_timestamp'],
               state_from_coordinates=None, poi_extraction_status='not_prepared')
    lat, lon = row.get('latitude'), row.get('longitude')
    valid_coordinates = all(isinstance(v, (int, float)) and math.isfinite(v) for v in [lat, lon])
    if not valid_coordinates or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        issues.append('invalid_or_missing_coordinates')
        row['poi_extraction_status'] = 'invalid_coordinates'
    else:
        try:
            coordinate_state = resolve_state(lat, lon)
            row['state_from_coordinates'] = coordinate_state
            if coordinate_state != state:
                issues.append('source_state_differs_from_coordinate_state')
        except HTTPException:
            issues.append('coordinates_outside_supported_state_boundary')
        try:
            row.update(extract_counts(query_snapshot(snapshot, lat, lon, radius_metres=RADIUS), lat, lon, radius_metres=RADIUS))
            row['poi_extraction_status'] = 'complete'
        except HTTPException as error:
            if error.status_code != 422:
                raise
            issues.append('full_radius_outside_snapshot_coverage')
            row['poi_extraction_status'] = 'outside_snapshot_coverage'
    row['nearby_total_poi_count'] = sum(row[key] for key in RULES) if row['poi_extraction_status'] == 'complete' else None
    row['category'] = str(row.get('category') or 'Unknown').strip() or 'Unknown'
    row['state'] = state
    row['preprocessing_eligible'] = not issues
    row['preparation_issues'] = ';'.join(issues)
    return row


def main():
    folder = ROOT / 'data' / 'updated_mevnet_source'
    features = json.loads((folder / 'features.json').read_text(encoding='utf-8'))
    fields = [f['name'] for f in json.loads((folder / 'layer_metadata.json').read_text())['fields']]
    snapshot = load_snapshot()
    override_path = folder / 'verified_category_overrides.json'
    overrides = json.loads(override_path.read_text(encoding='utf-8')) if override_path.exists() else {}
    for name in ['deduced_category_overrides.json','researched_category_overrides.json']:
        path=folder/name
        if path.exists():
            extra=json.loads(path.read_text(encoding='utf-8'))
            if set(extra)&set(overrides):raise ValueError('Conflicting category override sources')
            overrides.update(extra)
    from castravolt.projects import SITE_CATEGORIES
    if any(value['category'] not in SITE_CATEGORIES for value in overrides.values()):
        raise ValueError('Override outside agreed host category vocabulary')
    rows = []
    for i, feature in enumerate(features, 1):
        prepared = prepare(feature['attributes'], snapshot)
        override = overrides.get(str(feature['attributes']['objectid']))
        if override and not feature['attributes'].get('category'):
            source = feature['attributes']
            assert all(source[key] == override[key] for key in ['location','state','latitude','longitude'])
            prepared['category'] = override['category']
        rows.append(prepared)
        if i % 250 == 0:
            print(f'Prepared {i}/{len(features)} sites', flush=True)
    # Detailed records stay outside the lean ML matrix for traceability and splits.
    output = folder / 'prepared_sites_1km.csv'
    fields += [key for key in rows[0] if key not in fields]
    temporary = output.with_suffix('.csv.tmp')
    with temporary.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with temporary.open(encoding='utf-8-sig', newline='') as handle:
        exported = list(csv.DictReader(handle))
    assert len(exported) == len(features)
    assert len({row['objectid'] for row in exported}) == len(features)
    for record, original, saved in zip(rows, features, exported):
        assert all(record[key] == value for key, value in original['attributes'].items() if key not in {'category','state'})
        assert all(saved[key] == ('' if record[key] is None else str(record[key])) for key in fields)
        if record['poi_extraction_status'] == 'complete':
            assert all(type(record[key]) is int and record[key] >= 0 for key in RULES)
        else:
            assert all(record[key] is None for key in RULES)
        assert record['total_planned_chargers'] == record['number_of_existing_ev_charger_s'] + record['number_of_proposed_ev_charger__']
    temporary.replace(output)
    eligible=[]; excluded=[]; seen=set(); assignments=[]
    originals={feature['attributes']['objectid']:feature['attributes'] for feature in features}
    for row in rows:
        if not row['preprocessing_eligible']:
            excluded.append(row)
            continue
        identity=tuple(row.get(key) for key in ['latitude','longitude','location','state','category',
                        'number_of_existing_ev_charger_s','number_of_proposed_ev_charger__'])
        if identity in seen:
            row=dict(row,preprocessing_eligible=False,preparation_issues='duplicate_site_observation')
            excluded.append(row)
            continue
        seen.add(identity)
        eligible.append({key:row[key] for key in TRAINING_FIELDS})
        assignments.append({'training_row':len(eligible)-1,'objectid':row['objectid'],
                            'latitude':row['latitude'],'longitude':row['longitude'],
                            'coordinate_group':f"{row['latitude']:.7f}|{row['longitude']:.7f}",
                            'status':row['status'],
                            'source_category_missing':not bool(originals[row['objectid']].get('category')),
                            'category_source':overrides.get(str(row['objectid']),{}).get('source',
                                'official MEVnet' if originals[row['objectid']].get('category') else 'unresolved')})
    training_output=ROOT / 'data' / 'ML Data' / 'updated_mevnet.csv'
    try:
        with training_output.open('ab'):
            pass
    except PermissionError:
        training_output=training_output.with_name('updated_mevnet_1km.csv')
        print('Requested filename is locked; saving completed data to updated_mevnet_1km.csv',flush=True)
    for path, records, columns in [(training_output,eligible,TRAINING_FIELDS),
            (folder/'excluded_sites_1km.csv',excluded,fields),
            (folder/'training_row_provenance_1km.csv',assignments,list(assignments[0]))]:
        with path.open('w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader();writer.writerows(records)
    with training_output.open(encoding='utf-8-sig',newline='') as handle:
        verified=list(csv.DictReader(handle))
    assert len(verified)==len(eligible) and len(eligible)+len(excluded)==len(rows)
    assert all(list(row)==TRAINING_FIELDS and all(value!='' for value in row.values()) for row in verified)
    assert all(int(row['total_planned_chargers'])>0 for row in verified)
    manifest = {
        'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'rows': len(rows), 'columns': len(fields),
        'poi_statuses': dict(Counter(row['poi_extraction_status'] for row in rows)),
        'preprocessing_eligible': sum(row['preprocessing_eligible'] for row in rows),
        'issues': dict(Counter(issue for row in rows for issue in row['preparation_issues'].split(';') if issue)),
        'radius_metres': RADIUS, 'rule_version': RULE_VERSION, 'rule_sha256': RULE_HASH,
        'snapshot_sha256': snapshot['_snapshot_sha256'], 'osm_timestamp': snapshot['source_timestamp'],
        'osm_attribution': 'OpenStreetMap contributors; Geofabrik extract; ODbL 1.0',
        'source_layer': json.loads((folder / 'manifest.json').read_text())['source_layer'],
        'training_file':str(training_output.relative_to(ROOT)),
        'training_rows':len(eligible),'training_columns':TRAINING_FIELDS,'excluded_rows':len(excluded),
        'excluded_reasons':dict(Counter(row['preparation_issues'] for row in excluded)),
        'unknown_categories_retained':sum(row['category']=='Unknown' for row in eligible),
        'category_overrides':len(overrides),
        'official_coverage_category_overrides':sum(value.get('source')=='MEVnet dashboard coverage layer' for value in overrides.values()),
        'osm_inferred_categories':sum(value.get('source','').startswith('OSM') for value in overrides.values()),
        'description_deduced_categories':sum(value.get('source','').startswith('Deduced') for value in overrides.values()),
        'researched_deduced_categories':sum(value.get('source','').startswith('Researched') for value in overrides.values()),
        'constant_training_columns':[key for key in TRAINING_FIELDS if len({row[key] for row in eligible})==1],
        'csv_sha256': hashlib.sha256(training_output.read_bytes()).hexdigest(),
        'target': 'existing + proposed, using the user-authorised additional-proposed assumption',
        'adoption': 'Excluded from this training dataset; registration data retained separately for dashboard use.',
        'eligibility_meaning': 'Preprocessing checks only; does not certify target validity or prediction quality.',
        'nearby_total_poi_count_meaning': 'Sum of category counts; overlapping facility categories may double-count entities.',
    }
    (folder / 'preparation_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
