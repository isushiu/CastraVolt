# CastraVolt UI/UX Design Brief

Status: Working specification — Midnight Iris direction adopted; remaining bracketed fields are handoff prompts

Owner: [Name]

Last updated: 26 October 2026

Figma link: [Link]

Related specifications: [PRD.md](PRD.md) and [TRD.md](TRD.md). If a proposed design changes product behaviour, record the change in those documents too.

Visual reference: `CastraVolt_UI_UX_Design_Guide.pdf` (14 pages, project root). Adopt its visual identity and component guidance. The concrete specifications in Section 13 below take precedence over unfilled template prompts above them. PRD.md and TRD.md govern product behaviour where the PDF describes an earlier exploratory dashboard or optional accounts.

> How to use: follow the adopted specifications, attach Figma frames, and resolve remaining bracketed choices. The PDF's schematic maps and example counts are illustrative, not real application data.

## 1. Design goal

Help an individual planner select a proposed urban EV charging site, understand the estimated total charging points, and review monthly registration trends.

The main thing a planner should accomplish easily:

[Describe the main task in one sentence.]

What should the experience feel like?

[Choose three qualities, such as clear, trustworthy, and efficient. Explain briefly what each means in this app.]

What would make the interface confusing?

[List the misunderstandings the design should prevent.]

## 2. Users and context

Primary user: an infrastructure planner with an individual account and private projects.

- Typical device: [Laptop, desktop, tablet; rank priorities.]
- Map/GIS familiarity: [Describe expected knowledge.]
- Typical visit: [What brings the planner here? What do they leave with?]
- Interface language: [Choose language and any localisation needs.]
- Accessibility needs: [Keyboard use, zoom, contrast, alternative map input, etc.]

## 3. Product facts the design must preserve

- Supported study: urban locations in Selangor and Kuala Lumpur; precise urban coverage is defined during implementation.
- Planner selects a map pin/address and confirms the planned site's category.
- Site category describes the host location, such as a hospital or mall. Surrounding POI counts are separate.
- Display a 3 km circle around the selected pin. POIs are gathered on an explicit estimate request, not every drag movement.
- Backend gathers eight nearby facility groups and supplies the configured state registration indicator automatically.
- Prediction output is estimated total charging points, not additional chargers, energy demand, or AC/DC equipment recommendations.
- Round to nearest integer, with .5 upward; initial configurable minimum is one.
- Adoption-enabled model uses configured 2025 state totals. The trend dashboard covers 2024–2026 available data, not a three-year prediction feature.
- Accounts, projects, sites and saved predictions are private to each planner.
- Avoid invented confidence percentages or claims of guaranteed optimal capacity.

## 4. Navigation and information structure

Proposed main destinations:

- Projects: create/open the planner's work.
- Site estimator: choose a site and request an estimate.
- Saved results: inspect previous predictions within a project/site.
- EV adoption trends: explore monthly registrations.
- Account: session/account actions.

Choose navigation pattern: [Sidebar, top navigation, or another pattern. Explain why.]

Landing page after login: [Which destination, and why?]

Current project visibility: [How will the planner know which project they are editing?]

## 5. Main user flows

### A. First visit and login

Register → verify email → log in → open Projects.

Wireframe link: [Link]

Design decisions: [Form layout, guidance, feedback and next action.]

### B. New site estimate

Open/create project → select site on map or search address → confirm category → request estimate → inspect result → save/open the saved prediction.

The API records successful predictions under the owned site. Decide whether the interface uses an explicit save action for the site before estimation; do not show a separate prediction-save action unless it has a real purpose.

Wireframe link: [Link]

Primary action label: [For example, Estimate charging points.]

After the pin/category changes: [Explain how the old result becomes visibly outdated.]

### C. Revisit a prediction

Open project → select saved site → inspect prediction history → open a result and its original inputs.

Wireframe link: [Link]

How do old/new predictions differ visually? [Describe timestamps and version/context visibility.]

### D. Explore adoption trends

Open trends → select states, years and month range → inspect counts/comparison → reset filters.

Wireframe link: [Link]

How will the selected period and partial 2026 coverage stay visible? [Describe.]

## 6. Screen briefs

For each screen, specify its purpose, most important content, primary action, secondary actions, states and wireframe.

### 6.1 Account screens

Purpose: register, verify email, login, logout and recover access.

- Required fields and labels: [List.]
- Primary action: [Label.]
- Feedback: [Loading, validation, expired link and success behaviour.]
- Wireframes: [Links.]

### 6.2 Projects

Purpose: organise the planner's private sites and estimates.

- Project list/card content: [Name, updated time, and other useful information.]
- Create/open/edit actions: [Describe.]
- Empty state: [Helpful message and next action.]
- Delete confirmation: [State clearly what will be removed.]
- Wireframe: [Link.]

