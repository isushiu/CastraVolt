from test_accounts import account_settings, client
from test_projects import login, write


def test_location_validation_and_site_saving(client,account_settings):
    assert client.get('/api/v1/locations/validate?latitude=3.1579&longitude=101.7116').status_code==401
    login(client,account_settings)
    result=client.get('/api/v1/locations/validate?latitude=3.1579&longitude=101.7116')
    assert result.status_code==200
    assert result.json()['state']=='W.P. KUALA LUMPUR'
    assert result.json()['urban_coverage']=='provisional'
    assert client.get('/api/v1/locations/validate?latitude=5.4141&longitude=100.3288').status_code==422
    pid=write(client,'POST','/projects',{'name':'Map project'}).json()['id']
    site=write(client,'POST',f'/projects/{pid}/sites',{'name':'KL pin','latitude':3.1579,'longitude':101.7116,'category':'Office'})
    assert site.status_code==201 and site.json()['state']=='W.P. KUALA LUMPUR'
    sid=site.json()['id']
    changed=write(client,'PATCH',f'/sites/{sid}',{'latitude':3.0738,'longitude':101.5183})
    assert changed.json()['state']=='SELANGOR'
    assert write(client,'PATCH',f'/sites/{sid}',{'latitude':5.4141,'longitude':100.3288}).status_code==422
    assert client.get(f'/api/v1/sites/{sid}').json()['state']=='SELANGOR'
    assert write(client,'POST',f'/projects/{pid}/sites',{'name':'Unsupported','latitude':0,'longitude':0,'category':'Office'}).status_code==422


def test_search_is_authenticated_cached_and_bounded(client,account_settings,monkeypatch):
    assert client.get('/api/v1/locations/search?q=KLCC').status_code==401
    login(client,account_settings)
    from castravolt import locations
    calls=[]
    def fetch(settings,query):
        calls.append(query)
        return [{'lat':'3.1579','lon':'101.7116','display_name':'KLCC, Kuala Lumpur','name':'KLCC'}]
    monkeypatch.setattr(locations,'fetch_search',fetch)
    first=client.get('/api/v1/locations/search?q=KLCC')
    assert first.status_code==200 and first.json()[0]['state']=='W.P. KUALA LUMPUR'
    assert client.get('/api/v1/locations/search?q=KLCC').json()==first.json()
    assert len(calls)==1
    assert client.get('/api/v1/locations/search?q=KL').status_code==422
    # An uncached immediate second query is throttled application-wide.
    assert client.get('/api/v1/locations/search?q=Shah%20Alam').status_code==429


def test_search_failure_is_not_an_empty_success(client,account_settings,monkeypatch):
    login(client,account_settings)
    from castravolt import locations
    def fail(*args): raise TimeoutError()
    monkeypatch.setattr(locations,'fetch_search',fail)
    assert client.get('/api/v1/locations/search?q=Missing').status_code==503


def test_pin_address_is_derived_cached_and_state_is_local(client,account_settings,monkeypatch):
    login(client,account_settings)
    from castravolt import locations
    calls=[]
    def reverse(settings,latitude,longitude):
        calls.append((latitude,longitude))
        return {'display_name':'Ara Damansara, Selangor, Malaysia','address':{'state':'Wrong remote state'}}
    monkeypatch.setattr(locations,'fetch_reverse',reverse)
    url='/api/v1/locations/address?latitude=3.1136053973717&longitude=101.6037940979'
    result=client.get(url)
    assert result.status_code==200
    assert result.json()['state']=='SELANGOR'
    assert result.json()['address']=='Ara Damansara, Selangor, Malaysia'
    assert client.get(url).json()==result.json() and len(calls)==1
    assert client.get('/api/v1/locations/address?latitude=0&longitude=0').status_code==422
