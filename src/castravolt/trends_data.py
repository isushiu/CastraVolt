"""Reproducible, versioned monthly import. Raw vehicle records never enter the API."""
import csv,hashlib,json
from collections import Counter
from datetime import datetime
from importlib.resources import files
from pathlib import Path

STATES=('SELANGOR','W.P. KUALA LUMPUR')
SOURCES=((2024,'ev_registration2024.csv',12),(2025,'ev_registration2025.csv',12),(2026,'vehicles_2026.csv',9))


def identity(data):
    return hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='version'},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build_snapshot(directory=Path('data/ML Data')):
    counts=Counter();sources=[];coverage=[]
    for year,name,end in SOURCES:
        path=Path(directory)/name;accepted=excluded=0
        with path.open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                state=row['state'].strip().upper()
                if row['fuel'].strip().lower()!='electric' or row['type'].strip().lower()!='motokar' or state not in STATES:
                    excluded+=1;continue
                raw=row['date_reg'].strip()
                day=datetime.strptime(raw,'%Y-%m-%d' if '-' in raw else '%d/%m/%Y')
                if day.year!=year or day.month>end:raise ValueError('Record outside declared source coverage')
                counts[(state,day.strftime('%Y-%m'))]+=1;accepted+=1
        sources.append({'filename':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'accepted':accepted,'excluded':excluded})
        for state in STATES:coverage.append({'state':state,'year':year,'start_month':f'{year}-01','end_month':f'{year}-{end:02d}'})
    data={'schema_version':1,'scope':{'fuel':'electric','type':'motokar','states':list(STATES),'excluded':'Rakan Niaga and all other states/types/fuels; this is new registrations, not fleet ownership'},
          'sources':sources,'coverage':coverage,
          'months':[{'state':c['state'],'month':f"{c['year']}-{m:02d}",'count':counts[(c['state'],f"{c['year']}-{m:02d}")]} for c in coverage for m in range(1,int(c['end_month'][-2:])+1)]}
    data['version']=identity(data);validate_snapshot(data);return data


def validate_snapshot(data):
    if data['version']!=identity(data):raise ValueError('Monthly snapshot checksum mismatch')
    expected={(c['state'],f"{c['year']}-{m:02d}") for c in data['coverage'] for m in range(int(c['start_month'][-2:]),int(c['end_month'][-2:])+1)}
    actual={(r['state'],r['month']) for r in data['months']}
    if actual!=expected or len(actual)!=len(data['months']):raise ValueError('Monthly coverage differs')
    if any(type(r['count']) is not int or r['count']<0 for r in data['months']):raise ValueError('Invalid monthly count')
    for year,name,_ in SOURCES:
        source=next(s for s in data['sources'] if s['filename']==name)
        if sum(r['count'] for r in data['months'] if r['month'].startswith(str(year)))!=source['accepted']:raise ValueError('Source reconciliation failed')


def packaged_snapshot():
    data=json.loads(files('castravolt').joinpath('resources/registration_monthly.json').read_text(encoding='utf-8'))
    validate_snapshot(data);return data
