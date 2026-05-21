# ROADMAP

Goal: Improve the README to make the relationship between this Home Assistant integration and the Endgame Grocery app clear for new users.

## Priority 1

Objective: Add a compact "Endgame Grocery App" section to README.md that explains what the companion app is, links to its repository, and tells users how to generate the API key.

Constraints:
- README stays in English
- Section is compact (no Docker quickstart, no full feature table)
- Placed directly before the existing "Prerequisites" section
- Content derived from https://github.com/derfloDev/endgame_grocery

Acceptance criteria:
- A new "## Endgame Grocery App" section appears before "## Prerequisites"
- Section describes the app as a self-hosted PWA (React · Express · PostgreSQL) for shared grocery lists
- Section links to `https://github.com/derfloDev/endgame_grocery`
- Section links to the Docker deployment docs in that repo
- Section tells users where to find the API key: *Info & Settings → Home Assistant API Key*
- No other sections of the README are changed