### 6.3 Site estimator

Purpose: select the host site and obtain an estimate.

- Map placement and available space: [Describe.]
- Address search and manual pin interaction: [Describe.]
- Selected-location summary: [Address/coordinates/state visibility.]
- 3 km circle and legend: [Describe.]
- Site-category confirmation: [Control, suggested value and correction.]
- Estimate action placement: [Describe.]
- POI count presentation: [How eight groups are shown without overwhelming the map.]
- Unsupported location and provider failure states: [Describe.]
- Wireframe: [Link.]

### 6.4 Prediction result

Purpose: communicate the estimated total and the context needed to assess it.

- Main result: [Number + label Estimated total charging points.]
- Site summary: [Confirmed category, selected location and state.]
- Supporting inputs: [POI counts, 3 km radius and extraction date.]
- Adoption context: [State registration figure and reference year.]
- Explanation: [Short plain-language description of what the estimate represents.]
- Model/data details: [Where expandable version/provenance information appears.]
- Next actions: [Return to map, inspect history, etc.; add only supported actions.]
- Wireframe: [Link.]

### 6.5 EV adoption trends

Purpose: show monthly new electric motokar registrations as an adoption indicator.

- Primary chart: [Timeline layout, legend and monthly count details.]
- Filters: states; years; inclusive month range; timeline/year-over-year comparison; reset.
- Summary metrics: selected-period registrations; average per covered month; same-period previous-year growth when valid.
- Default view: both states, January 2024–September 2026 available coverage.
- Coverage message: 2024/2025 full years; 2026 through September. Unavailable months are not zeros.
- Scope note: electric motokar only, explicitly recorded in the two states; Rakan Niaga excluded. Counts are new registrations, not total fleet.
- Accessible monthly data view: [Describe.]
- Missing comparison/zero denominator feedback: [Describe.]
- Wireframe: [Link.]

## 7. Visual direction

Reference designs: [Add two or three links/images and state what is useful about each.]

Colour roles: [Primary action, background, surfaces, text, borders, success, warning, error.]

Typography: [Font family, heading/body/label hierarchy, numerical display style.]

Spacing and density: [Choose a consistent spacing scale and comfortable desktop density.]

Components: [Buttons, form fields, selects, cards, tabs, notifications and dialogs.]

Chart series: [Use consistent labelled colours for Selangor and Kuala Lumpur; do not rely on colour alone.]

Map emphasis: [How selected pin, radius, boundaries and relevant facilities remain distinguishable.]

Theme: [Light/dark requirements and rationale.]

## 8. State and feedback checklist

For each state below, add the message, available action and wireframe reference:

- Initial empty project/site.
- Address search in progress, no match, or failed.
- Category unidentified or awaiting confirmation.
- Pin outside supported coverage.
- POIs loading; complete successful result with zero facilities; failed/incomplete query.
- Prediction running, successful, or failed.
- Selection changed while a request is in flight.
- Registration filters yield no covered months.
- Growth comparison unavailable.
- Session expired or access denied.
- Save/delete success or failure.

Do not make failed requests look like successful zero-count estimates. Avoid showing an old prediction as current after a site change.

## 9. Responsive and accessible behaviour

- Desktop arrangement: [Map, controls and result placement.]
- Narrow-screen arrangement: [Stacking, map height and filter behaviour.]
- Keyboard map alternative: [Address search/location fields and selected-site summary.]
- Focus order and visible focus: [Describe.]
- Labels/errors: [How controls are named and errors associated with fields.]
- Charts: [Text equivalents, focusable details and readable legends.]
- Zoom and text enlargement: [How layouts remain usable.]
- Motion: [Keep optional/nonessential animation respectful of reduced-motion preferences.]

## 10. Content and terminology

Use consistently:

- Estimated total charging points — primary prediction label.
- Site category — type of host location.
- Nearby facilities / POIs — surrounding mapped facilities within 3 km.
- New electric motokar registrations — chart measure.
- EV adoption trends — dashboard title, with the registration indicator explained.

Draft short messages for estimate explanation, unavailable POI data, unsupported location, partial-year coverage and stale results:

[Write the messages here.]

## 11. Usability review

Ask a representative planner/test participant to:

1. Create a project and find a proposed site.
2. Confirm its category and obtain an estimate.
3. Explain whether the number means total or additional charging points.
4. Change the pin and recognise that the previous estimate is outdated.
5. Find a saved prediction and identify its original inputs.
6. Compare matching months across years and explain the 2026 coverage limit.

Record observed issues, task completion, confusion and changes made. Agree success criteria before the review rather than inventing a passing score afterward.

Participants/date: [Fill in.]

Findings and design changes: [Fill in.]

## 12. Handoff and approval

