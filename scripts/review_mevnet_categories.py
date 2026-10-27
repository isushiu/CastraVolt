"""Deduced host labels from explicit original place descriptions; never official labels."""
import csv
import json
import re
from pathlib import Path
from scripts.classify_mevnet_hosts import normalise

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'data/updated_mevnet_source'


def deduce_named_host(name):
    text=normalise(name.replace('Â',''))
    # Order matters: the host named in the record takes priority over a brand,
    # campus or fuel-station address mentioned in the same name.
    rules=[
        ('Hospital',r'\b(hospital|medical centre|medical center)\b','named hospital/medical centre'),
        ('F&B',r'\b(kfc|mcdonalds|coffee bean|tea leaf|tealive|taco bell|restaurant|restoran|rumah makan|kopitiam|food court|steamboat|blackball|cafe)\b','explicit food/beverage venue'),
        ('Showroom',r'\b(showroom|motors|mazda|volkswagen|honda auto|auto city)\b','named vehicle showroom/dealer'),
        ('Office',r'\b(research|leadership centre|leadership center|management office|office lots|site office|campus office|wisma|menara|department|ministry|majlis|municipal council|district office|government office|land office|land and district office|district and land office|suruhanjaya|agensi|agency|bahagian|markas|pejabat|jpj|lits office|corporate center)\b','explicit office/government/research premises'),
        ('Petrol Station - Highway',r'\b(shell|petronas|petron|caltex|bhp|petrol|bhpetrol)\b.*\b(highway|plus|kesas|l raya|lebuhraya|r and r)\b','named fuel station with explicit highway/rest-stop context'),
        ('Petrol Station',r'\b(shell|petronas|petron|caltex|bhp|bhpetrol|petrol station)\b','explicit fuel-station brand/site'),
        ('Convention Center',r'\b(convention cent(re|er)|dewan perdana)\b','named convention/event venue'),
        ('Galleria',r'\b(galleri|galleria)\b','named galleria (not property sales or museum gallery)'),
        ('Library',r'\b(library|perpustakaan|ppas)\b','named public library'),
        ('University',r'\b(university|universiti|uitm|fakulti|faculty|chancellery)\b','explicit university/campus/faculty'),
        ('Airport',r'\b(airport|lapangan terbang)\b','named airport'),
        ('Strata',r'\b(condominium|apartment|service apartment)\b','explicit multi-unit apartment/condominium; project Strata mapping'),
        ('Residences',r'\b(residence|residences|residen|residential)\b','explicit residential development; tenure not inferred'),
        ('Theme Park',r'\b(sunway lagoon|snowalk|escape|wonderland)\b','explicit named theme/water/indoor attraction'),
        ('Hotel & Resort',r'\b(hotel|resort|chalet)\b','explicit accommodation/resort'),
        ('Recreation Center',r'\b(golf|futsal|badminton|stadium|arena|football|sport|sports|clubhouse|club house|club|kelab|recreational|recreation|extreme park|central park|ecohill park|hot springs|wetlands|driving range|padang|dataran|giverny park)\b','explicit sport/recreation/park venue'),
        ('Shopping Mall',r'\b(mall|shopping centre|shopping center|digital mall)\b','explicit shopping mall/centre'),
        ('Others',r'\b(mart|supermarket|supermarkets|hypermarket|superstore|grocer|fresh|freshmart|market|pasar|pasaraya|ninso|nsk|eco shop|lotus|lotuss|jakel|decathlon|sports direct|gedung|bundle|wholesale|retail)\b','identified retail/grocery/market outside mall category'),
        ('Others',r'\b(museum|muzium|zoo|science|sains|park n|park and ride|terminal|mrt|teksi|taxi|car park|parking|bus|bas|ktm|lrt|sentral|port klang cruise)\b','identified museum/transport/parking/public facility not represented by a specific category'),
        ('Others',r'\b(school|college|kolej|academy|akademi|training|institut|institusi|institute|darul quran|factory|manufacturing|assemblies|logistics|accessories centre|sales gallery|property gallery|ecoworld gallery|welcome centre|welcome center|sirim)\b','identified education/industrial/property-sales premises outside specific categories'),
    ]
    # Sales galleries are not shopping gallerias; corporate research facilities
    # are not petrol stations, even when owned by a fuel company.
    if re.search(r'\b(sales gallery|property gallery|ecoworld gallery|welcome centre)\b',text):
        return 'Others','identified property sales/gallery premises, not shopping galleria'
    if 'geo sample' in text:return 'Office','geoscience sample/research centre, not a fuel retail station'
    if 'sports direct' in text:return 'Others','Sports Direct is a retailer, not a sports venue'
    for category,pattern,reason in rules:
        if re.search(pattern,text):return category,reason
    return None


def main():
    source=[x['attributes'] for x in json.loads((FOLDER/'features.json').read_text(encoding='utf-8'))]
    overrides=json.loads((FOLDER/'verified_category_overrides.json').read_text(encoding='utf-8'))
    deductions={};unresolved=[]
    for row in source:
        if row.get('category') or str(row['objectid']) in overrides:continue
        result=deduce_named_host(row['location'])
        if result is None:
            unresolved.append(row)
            continue
        category,reason=result
        lat,lon=row['latitude'],row['longitude']
        deductions[str(row['objectid'])]={'category':category,**{k:row[k] for k in ['location','state','latitude','longitude']},
            'source':'Deduced from official site identity and location; not official category',
            'source_url':'https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/MEVnet_EVCB/FeatureServer/0',
            'map_url':f'https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=19/{lat}/{lon}' if lat is not None else '',
            'matching':reason,'confidence':'inferred_from_explicit_host_description','requires_review':True}
    research_path=FOLDER/'researched_category_overrides.json'
    researched=json.loads(research_path.read_text(encoding='utf-8')) if research_path.exists() else {}
    unresolved=[row for row in unresolved if str(row['objectid']) not in researched]
    (FOLDER/'deduced_category_overrides.json').write_text(json.dumps(deductions,indent=2),encoding='utf-8')
    (FOLDER/'category_research_remaining.json').write_text(json.dumps(unresolved,indent=2),encoding='utf-8')
    print('Deduced:',len(deductions),'remaining:',len(unresolved))
    for row in unresolved:print(row['objectid'],row['location'])


if __name__=='__main__':main()
