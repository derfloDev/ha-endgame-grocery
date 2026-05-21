# Plan

Status: **ready_for_implement**

Goal: Add a compact "Endgame Grocery App" section to README.md so new users immediately understand what the companion app is, where to find it, and how to obtain an API key.

## Scope

Add a new `## Endgame Grocery App` section to `README.md`, positioned directly before the existing `## Prerequisites` section. No other sections are modified.

## Acceptance Criteria

1. `README.md` contains a `## Endgame Grocery App` heading placed immediately before `## Prerequisites`.
2. The section describes the app as a self-hosted PWA for shared grocery lists with its tech stack (React · Express · PostgreSQL).
3. The section links to `https://github.com/derfloDev/endgame_grocery`.
4. The section mentions key features: shared lists, dark Endgame theme, push notifications, offline support.
5. The section tells users where to generate the API key: *Info & Settings → Home Assistant API Key*.
6. The section contains a direct link to the Docker deployment docs at `https://github.com/derfloDev/endgame_grocery#docker-deployment`.
7. No other content in `README.md` is altered.

## Implementation Phases

### Phase 1 — Update README.md

**File to change:** `README.md`

Insert the following block between the `## Overview` / `## Features` sections and `## Prerequisites`:

```markdown
## Endgame Grocery App

This integration connects Home Assistant with an [Endgame Grocery](https://github.com/derfloDev/endgame_grocery) server — a self-hosted PWA for shared grocery lists (React · Express · PostgreSQL).

Features: shared lists, dark Endgame theme, push notifications, offline support.

**Generate your API key:** In the app under *Info & Settings → Home Assistant API Key*.

➡ [Install the app (Docker)](https://github.com/derfloDev/endgame_grocery#docker-deployment)
```

Exact insertion point: immediately before the line `## Prerequisites`.

## Validation

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile custom_components/endgame_grocery/*.py
```

Both commands must exit 0. No code logic is changed, so these are a sanity check only.
