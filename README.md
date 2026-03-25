<a name="readme-top"></a>

[![Release][release-shield]][release-url]
[![Stargazers][stars-shield]][stars-url]
![codecov][codecov-shield]

![GitHub last release date][gh-last-release-date]
![GitHub last commit][gh-last-commit]

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Issues][issues-shield]][issues-url]

[![Lines of code][lines]][lines-url]
![Code size][code-size]

[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/totaldebug/armadarr">
    <img src="logo.png" alt="Logo" width="400">
  </a>

  <h3 align="center">Armadarr</h3>

  <p align="center">
    Armadarr: Providing the firepower for your media empire.
  </p>
    <br />
    <br />
    <a href="https://github.com/totaldebug/armadarr/issues/new?assignees=&labels=type%2Fbug&template=bug.yml">Report Bug</a>
    ·
    <a href="https://github.com/totaldebug/armadarr/issues/new?assignees=&labels=type%2Ffeature&template=feature_request.yml">Request Feature</a>

</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li><a href="#features">Features</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#configuration">Configuration</a></li>
    <li><a href="#services">Services</a></li>
    <li><a href="#usage-tips">Usage Tips</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

Armadarr is a comprehensive Home Assistant integration for managing your "*Arr" applications (Sonarr, Radarr, Lidarr, Readarr, Prowlarr, Bazarr, and Whisparr). It provides sensors, binary sensors, buttons, and a calendar to monitor and control your media management stack.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

[![python][python]][python-url]
[![Home Assistant][home-assistant]][home-assistant-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- FEATURES -->
## Features

### Supported Applications
- **Sonarr / Whisparr**: TV series management.
- **Radarr**: Movie management.
- **Lidarr**: Music management.
- **Readarr**: Book management.
- **Prowlarr**: Indexer management.
- **Bazarr**: Subtitle management.

### Platforms & Entities
- **Sensors**:
  - **Queue Size**: Number of items currently in the download queue.
  - **Health Warnings**: Count of active system health warnings.
  - **Disk Space**: Real-time free space monitoring for all configured root folders.
  - **Content Counts**: Total number of Series, Movies, Artists, Authors, or Indexers.
  - **Missing Items**: Total number of missing episodes, movies, etc.
  - **Unmonitored Items**: Total number of unmonitored items in your library.
  - **Indexer Errors**: (Prowlarr only) Count of indexers with connection errors.
- **Binary Sensors**:
  - **Connectivity**: Monitor if the application is reachable.
  - **Update Available**: Alerts when a new version of the application is available.
- **Buttons**:
  - **Restart Application**: Remotely restart the service.
  - **Backup Now**: Trigger an immediate system backup.
  - **Sync App Indexers**: (Prowlarr only) Trigger a sync of indexers to applications.
  - **Search Missing Subtitles**: (Bazarr only) Trigger a search for missing subtitles.
- **Calendar**:
  - **Upcoming Media**: View upcoming air dates and release dates directly in the Home Assistant calendar.
  - **Enhanced Titles**: Sonarr/Whisparr events show both the Show Name and Episode Title (e.g., "The Mandalorian - Chapter 1").

### Events
- **`armadarr_history_event`**: Fired when a new record appears in the application history (e.g., download completed, grabbed, failed).
  - **Payload**: `app_type`, `entry_id`, `event_type`, `source_title`, `date`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- INSTALLATION -->
## Installation

### Option 1: HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. Go to **HACS** > **Integrations**.
3. Click the three dots in the top right and select **Custom repositories**.
4. Add `https://github.com/totaldebug/armadarr` with category `Integration`.
5. Click **Add**, then find **Armadarr** in the list and click **Download**.
6. Restart Home Assistant.

### Option 2: Manual
1. Download the `custom_components/armadarr` folder from this repository.
2. Copy the folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONFIGURATION -->
## Configuration
1. In Home Assistant, go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **Armadarr**.
3. Fill in the required information:
   - **App Type**: Select the application (e.g., Sonarr).
   - **URL**: The full URL of your instance (e.g., `http://192.168.1.10:8989`).
   - **API Key**: Found in the application's settings under **General**.
   - **Verify SSL**: Uncheck if using self-signed certificates.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- SERVICES -->
## Services

Armadarr provides several services to control your applications. Services are conditionally registered based on the application types you have configured.

### Common Services
- **`armadarr.system_task`**: Execute any system command or scheduled task.
  - `task`: The command name (e.g., `RssSync`) or numeric Task ID (e.g., `1`).
- **`armadarr.search_missing`**: Trigger a search for missing media (app-aware).
- **`armadarr.delete_queue_item`**: Remove an item from the download queue.
  - `item_id`: The ID of the item in the queue.
- **`armadarr.get_upcoming_media`**: Retrieve a list of upcoming media with full metadata (posters, summaries, etc.) for use in dashboards or notifications.

### Media Management Services
These services allow you to add new content to your library. If an ID is not provided, the integration will attempt to look up the item by title. If multiple matches are found, an error will be raised listing the options.

- **`armadarr.add_series`**: Add a new series to Sonarr/Whisparr.
- **`armadarr.add_movie`**: Add a new movie to Radarr.
- **`armadarr.add_artist`**: Add a new artist to Lidarr.
- **`armadarr.add_author`**: Add a new author to Readarr.

### Lookup Services
These services return the raw search results from the application, useful for finding IDs programmatically.

- **`armadarr.lookup_series`**: Search for series on TheTVDB.
- **`armadarr.lookup_movie`**: Search for movies on TMDB.
- **`armadarr.lookup_artist`**: Search for artists on MusicBrainz.
- **`armadarr.lookup_author`**: Search for authors on Readarr.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE TIPS -->
## Usage Tips
- **Multiple Instances**: You can add multiple instances of the same app type (e.g., Sonarr and Sonarr-4K) by repeating the configuration flow.
- **Calendar**: Use the built-in Calendar card to see what's airing soon.
- **Automation**: Use the `armadarr_history_event` to trigger notifications when a download completes.
- **Dashboards**: Use the `get_upcoming_media` service with the [Upcoming Media Card](https://github.com/custom-cards/upcoming-media-card) or similar for a rich visual experience.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Got something you would like to add? Check out the [contributing guide](CONTRIBUTING.md).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

* [Discord](https://discord.gg/6fmekudc8Q)
* [Discussions](https://github.com/totaldebug/armadarr/discussions)
* [Project Link](https://github.com/totaldebug/armadarr)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [pyarr](https://github.com/totaldebug/pyarr) - The library powering this integration.
* [Home Assistant](https://www.home-assistant.io/) - The best home automation platform.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[release-shield]: https://img.shields.io/github/v/release/totaldebug/armadarr?color=ff7034&label=Release&sort=semver&style=flat-square
[release-url]: https://github.com/totaldebug/armadarr/releases
[contributors-shield]: https://img.shields.io/github/contributors/totaldebug/armadarr.svg?style=flat-square
[contributors-url]: https://github.com/totaldebug/armadarr/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/totaldebug/armadarr.svg?style=flat-square
[forks-url]: https://github.com/totaldebug/armadarr/network/members
[stars-shield]: https://img.shields.io/github/stars/totaldebug/armadarr.svg?style=flat-square
[stars-url]: https://github.com/totaldebug/armadarr/stargazers
[issues-shield]: https://img.shields.io/github/issues/totaldebug/armadarr.svg?style=flat-square
[issues-url]: https://github.com/totaldebug/armadarr/issues
[license-shield]: https://img.shields.io/github/license/totaldebug/armadarr.svg?style=flat-square
[license-url]: https://github.com/totaldebug/armadarr/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/marksie1988
[codecov-shield]: https://img.shields.io/codecov/c/github/totaldebug/armadarr?style=flat-square

[gh-last-release-date]: https://img.shields.io/github/release-date/totaldebug/armadarr?style=flat-square&label=Last%20Release%20Date&logo=github&logoColor=white
[gh-last-commit]: https://img.shields.io/github/last-commit/totaldebug/armadarr.svg?style=flat-square&logo=github&label=Last%20Commit&logoColor=white

[lines]: https://img.shields.io/tokei/lines/github/totaldebug/armadarr?style=flat-square
[lines-url]: https://github.com/totaldebug/armadarr
[code-size]: https://img.shields.io/github/languages/code-size/totaldebug/armadarr?style=flat-square

[python]: https://img.shields.io/badge/Python-blue?style=flat-square&logo=Python&logoColor=white
[python-url]: https://www.python.org/
[home-assistant]: https://img.shields.io/badge/Home%20Assistant-blue?style=flat-square&logo=home-assistant&logoColor=white
[home-assistant-url]: https://www.home-assistant.io/
