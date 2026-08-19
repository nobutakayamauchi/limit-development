# Homepage v2 — Ultimate Loop decision record

## Frozen goal
Implement the approved ONE PHONE FOUNDRY top page with the visual order and copy already fixed in conversation.

## Raison d'être Destroy
Do not rebuild the site architecture.

Survivor:
- existing GitHub Pages
- existing approved hero asset
- static HTML/CSS/JS
- existing FGE runtime
- existing `development.html` as the old/archive development view

Killed as unnecessary:
- SPA/framework migration
- CMS migration
- new backend/database
- custom carousel dependency

## METEOR
Compared the smallest viable candidates:

1. rebuild the hero and entire page from CSS primitives
2. reuse the approved hero source and only implement the surrounding page shell

Candidate 2 survives because it minimizes visual drift and preserves the already-approved source image.

For the production carousel:
- data-driven vanilla JS survives
- third-party slider library dies as unnecessary

## Reality checks
- HTML/local-link contract check
- JS syntax check
- responsive CSS breakpoints for desktop / 820 / 520 / 390
- mobile horizontal thumbnail scrolling instead of forcing all cards into one row
- explicit COMING SOON state for YouTube / LINE / メルマガ

## Known boundary
Automated checks confirm structure and syntax, not human visual equivalence. After GitHub Pages deployment, the real iPhone pass at 375 / 390 / 430 px remains the final visual gate.

## DARWIN trigger
Reopen this decision only if:
- real-device layout breaks
- FGE public data needs deeper homepage integration
- a clearly smaller/safer implementation becomes available
- the approved visual source changes
