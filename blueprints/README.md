# Armadarr Blueprints

Reusable [Home Assistant script blueprints](https://www.home-assistant.io/docs/blueprint/)
for searching for and adding media through the Armadarr integration, straight
from a dashboard.

They cover every add-able *arr type:

| Media  | App     | Lookup blueprint     | Add blueprint     |
| ------ | ------- | -------------------- | ----------------- |
| Series | Sonarr  | `lookup_series.yaml` | `add_series.yaml` |
| Movie  | Radarr  | `lookup_movie.yaml`  | `add_movie.yaml`  |
| Artist | Lidarr  | `lookup_artist.yaml` | `add_artist.yaml` |
| Author | Readarr | `lookup_author.yaml` | `add_author.yaml` |

Plus one shared helper:

| Purpose                                  | Blueprint               |
| ---------------------------------------- | ----------------------- |
| Fill quality / root / metadata dropdowns | `refresh_profiles.yaml` |

Unlike a hard-coded quality-profile map, `refresh_profiles` reads the live
config from your instance via the `armadarr.get_config_data` action, so the
dropdowns always match the real profiles and root folders on that server.

## How it works

A script can't pause to let you pick a search result, so the flow is split into
three small scripts per instance that share `input_select` helpers:

1. **Refresh profiles** — calls `get_config_data`, fills the quality / root
   (and, for Lidarr/Readarr, metadata) dropdowns with `Name (id)` options.
2. **Lookup** — calls `lookup_*` with your search term, fills the result
   dropdown with `Title (id)` options.
3. **Add** — reads the selected result + profiles, parses the IDs back out, and
   calls `add_*`.

## Setup

### 1. Import the blueprints

In Home Assistant: **Settings → Automations & scenes → Blueprints → Import
Blueprint**, then paste the raw URL of each blueprint you want, e.g.:

```
https://github.com/totaldebug/armadarr/blob/main/blueprints/script/armadarr/refresh_profiles.yaml
https://github.com/totaldebug/armadarr/blob/main/blueprints/script/armadarr/lookup_series.yaml
https://github.com/totaldebug/armadarr/blob/main/blueprints/script/armadarr/add_series.yaml
```

### 2. Create the helper entities

For each instance, create these helpers under **Settings → Devices & services →
Helpers** (**Create Helper**). Example for Sonarr:

| Helper type        | Suggested name           |
| ------------------ | ------------------------ |
| Text               | `Sonarr search`          |
| Dropdown           | `Sonarr result`          |
| Dropdown           | `Sonarr quality profile` |
| Dropdown           | `Sonarr root folder`     |

Give the dropdowns a placeholder option (e.g. `Refresh me`) to start —
`refresh_profiles` and the lookup script overwrite the options at runtime.

For Lidarr/Readarr also add a **`… metadata profile`** dropdown.

### 3. Create the scripts from the blueprints

Create a script from each blueprint (**Settings → Automations & scenes →
Scripts → Add Script → Use blueprint**) and point its inputs at the matching
instance + helpers. Run the **Refresh profiles** script once now to populate the
quality / root / metadata dropdowns.

### 4. Add a dashboard card

```yaml
type: vertical-stack
cards:
  - type: heading
    heading: Add Series to Sonarr
    icon: mdi:television-plus
  - type: entities
    show_header_toggle: false
    entities:
      - entity: input_text.sonarr_search
        name: Search
      - entity: script.sonarr_lookup_series
        name: Search TheTVDB
        icon: mdi:magnify
      - entity: input_select.sonarr_result
        name: Match
      - entity: input_select.sonarr_quality_profile
        name: Quality profile
      - entity: input_select.sonarr_root_folder
        name: Root folder
      - entity: script.sonarr_refresh_profiles
        name: Refresh profiles
        icon: mdi:cloud-refresh
      - entity: script.sonarr_add_series
        name: Add to Sonarr
        icon: mdi:television-plus
```

(Substitute your own helper/script entity IDs.)

## Notes

- `add_*` actions return no response data; success/failure is reported via a
  persistent notification raised by the script.
- Artist (`mb_id`) and author (`author_id`) IDs are strings (e.g. MusicBrainz
  UUIDs), so their blueprints parse the selection as text rather than a number.
- Originally contributed as a dashboard recipe in
  [discussion #17](https://github.com/totaldebug/armadarr/discussions/17).
