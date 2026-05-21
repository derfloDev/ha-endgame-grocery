<p align="center">
  <img src="assets/endgame_grocery_logo.png" alt="Endgame Grocery" width="150">
</p>

<h1 align="center">Endgame Grocery - Home Assistant Integration</h1>

<p align="center">
  <a href="https://github.com/DerFloDev/ha-endgame-grocery/actions/workflows/ci.yml">
    <img src="https://github.com/DerFloDev/ha-endgame-grocery/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=DerFloDev&repository=ha-endgame-grocery&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open in HACS">
  </a>
</p>

## Overview

Endgame Grocery connects an Endgame Grocery server to Home Assistant and exposes each grocery list as a `todo` entity. That gives you a native way to view, update, and automate shopping lists from dashboards, assistants, and scripts.

## Features

- One Home Assistant `todo` entity per Endgame Grocery list
- Create, rename, describe, complete, reopen, and delete grocery items from Home Assistant
- 60-second background refresh to keep Home Assistant in sync with the server
- Config flow setup with live API credential validation
- Works with the Lovelace Todo card and Home Assistant automations

## Endgame Grocery App

This integration connects Home Assistant with an [Endgame Grocery](https://github.com/derfloDev/endgame_grocery) server - a self-hosted PWA for shared grocery lists (React, Express, PostgreSQL).

Features: shared lists, dark Endgame theme, push notifications, offline support.

**Generate your API key:** In the app under *Info & Settings -> Home Assistant API Key*.

[Install the app (Docker)](https://github.com/derfloDev/endgame_grocery#docker-deployment)

## Prerequisites

- An Endgame Grocery server that is reachable from Home Assistant
- An API key from the Endgame Grocery settings page
- Home Assistant `2026.5.0` or newer
- HACS installed if you want the HACS installation path

## Installation via HACS

1. Open HACS in Home Assistant.
2. Go to `Integrations`, then open the three-dot menu and choose `Custom repositories`.
3. Add `https://github.com/DerFloDev/ha-endgame-grocery` as a repository with category `Integration`.
4. Search for `Endgame Grocery` in HACS and install it.
5. Restart Home Assistant.

## Manual Installation

1. Download the latest `endgame_grocery.zip` asset from the GitHub Releases page.
2. Create the folder `<config>/custom_components/endgame_grocery/` if it does not already exist.
3. Extract the ZIP contents directly into `<config>/custom_components/endgame_grocery/`.
4. Restart Home Assistant.

## Configuration

1. In Home Assistant, open `Settings -> Devices & Services`.
2. Select `Add Integration` and search for `Endgame Grocery`.
3. Enter the base URL for your server, for example `https://grocery.example.com`.
4. Enter your API key.
5. Submit the form. Home Assistant creates one `todo` entity for each grocery list.

## Usage

After setup, each Endgame Grocery list appears as its own Home Assistant `todo` entity named after the list. You can use those entities in the Todo dashboard card, service calls, automations, or scripts to create items, edit their descriptions, rename them, change completion state, and delete them.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `invalid_auth` during setup | Wrong or expired API key | Generate a new API key in Endgame Grocery settings and try again |
| `cannot_connect` during setup | Wrong base URL or the server is unreachable | Check the URL, TLS settings, and network reachability from Home Assistant |
| `Could not delete item from list ...` when removing a todo item | The server rejected the delete request or the item disappeared before Home Assistant refreshed | Refresh the list and retry. If it keeps happening, verify the item still exists on the Endgame Grocery server and check the integration logs for the underlying API error |
| New lists do not appear after they are created on the server | Todo entities are created when the integration is set up | Reload the integration from Devices & Services |

## Release and versioning

Contributors publish a release by pushing a semantic version tag. The release workflow stamps the tag version into the packaged `manifest.json`, builds `endgame_grocery.zip` with the integration files at the archive root, attaches that archive to the GitHub Release with generated notes, and then fetches the latest `main` branch before committing the stamped `manifest.json` back with a `[skip ci]` bot commit so the repository stays in sync without a detached-HEAD push rejection.

```bash
git tag v0.2.0
git push origin v0.2.0
```

## License

MIT. The maintainer can replace this section later if the repository adopts a different license file.
