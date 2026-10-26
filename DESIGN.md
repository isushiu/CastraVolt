# CastraVolt UI/UX Design Brief

Status: Fill-in template — visual choices and layouts are not yet approved

Owner: [Name]

Last updated: [Date]

Figma link: [Link]

Related specifications: [PRD.md](PRD.md) and [TRD.md](TRD.md). If a proposed design changes product behaviour, record the change in those documents too.

> How to use: replace bracketed prompts, add wireframe links or screenshots, and mark each proposal as draft or approved. Existing product decisions below are context, not extra questions to answer again.

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
