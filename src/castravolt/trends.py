"""Authenticated deterministic registration metrics; LLM prose is separate."""
import re
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,model_validator
from sqlalchemy import select,update,delete,text
from sqlalchemy.orm import Session
from castravolt.auth import current_user,database,now
from castravolt.trends_data import STATES,validate_snapshot
from castravolt.trend_models import RegistrationVersion,RegistrationMonth

router=APIRouter(prefix='/api/v1/trends',tags=['Registration trends'])


class TrendFilters(BaseModel):
    model_config=ConfigDict(extra='forbid')
    states:list[str]=Field(default_factory=lambda:list(STATES),min_length=1,max_length=2)
    years:list[int]=Field(default_factory=lambda:[2024,2025,2026],min_length=1,max_length=3)
    comparison_mode:Literal['timeline','year_over_year']='timeline'
    start_month:str|None=None
    end_month:str|None=None
    calendar_month_start:int=Field(default=1,ge=1,le=12)
    calendar_month_end:int=Field(default=12,ge=1,le=12)

    @model_validator(mode='after')
    def valid(self):
        if any(s not in STATES for s in self.states) or any(y not in [2024,2025,2026] for y in self.years):raise ValueError('Unsupported state/year')
        self.states=sorted(set(self.states));self.years=sorted(set(self.years))
        for value in [self.start_month,self.end_month]:
            if value and not re.fullmatch(r'20[0-9]{2}-(0[1-9]|1[0-2])',value):raise ValueError('Use YYYY-MM')
        if self.start_month and self.end_month and self.start_month>self.end_month:raise ValueError('Reversed period')
        if self.calendar_month_start>self.calendar_month_end:raise ValueError('Reversed calendar window')
        if self.comparison_mode=='year_over_year' and (self.start_month or self.end_month):raise ValueError('Use calendar months for comparisons')
        if self.comparison_mode=='timeline' and (self.calendar_month_start!=1 or self.calendar_month_end!=12):raise ValueError('Calendar window requires comparison mode')
        return self


def publish_snapshot(db,data):
    validate_snapshot(data)
    # Serialise publication so concurrent imports cannot leave multiple active versions.
    db.execute(text("SELECT pg_advisory_xact_lock(7132091)"))
    version=db.get(RegistrationVersion,data['version'])
    if version is None:
        version=RegistrationVersion(id=data['version'],manifest={k:v for k,v in data.items() if k!='months'},active=False,imported_at=now())
        db.add(version);db.flush()
        db.add_all([RegistrationMonth(version_id=version.id,**row) for row in data['months']]);db.flush()
    db.execute(update(RegistrationVersion).values(active=False));db.flush()
    version.active=True;db.flush()


def active_snapshot(db):
    version=db.scalar(select(RegistrationVersion).where(RegistrationVersion.active.is_(True)))
    if version is None:raise HTTPException(503,'Monthly registration data is not imported. Run the project startup migration.')
    rows=db.scalars(select(RegistrationMonth).where(RegistrationMonth.version_id==version.id).order_by(RegistrationMonth.state,RegistrationMonth.month)).all()
    return {**version.manifest,'months':[{'state':r.state,'month':r.month,'count':r.count} for r in rows]}


def calculate_dashboard(data,filters):
    lookup={(r['state'],r['month']):r['count'] for r in data['months']}
    coverage=[c for c in data['coverage'] if c['state'] in filters.states]
    def selected(row):
        month=row['month'];year=int(month[:4]);number=int(month[-2:])
        if row['state'] not in filters.states or year not in filters.years:return False
        if filters.comparison_mode=='timeline':return (not filters.start_month or month>=filters.start_month) and (not filters.end_month or month<=filters.end_month)
        return filters.calendar_month_start<=number<=filters.calendar_month_end
    rows=sorted((r for r in data['months'] if selected(r)),key=lambda r:(r['month'],r['state']))
    distinct=sorted({r['month'] for r in rows});metrics=[]
    for state in filters.states:
        for year in filters.years:
            current=[r for r in rows if r['state']==state and int(r['month'][:4])==year]
            if not current:continue
            months=[int(r['month'][-2:]) for r in current]
            previous=[f'{year-1}-{m:02d}' for m in months]
            growth={'available':False,'percent':None,'previous_total':None,'previous_start':previous[0],'previous_end':previous[-1],'reason':'Previous-year coverage is unavailable or incomplete.'}
            if all((state,m) in lookup for m in previous):
                total=sum(lookup[(state,m)] for m in previous);growth['previous_total']=total
                if total>0:growth.update(available=True,percent=(sum(r['count'] for r in current)-total)/total*100,reason=None)
                else:growth['reason']='Previous-year registrations are zero.'
            total=sum(r['count'] for r in current)
            metrics.append({'state':state,'year':year,'start_month':current[0]['month'],'end_month':current[-1]['month'],'covered_months':len(current),'total':total,'average_per_month':total/len(current),'growth':growth})
    common_start=max([filters.calendar_month_start]+[int(c['start_month'][-2:]) for c in coverage if c['year'] in filters.years])
    common_end=min([filters.calendar_month_end]+[int(c['end_month'][-2:]) for c in coverage if c['year'] in filters.years])
    total=sum(r['count'] for r in rows) if rows else None
    peak=max(rows,key=lambda r:r['count']) if rows else None
    return {'source_version':data['version'],'scope':data['scope'],'sources':data['sources'],'coverage':coverage,'filters':filters.model_dump(),
        'months':rows,'total':total,'covered_months':len(distinct),'average_per_month':total/len(distinct) if distinct else None,
        'period_start':distinct[0] if distinct else None,'period_end':distinct[-1] if distinct else None,
        'common_month_window':[common_start,common_end] if common_start<=common_end else None,
        'metrics':metrics,'peak':peak,'metric_label':'New electric motokar registrations'}


@router.get('')
def dashboard(request:Request,states:str='SELANGOR,W.P. KUALA LUMPUR',years:str='2024,2025,2026',comparison_mode:str='timeline',start_month:str|None=None,end_month:str|None=None,calendar_month_start:int=1,calendar_month_end:int=12,user=Depends(current_user),db:Session=Depends(database)):
    try:
        filters=TrendFilters(states=states.split(','),years=[int(y) for y in years.split(',')],comparison_mode=comparison_mode,start_month=start_month,end_month=end_month,calendar_month_start=calendar_month_start,calendar_month_end=calendar_month_end)
    except ValueError:raise HTTPException(422,'Choose valid states, years and an ordered month range.') from None
    result=calculate_dashboard(active_snapshot(db),filters)
    from castravolt.trend_summaries import cached_summary
    result['summary']=cached_summary(db,request.app.state.settings,result)
    result['summary_enabled']=bool(result['summary'] or request.app.state.settings.groq_api_key.get_secret_value().strip())
    return result