- [ ] Screen inventory and primary flows covered.
- [ ] Wireframes reviewed against PRD/TRD.
- [ ] Loading, empty, error, stale-result and success states designed.
- [ ] Site category and surrounding POIs clearly distinguished.
- [ ] Total charging-point estimate and its limitations are understandable.
- [ ] Trend filters, units and source coverage are clear.
- [ ] Responsive and accessibility behaviour documented.
- [ ] Final Figma frames/components linked and named.
- [ ] Open decisions and unsupported concepts flagged.

Approved by: [Name]

Approval date/version: [Fill in.]

Open design decisions: [List only unresolved items.]

## 13. Adopted visual specification and adapted screens

This section adopts the supplied PDF's Midnight Iris direction and replaces its earlier research-explorer-only journey with the agreed planner product. It supplies the concrete visual/layout decisions requested by earlier template sections.

### Visual identity

- Midnight Ink `#19172B`: sidebar and brand anchors.
- Electric Iris `#6546D7`: primary actions, selected locations and brand focus.
- Iris hover `#5033B4`: hover/pressed emphasis.
- Signal Rose `#B83D70`: restrained comparison/residual accent.
- Canvas `#F7F6FB`; surface `#FFFFFF`; iris wash `#EEE9FC`.
- Main text `#282538`; secondary text `#625D73`.
- Divider `#DDD9E8`; interactive control border `#8A829D`.
- Supporting blue `#285BC4`; error `#AD2947`; success `#42614D` for completed actions.
- Active sidebar background `#302B47`, white text and a lilac indicator.

Use roughly 75% neutral surfaces, 20% ink/iris, and up to 5% supporting accents. No full-page gradients, neon glows, flashing pins, or continuously pulsing icons. If a warning token is needed, choose/test it explicitly; the guide does not specify one.

Use Inter with system-ui, Segoe UI and sans-serif fallbacks; weights 400, 500 and 600. Page title 28/36 px at 600; section title 20/28 px at 600; body/labels/tables 14/20 px; supporting text 12/18 px; KPI values 32/40 px at 600 with tabular numerals.

Desktop frame: 1440 × 900 px; 224 px sidebar; 64 px utility bar; 32 px content padding; maximum content width 1600 px; 12 columns and 24 px gutters. Spacing scale: 4, 8, 12, 16, 24, 32 and 48 px. Cards: 20–24 px padding, 12 px radius, subtle 1 px border. Inputs/buttons: 8 px radius. Small badges: 6 px radius. Restrained shadow only on floating panels. Left-align text; right-align numerical table columns. Allow vertical scrolling rather than compressing charts/text into one viewport.

Keep spelling CastraVolt. Use a semibold wordmark. The PDF's open-C/two-bars symbol is a concept pending approval of a final vector asset; minimum symbol size 24 px and clear space half its height. Light surfaces with a dark sidebar are the initial theme; full dark mode is not required. Colour/opacity transitions should be brief (120–180 ms) and respect reduced-motion preferences.

### Components and accessibility

- Primary button: 44 px high, iris fill, white label, 16 px horizontal padding; hover iris-hover.
- Secondary button: white fill, iris text, control border; hover iris wash.
- Inputs/selects: 44 px high, persistent labels, white surface and control border. Focus uses a 3 px iris outline with 2 px white offset. Error text explains the correction.
- Filter chips: 32 px visual height with accessible removal labels and adequate hit targets.
- Tables: 48–56 px rows, pale lilac header, and a selection indicator in addition to colour. Reference-site tables can use 25-row pages.
- Toasts confirm completed actions; persistent errors stay inline. Tooltips support keyboard focus and never contain the only copy of critical information.
- Target WCAG AA contrast, visible focus, meaningful labels, keyboard operation, reduced motion and 200% zoom usability. Verify the implemented combinations; the PDF's sample contrast calculations are not certification of the finished app.

### Navigation and screen priority

Use a dark desktop sidebar and utility header; drawer navigation on smaller screens. Main destinations: Projects, Site estimator (within current project), Saved predictions/history, EV adoption trends, and Account. Show project/site context in the header and the study-area label near the sidebar bottom. Land on Projects after login.

Keep individual accounts and private projects as required by PRD/TRD, even though page 4 of the PDF treats login as optional. Design registration, verification, login/logout, password recovery, project creation and ownership-aware errors.

Infrastructure Overview, recorded-site explorer, Model analysis and Data & methods are optional supporting screens from the guide. They do not replace the new-site prediction journey. Do not add exports, organisation sharing, billing or extra analytics without a corresponding product/API requirement.

### Primary site-estimation screen

On desktop, use an 8-column map and a 4-column controls/result panel, with approximately 480–560 px map height. Address search is visible above the map; a planner can place/move a proposed-site pin. Show its location, derived state and confirmed host-site category.

