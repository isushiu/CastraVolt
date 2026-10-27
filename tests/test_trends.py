import copy
import pytest
from pydantic import ValidationError
from castravolt.trends_data import build_snapshot, validate_snapshot, packaged_snapshot
from castravolt.trends import TrendFilters, calculate_dashboard


def dataset():
    return packaged_snapshot()


def test_sources_reconcile_and_missing_2026_months_are_not_zero():
    data=dataset();validate_snapshot(data)
    assert len(data['months'])==66
    assert sum(r['count'] for r in data['months'] if r['month'].startswith('2024'))==2688
    assert sum(r['count'] for r in data['months'] if r['month'].startswith('2025'))==1797
    assert sum(r['count'] for r in data['months'] if r['month'].startswith('2026'))==1916
    assert not any(r['month']>'2026-09' for r in data['months'])
    broken=copy.deepcopy(data);broken['months'][0]['count']+=1
    with pytest.raises(ValueError):validate_snapshot(broken)


def test_defaults_and_same_period_growth():
    data=dataset();result=calculate_dashboard(data,TrendFilters())
    assert result['total']==6401
    assert result['covered_months']==33
    assert result['average_per_month']==pytest.approx(6401/33)
    filtered=calculate_dashboard(data,TrendFilters(years=[2026]))
    assert filtered['covered_months']==9
    for metric in filtered['metrics']:
        assert metric['growth']['available']
        assert metric['growth']['previous_start']=='2025-01'
        assert metric['growth']['previous_end']=='2025-09'
        previous=sum(r['count'] for r in data['months'] if r['state']==metric['state'] and '2025-01'<=r['month']<='2025-09')
        assert metric['growth']['percent']==pytest.approx((metric['total']-previous)/previous*100)


def test_unavailable_zero_and_year_comparison():
    data=dataset()
    empty=calculate_dashboard(data,TrendFilters(years=[2026],start_month='2026-10',end_month='2026-12'))
    assert empty['total'] is None and empty['average_per_month'] is None
    assert not empty['months']
    result=calculate_dashboard(data,TrendFilters(comparison_mode='year_over_year',calendar_month_start=1,calendar_month_end=12))
    assert result['common_month_window']==[1,9]
    # Source coverage remains explicit; noncovered Oct–Dec 2026 are not inserted.
    assert len(result['months'])==66
    for row in data['months']:
        if row['month'].startswith('2025'):row['count']=0
    result=calculate_dashboard(data,TrendFilters(years=[2026]))
    assert all(not m['growth']['available'] and 'zero' in m['growth']['reason'] for m in result['metrics'])
    result=calculate_dashboard(dataset(),TrendFilters(years=[2024]))
    assert all(not m['growth']['available'] for m in result['metrics'])


@pytest.mark.parametrize('filters',[
 {'states':['JOHOR']},{'years':[2023]},{'start_month':'2026-12','end_month':'2026-01'},
 {'comparison_mode':'year_over_year','start_month':'2024-01'},
 {'calendar_month_start':10,'calendar_month_end':2},{'start_month':'2026-13'},
 {'years':[]},{'unknown':True}, {'calendar_month_start':2}])
def test_invalid_filters(filters):
    with pytest.raises(ValidationError):TrendFilters(**filters)


def test_zero_is_counted_inside_coverage_and_combined_average_uses_calendar_months():
    data=dataset()
    for row in data['months']:
        if row['month']=='2026-01':row['count']=0
    result=calculate_dashboard(data,TrendFilters(years=[2026],start_month='2026-01',end_month='2026-01'))
    assert result['total']==0 and result['average_per_month']==0
    assert result['covered_months']==1 and len(result['months'])==2
    assert all(m['covered_months']==1 for m in result['metrics'])


def test_timeline_bounds_and_common_window():
    result=calculate_dashboard(dataset(),TrendFilters(years=[2024,2026],start_month='2024-11',end_month='2026-02',states=['SELANGOR']))
    assert [r['month'] for r in result['months']]==['2024-11','2024-12','2026-01','2026-02']
    comparison=calculate_dashboard(dataset(),TrendFilters(comparison_mode='year_over_year',calendar_month_end=9))
    assert len(comparison['months'])==54
    assert all(int(m['end_month'][-2:])==9 for m in comparison['metrics'])


def test_groq_transport_is_bounded_and_uses_only_aggregate_payload(monkeypatch):
    import json
    from pydantic import SecretStr
    from castravolt.config import Settings
    from castravolt import trend_summaries as summaries
    captured={}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            captured['limit']=limit
            return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'Monthly registrations vary.'}}]}).encode()
    def provider(request,**kwargs):captured.update(request=request,kwargs=kwargs);return Response()
    monkeypatch.setattr(summaries,'urlopen',provider)
    settings=Settings(groq_api_key=SecretStr('transport-test'))
    assert summaries.generate_text(settings,{'total':6401})=='Monthly registrations vary.'
    assert captured['request'].full_url=='https://api.groq.com/openai/v1/chat/completions'
    assert captured['request'].get_header('User-agent')=='CastraVolt/0.1'
    assert captured['request'].get_header('Accept')=='application/json'
    payload=json.loads(captured['request'].data)
    assert payload['model']==settings.groq_model and payload['max_completion_tokens']==1000
    assert payload['messages'][1]['content']=='{"total":6401}'
    assert captured['limit']==65537 and captured['kwargs']['timeout']==30


def test_csv_import_filters_scope_and_parses_both_date_formats(tmp_path):
    import csv
    from castravolt.trends_data import SOURCES
    for year,name,_ in SOURCES:
        day=f'02/01/{year}' if year<2026 else '2026-01-02'
        rows=[{'date_reg':day,'type':'motokar','fuel':'electric','state':'Selangor'},
              {'date_reg':day,'type':'motosikal','fuel':'electric','state':'Selangor'},
              {'date_reg':day,'type':'motokar','fuel':'petrol','state':'Selangor'},
              {'date_reg':day,'type':'motokar','fuel':'electric','state':'Rakan Niaga'}]
        with (tmp_path/name).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    data=build_snapshot(tmp_path)
    assert sum(r['count'] for r in data['months'])==3
    assert len(data['months'])==66
    assert all(s['accepted']==1 and s['excluded']==3 for s in data['sources'])
