# Local facility lookup repair

User reported repeated live failures. Use a verified Geofabrik OSM snapshot for normal application lookups, preserving the same provisional tags, bounding-box-centre radius and deduplication method. This changes availability, not the unresolved training-parity claim.

Bundle only qualifying public OSM nodes/ways/relations covering the study-state geometry plus >3 km buffer. Resolve way bounds from source node locations and relation bounds from all members (including nested relations); fail on missing geometry affecting coverage. Include source timestamp, URL, SHA-256 and ODbL attribution; hash-check the bundled file at runtime. Enforce coverage before counting. Different dataset hashes have different cache keys. No network/global Overpass cooldown for local queries. Keep Overpass as an explicit alternative setting, with native system certificate validation.

Builder is optional tooling, not a runtime dependency. Source PBF stays in ignored data/; the compact derived snapshot and manifest ship with the Python package. Setup on another computer needs no 240 MB download. Prepared inputs still have inference_eligible=false until original training parity is established. Verify genuine user-area counts and saved-site API on a disposable database/alternate ports. User ports/processes are preserved.