Draw a blue dashed 3 km ground-distance circle with faint fill and a labelled legend. Distinguish the proposed-site marker by shape and label from existing reference-site markers. Reference sites use 12–16 px iris circles; selected sites use a larger marker with an ink ring. Clusters show site counts, not demand. Selecting a recorded marker must not silently change the planner's proposed pin.

Place zoom top left, layers/Fit study area top right, legend bottom left, and visible OSM/provider attribution bottom right without overlaps. A verified boundary overlay may use an iris outline and faint fill. A Leaflet-based renderer is the PDF's recommendation; renderer/provider selection remains an implementation choice. Map overlays can be styled independently; raster tiles cannot be recoloured through Overpass.

Category control: suggest only when reliable, and let the planner confirm/correct one of the 23 host-site categories. It describes the planned charger's host location, not a classification of all surrounding POIs.

Primary action: **Estimate charging points**. Only an explicit request triggers the backend's 3 km Overpass extraction, deduplication, state/adoption lookup and inference. The radius circle itself does not prove that POIs have loaded. Present the eight returned POI counts in a compact two-column panel with source/radius/extraction time.

After a pin/category change, invalidate the active result and offer a new estimate. Ignore stale in-flight responses. Historical predictions remain accessible as historical records.

### Result panel

Prominent integer with label **Estimated total charging points**. Use nearest-integer half-up rounding with the configured minimum, not the old ceiling rule. Show site identity/category, state, POI evidence, 3 km radius, extraction time and the configured 2025 state registration indicator. The user does not enter adoption values.

Provide a short explanation that this is estimated planned capacity based on MEVnet records and surrounding features. Do not imply additional chargers, guaranteed optimal capacity, validated shortage, or calibrated confidence. Model/version and more detailed provenance can be expandable. The supported model has 11 features and adoption enabled; it does not learn the complete 2024–2026 monthly growth series.

If showing model analysis, use actual recorded results and identify the target, feature set, split and baselines. The PDF's Not evaluated cards are placeholders; do not retain them as current facts. Historical ceiling-rounded MAE must not be attributed to the new half-up rule.

### Adoption trends screen

Provide the dedicated view required by PRD/TRD, rather than hiding it only within Data & methods. Default: both states, January 2024–September 2026 available coverage. Include state, year, inclusive month-range filters, timeline/year-over-year modes and reset. Chart and summary metrics share the same filter state.

Timeline state colours: Selangor blue and Kuala Lumpur iris. A single-state year comparison may use 2024 blue, 2025 iris, 2026 rose as in the PDF. When comparing both state and year, add explicit state/year labels and line/point patterns; never rely solely on colour or change meanings without a legend.

Show period totals, average per covered month and comparable-period growth only where valid. Label the metric **New electric motokar registrations** and explain its scope. 2026 coverage is January–September, superseding the PDF's earlier January–May uncertainty. Unavailable months are gaps, not zeros. Explain excluded Rakan Niaga records and avoid describing the subset as verified resident fleet size. Exact registration-office semantics require source verification before adopting the PDF's office-location wording as fact.

### Responsive rules

- 1280 px and above: 224 px sidebar, four KPI cards where relevant, 8/4 map/detail layout.
- 1024–1279 px: sidebar may collapse to 72 px with accessible labels/tooltips; KPI cards 2 × 2; details below map if cramped.
- 768–1023 px: drawer navigation, two-column cards, full-width map with details below.
- Below 768 px: single column, 16 px padding, approximately 360 px minimum map height, full-width filters; tables scroll within their region.

Provide a non-map way to inspect saved sites and a chart data alternative. Ensure content remains usable at 200% zoom.

### Suggested current copy

- Empty estimator: Select a location on the map or search an address to estimate charging points.
- Category: Confirm the type of place where the chargers would be installed.
- POI loading: Gathering mapped facilities within 3 km…
- Prediction loading: Preparing your estimate…
- Changed selection: Location or category changed. Request a new estimate.
- POI error: Nearby facilities could not be retrieved. Retry to estimate this site.
- Missing source field: Not recorded.
- Map error: The map could not load. Retry or use address search when available.
- Registration coverage: 2026 data covers January–September. Counts represent filtered new electric motokar registrations.
- Rounding explanation: Estimates are rounded to the nearest whole charging point, with halves rounded upward.

Do not copy the PDF's Unknown POI radius message as current status: the user confirms 3 km. Other original extraction rules still need to be reproduced. Never turn a provider failure into zero POIs or show mock figures as real results.

### Next design handoff

Create desktop 1440 × 900 and mobile 390 × 844 Figma frames for account flows, Projects, Site estimator, prediction/history and adoption trends. Cover initial, selected, loading, success, changed-selection, empty, unsupported-location and error states. Link frames in earlier sections. Preserve the PDF's visual identity while checking every screen against the current PRD/TRD.
