# ROADMAP

Goal: make the scan interval configurable via the Home Assistant UI.

## Priority 1

Objective: allow users to set the polling interval for the Endgame Grocery integration
directly in Home Assistant, both during initial setup and via the options flow afterwards.

### Scope

- Add `CONF_SCAN_INTERVAL` constant and `DEFAULT_SCAN_INTERVAL_SECONDS = 60` to `const.py`.
- Extend the initial config-flow user step (`config_flow.py`) with a required integer field
  `scan_interval` (10–600 s, default 60).
- Add an `OptionsFlowHandler` to `config_flow.py` with the same `scan_interval` field so users
  can change the interval later without re-adding the integration.
- In `__init__.py`, read `scan_interval` from `entry.options` (preferred) falling back to
  `entry.data`, and pass the resulting `timedelta` to `EndgameGroceryCoordinator`.
- Register `async_update_options` on the config entry so the coordinator refreshes its interval
  when options change (via `entry.add_update_listener`).
- Update `strings.json` and `translations/en.json` with options-flow labels and descriptions.

### Acceptance Criteria

- Installing the integration shows a "Scan Interval" field (default 60, range 10–600).
- Submitting a value outside 10–600 shows a validation error, not an exception.
- After setup, the options flow (⚙ button) shows the current interval pre-filled.
- Saving a new interval in the options flow reloads the coordinator with the new `update_interval`.
- `python -m unittest discover -s tests -p "test_*.py"` passes with no failures.
- `python -m py_compile custom_components/endgame_grocery/*.py` exits 0.

### Constraints

- `scan_interval` is stored in `entry.data` on first setup and migrated/shadowed by
  `entry.options` on subsequent changes — this is standard HA practice.
- Default remains 60 s; no breaking change for entries that were created before this feature.
