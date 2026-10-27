"""Reconcile filtered 2025 rows into the serving context, without pandas or private paths."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def prepare(source):
    counts=Counter()
    with source.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            state=row['state'].strip().upper()
            if row['type'].strip().lower()!='motokar' or row['fuel'].strip().lower()!='electric' or state not in {'SELANGOR','W.P. KUALA LUMPUR'}:
                raise ValueError('Input must contain only filtered electric motokar in the two study states')
            if datetime.strptime(row['date_reg'],'%d/%m/%Y').year!=2025: raise ValueError('Wrong registration year')
            counts[state]+=1
    if dict(counts)!={'SELANGOR':560,'W.P. KUALA LUMPUR':1237}: raise ValueError('Counts differ from the evaluated model configuration; review rather than silently update')
    return {'version':'fixed-2025-v1','reference_year':2025,'period_start':'2025-01-01','period_end':'2025-12-31',
        'measure':'new electric motokar registrations, not fleet stock','counts':dict(sorted(counts.items())),
        'source_file':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'scope':{'fuel':'electric','vehicle_type':'motokar','exclude':'Rakan Niaga and all other states/types'}}


if __name__=='__main__':
    result=prepare(ROOT/'data/ML Data/ev_registration2025.csv')
    output=ROOT/'src/castravolt/resources/adoption_2025.json'
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified fixed-2025 adoption context:',result['counts'])
