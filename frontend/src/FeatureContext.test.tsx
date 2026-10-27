import { expect,test } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import FeatureContext from './FeatureContext';
import type { PreparedContext } from './FeatureContext';

test('context preview shows real fields and pending scientific validation',()=>{
  const context:PreparedContext={site_id:'s1',site_updated_at:'2026-10-27T00:00:00Z',radius_metres:1000,rule_sha256:'fixture',boundary_version:'fixture',inference_eligible:true,limitation:'Unverified',features:{nearby_mall_count:2,nearby_petrol_count:3,nearby_hotel_count:4,nearby_office_count:5,nearby_transit_count:6,nearby_university_count:7,nearby_hospital_count:8,nearby_parking_count:9,state:'W.P. KUALA LUMPUR',category:'Office'},provenance:{osm_base_timestamp:'2026-10-27',provider:'fixture',response_sha256:'fixture',geometry:'centres',deduplication:'fixture',attribution:'OSM'},extracted_at:'2026-10-27T00:00:00Z',extraction_rule_version:'provisional',cache_hit:true};
  const html=renderToStaticMarkup(<FeatureContext context={context} busy={false} error="" ready onPrepare={()=>{}}/>);
  expect(html).toContain('Mapped facilities within 1 km');expect(html).not.toContain('registrations');expect(html).not.toContain('not yet been verified');
  expect(html).toContain('Reused cached extraction');expect(html).toContain('Parking facilities');
});
test('preparation waits for a saved current site and displays errors instead of zeros',()=>{
  const html=renderToStaticMarkup(<FeatureContext context={null} busy={false} error="Provider unavailable" ready={false} onPrepare={()=>{}}/>);
  expect(html).toContain('disabled');expect(html).toContain('Provider unavailable');expect(html).not.toContain('facility-counts');
});
