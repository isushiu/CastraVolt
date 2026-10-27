from scripts.classify_mevnet_hosts import category_from_tags, match_host


def test_host_tags_do_not_turn_every_shop_or_parking_space_into_a_mall():
    assert category_from_tags({'shop':'mall'}) == 'Shopping Mall'
    assert category_from_tags({'shop':'supermarket'}) == 'Others'
    assert category_from_tags({'amenity':'parking'}) is None
    assert category_from_tags({'office':'government'}) == 'Office'
    assert category_from_tags({'building':'apartments'}) == 'Strata'


def test_nearby_unrelated_facility_is_not_the_host():
    site={'location':'Example Tower','latitude':3,'longitude':101.5}
    other={'id':1,'type':'node','lat':3.0001,'lon':101.5,'tags':{'name':'Petrol Station ABC','amenity':'fuel'}}
    assert match_host(site,[other])['category'] is None
    host=dict(other,tags={'name':'Example Tower','building':'office'})
    assert match_host(site,[host])['category']=='Office'


def test_conflicting_host_matches_stay_unresolved():
    site={'location':'Example Centre','latitude':3,'longitude':101.5}
    a={'id':1,'type':'node','lat':3,'lon':101.5,'tags':{'name':'Example Centre','shop':'mall'}}
    b=dict(a,id=2,tags={'name':'Example Centre','office':'company'})
    assert match_host(site,[a,b])['category'] is None


def test_mall_pin_in_mixed_use_apartments_is_not_labelled_strata():
    site={'location':'Example Mall','latitude':3,'longitude':101.5}
    building={'id':1,'type':'way','lat':3,'lon':101.5,'tags':{'building':'apartments'},
              'ring':[(101.49,2.99),(101.51,2.99),(101.51,3.01),(101.49,3.01),(101.49,2.99)]}
    assert match_host(site,[building])['category'] is None
