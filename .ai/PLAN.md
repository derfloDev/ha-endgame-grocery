# Plan

Status: **ready_for_implement**

Goal: make the scan interval configurable in Home Assistant — set during initial setup and
changeable at any time via the integration's options flow.

## Scope

See `ROADMAP.md` for full acceptance criteria and constraints.

## Tasks

| Task | Title | Depends On |
|------|-------|------------|
| T-001 | Constants, config flow, and strings | — |
| T-002 | Coordinator wiring, update listener, and tests | T-001 |

---

## T-001 — Constants, config flow, and strings

### Goal
Introduce `CONF_SCAN_INTERVAL` and `DEFAULT_SCAN_INTERVAL_SECONDS`, extend the initial user
step with a validated `scan_interval` field, add an `OptionsFlowHandler`, and update all
UI string files.

### Files to change

| File | Change |
|------|--------|
| `custom_components/endgame_grocery/const.py` | Add `CONF_SCAN_INTERVAL = "scan_interval"`, `DEFAULT_SCAN_INTERVAL_SECONDS = 60`, keep `DEFAULT_SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS)` |
| `custom_components/endgame_grocery/config_flow.py` | Add `scan_interval` (vol.Required, int, default 60) to `STEP_USER_DATA_SCHEMA`; add validation that rejects values outside 10–600 with error key `"invalid_scan_interval"`; add `OptionsFlowHandler` class with a single `async_step_init` that pre-fills the current value and saves to `entry.options`; register the handler via `async_get_options_flow` on the config flow class |
| `custom_components/endgame_grocery/strings.json` | Add `options` section with `step.init` title, `data.scan_interval`, `data_description.scan_interval`; add `error.invalid_scan_interval` |
| `custom_components/endgame_grocery/translations/en.json` | Keep in sync with `strings.json` (identical content) |

### Implementation notes

- Use `vol.All(vol.Coerce(int), vol.Range(min=10, max=600))` for validation.
- `STEP_USER_DATA_SCHEMA` should supply `default=DEFAULT_SCAN_INTERVAL_SECONDS` so the field
  is pre-populated.
- In `OptionsFlowHandler.async_step_init`, read the current value from
  `self.config_entry.options.get(CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))`.
- `async_get_options_flow` is a `@staticmethod` returning `OptionsFlowHandler(config_entry)`.
- `OptionsFlowHandler.__init__` stores `config_entry`.

### Validation
```
python -m py_compile custom_components/endgame_grocery/const.py
python -m py_compile custom_components/endgame_grocery/config_flow.py
python -m unittest discover -s tests -p "test_*.py"
```

---

## T-002 — Coordinator wiring, update listener, and tests

### Goal
Read `scan_interval` from `entry.options` (fallback `entry.data`, fallback default) in
`EndgameGroceryCoordinator`, and register an options-update listener so a saved options change
reloads the coordinator with the new interval without requiring a full restart.

### Files to change

| File | Change |
|------|--------|
| `custom_components/endgame_grocery/__init__.py` | In `EndgameGroceryCoordinator.__init__`, derive `update_interval` from `entry.options` → `entry.data` → `DEFAULT_SCAN_INTERVAL_SECONDS`; in `async_setup_entry`, register `entry.add_update_listener(async_reload_entry)` after storing `runtime_data`; add `async_reload_entry(hass, entry)` helper that calls `hass.config_entries.async_reload(entry.entry_id)` |
| `tests/test_init.py` | Add tests: coordinator reads `scan_interval` from `entry.options`; coordinator falls back to `entry.data`; coordinator falls back to default when neither present; `async_setup_entry` registers an update listener |
| `tests/test_config_flow.py` | Add tests: initial user step includes `scan_interval` field with default 60; submitting a value below 10 shows `invalid_scan_interval` error; submitting a value above 600 shows `invalid_scan_interval` error; options flow pre-fills the current interval; options flow saves to `entry.options`; strings/translations include options section |

### Implementation notes

- Interval resolution in coordinator:
  ```python
  raw = entry.options.get(CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
  update_interval = timedelta(seconds=int(raw))
  ```
- `async_reload_entry` signature: `async def async_reload_entry(hass, entry) -> None`.
- Coordinator does **not** need to call `async_set_updated_data` — HA's reload handles it.
- In `test_init.py`, the `FakeConfigEntry` stub needs an `options` attribute (default `{}`).
- In `test_config_flow.py`, the options flow tests need a minimal `FakeOptionsFlow` and
  `FakeConfigEntriesManager` stub that exposes `async_reload`.

### Validation
```
python -m py_compile custom_components/endgame_grocery/__init__.py
python -m unittest discover -s tests -p "test_*.py"
```

---

## Commit strategy

Two Conventional Commits, one per task (implementer runs `commit_task` after each review):

- T-001: `feat(config): add configurable scan interval to setup and options flow`
- T-002: `feat(coordinator): wire scan interval from options/data into update coordinator`
