from scripts.review_mevnet_categories import deduce_named_host


def test_specific_host_takes_priority_over_brand_and_surroundings():
    assert deduce_named_host('KFC Petronas Alam Damai Drive Thru')[0]=='F&B'
    assert deduce_named_host('PETRONAS Research Sdn Bhd')[0]=='Office'
    assert deduce_named_host('PETRONAS Geo-Sample Centre')[0]=='Office'
    assert deduce_named_host('Sports Direct')[0]=='Others'
    assert deduce_named_host('University of Malaya Medical Centre')[0]=='Hospital'
    assert deduce_named_host('Shell Kawasan R&R Kinrara L/raya KESAS')[0]=='Petrol Station - Highway'


def test_unrepresented_known_host_type_is_others_not_unknown():
    assert deduce_named_host('Park N Ride MRT UPM Station')[0]=='Others'
    assert deduce_named_host('National Museum')[0]=='Others'
    assert deduce_named_host('TMG Mart Sri Gombak')[0]=='Others'


def test_opaque_company_or_mixed_use_name_needs_more_evidence():
    assert deduce_named_host('MAHA USAHA SDN BHD') is None
    assert deduce_named_host('Sky Park @ Cyberjaya') is None
