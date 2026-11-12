# Hexen Map

[Português (Brasil)](README.md) · **English**

### Your AppSample progress, on the in-game maps.

Explore **Genshin Impact** with pins on the minimap and the full-screen map, track your collected items, and bring along the progress you already marked on AppSample. Choose your items, collapse the panel, and keep playing.

**Windows 10/11 · External overlay · 2.0.1 · Test version**

> The interface, reviewed catalog, startup messages and installer support English and Brazilian Portuguese. Supporting documents linked below are primarily in Portuguese.

## What Hexen Map offers

| Feature | How it helps |
| --- | --- |
| **Minimap and full-screen map pins** | Displays selected items on the game's native maps, following the alignment recognized on screen. |
| **Chest AutoMark · Beta** | Combines opening and reward signals to record a nearby chest when the association is reliable. |
| **AppSample progress import** | Reuses your collected items through a preview, merge, and backup workflow. |
| **Organized resource catalog** | Groups resources into subcategories and supports aliases and accent-insensitive searches. Unidentified categories remain labeled as pending. |
| **Location photos** | Click a card photo to enlarge it, zoom, and drag the image. |
| **Independent panel** | Move, resize using the window borders, or collapse it. Settings offer 125% and 150% text/control scaling. |
| **World map and separate areas** | Browse Teyvat, the six permanent separate maps and their installed floors with shared filters, photos and progress. Browsing does not change game tracking. |

The application uses external image recognition. It does not read game memory, inject code, or control the character. Recognition may lose alignment; pins are hidden while the position is recovered.

Choose **Português (Brasil)** or **English** during installation or under **Settings → Idioma / Language** in the main panel. Reopen the application to apply a change. The preference is shared across profiles and preserved by automatic updates.

Changing the application language does not change Genshin. **AutoMark beta** also recognizes pairs of reward icons without relying on game text. Qualified Portuguese text references remain available as a fallback; English-HUD gameplay was confirmed in local testing. The AutoMark switch is above the main panel footer.

## Maps and automatic detection

The 2.0.x series includes **Enkanomiya, The Chasm: Underground Mines,
Sea of Bygone Eras, Ancient Sacred Mountain, Temple of Space and Frost Moon**,
in addition to Teyvat. Choose **Automatic · Detect map** to recover your area from
the minimap or in-game map after tracking is lost, or select a fixed map/floor.
Markers stay hidden when the current location cannot be confirmed.

The planet window opens on the recognized area or the last browsed map. Explore
freely without changing game tracking; **Current area** returns to the recognized
context. The separate maps include their 44 published floors. Expanding Teyvat's
cave coverage and temporary event maps is outside this stage.

Installed images work offline and load on demand. The expansion is available in
the 2.0.x series; in-game validation across maps and layers remains ongoing.

## Start playing

1. Extract the **complete portable package** into a permanent folder, keeping `userData` intact.
2. Open **HexenMap.exe** or **Iniciar_HexenMap.bat**. Accept the administrator prompt when needed to interact with an elevated game.
3. Run Genshin in **windowed or borderless mode**. Choose your map, layer, and items in the panel.
4. Return to the game. Press **F8** to collapse or reopen the panel.

**The ready-to-use package does not require Python or Node.js.** Cloning this repository or copying the `.exe` alone does not install personal map, image, and reference packs. Available coverage depends on the files included in your installation.

The panel can be attached to Genshin or used as an independent window. The Windows tray can reopen it or exit the app. There is no compass, guided search or farming hotkeys.

## Controls

| Default control | Action |
| --- | --- |
| **F8** | Open/collapse the panel. |
| **Ctrl+Alt+F12** | Show/hide pins. |
| **Ctrl + click a pin** | Open its card to mark/unmark it and view photos. |
| **Hold Ctrl** | Reveal collected items in gray. |
| **F9** | Confirm a nearby collection or choose between candidates. |
| **F10** | Undo the session's last collection. |

Hotkeys can be configured under **Ajustes** (Settings). Settings are grouped into collapsible sections for profiles, the panel and screen sharing, AppSample progress, hotkeys and diagnostics. The AutoMark switch is above the main panel footer. Screen-sharing visibility determines whether the overlay appears in captures; it does not turn recognition off.

## Bring your AppSample progress

The test **Hexen Map Exporter** extension for Chrome and Edge captures progress IDs loaded by AppSample itself. Normal export does not require browser developer tools.

1. Extract the extension ZIP and load the **HexenMapExporter** folder at `chrome://extensions` or `edge://extensions`, using **Developer mode → Load unpacked**.
2. Open AppSample while signed in. In the extension, click **Atualizar leitura** (Refresh reading), then check for **Progresso detectado** (Progress detected) after the page loads.
3. Choose a delivery method:

| Option in the interface | Workflow |
| --- | --- |
| **Enviar ao Hexen Map** (Send to Hexen Map) | Enable **Ajustes → Coletados do AppSample → Ativar conexão com a extensão** once in the application. With `HexenMapBridge.exe` next to the application, the button forwards IDs and opens the import preview in Hexen Map. |
| **Baixar JSON** (Download JSON) | Save the file, then choose **Importar arquivo de coletados** in the application's settings. Connector activation is not required. |

Review the preview and confirm the merge. Existing progress is preserved with a backup; importing the same file again does not duplicate collections. IDs without a verified match are not mapped by proximity. Canceling the preview does not apply collections.

Direct delivery uses **Native Messaging**, only on an explicit action, without a server or localhost. The extension does not read cookies, passwords, or tokens and does not modify marks on AppSample. There is no automatic or two-way synchronization. Refresh the reading after changing accounts or collected items on the site. When upgrading from extension 0.1.x, disable the old extension before installing the new one.

[Illustrated installation and permissions](docs/EXPORTER_INSTALL.html) · [Import guide](docs/APPSAMPLE_IMPORT.md)

## AutoMark: automatic assistance with conservative confirmation

**AutoMark is a beta and is off by default.** It requires qualified visual references in your installation and combines interaction, reward, and position signals to associate an opening with one nearby chest.

Enable AutoMark above the footer and return to Genshin to synchronize. Use **↻** to resync; initial preparation does not guarantee a collection. The personal calibration wizard is not included yet.

An uncertain position or multiple candidates do not authorize automatic collection. Manual confirmation remains available, and **F10** undoes the session's last collection. Live validation does not yet cover every rarity, background, resolution, and language.

## Coverage, performance, and current status

- **Maps and layers:** AppSample is the sole operational source of markers and terrain references. Maps without valid references remain unavailable. Imported data does not mean complete coverage has been tested in the game.
- **Progress and preferences:** stored in `%LOCALAPPDATA%\HexenMap\state`, outside the program folder. Local profiles separate accounts. Keep backups and the `userData` folder containing personal map packs.
- **Respawns:** permanent items never expire. Resources without a qualified rule show **Reposição não confirmada** (Respawn unconfirmed); there is no universal timer.
- **References and memory:** managed automatically and loaded on demand. The interface has no Light/Global selector; long-distance travel may require brief recovery.

**Verified so far:** a real Chrome export containing 3,755 unique IDs, with the file accepted by the importer. Full native delivery through the browser and real Edge compatibility remain pending. We do not claim better accuracy, stability, or resource use than other overlays without a controlled comparison.

[Project status](docs/REBUILD.md) · [Coverage](docs/REGIONAL_COVERAGE.md) · [Stability](docs/STABILITY.md) · [Performance](docs/PERFORMANCE.md) · [Exporter tests](docs/EXPORTER_TEST_REPORT.md)

<details>
<summary><strong>Development and builds</strong></summary>

Use a Python version supported by `pyproject.toml` and run from the repository root:

```powershell
python -m pip install -r requirements.txt
python src/app.py
python src/app.py --diagnose
python -m pytest -q
```

JavaScript extension tests also require Node.js in the development environment.

```powershell
python -m pip install pyinstaller
python scripts/build_release.py
python scripts/package_exporter.py
```

The current package is in `dist/atual`, with a versioned ZIP and folder. Extract the complete ZIP; do not move only the executable into an empty folder. Previous deliveries are in `dist/arquivo`. The standalone extension is in `dist/extensoes/<version>`. Load the generated folder; the extension source needs the packager to include the shared core.

`scripts/build_release.py` builds binaries in `build/release-staging` and calls `scripts/package_portable.py` to assemble the portable with verified personal packs. Personal progress is excluded. It does not download or license missing data, and does not silently overwrite an existing release.

[Portuguese catalog review](docs/LOCALIZATION.md) · [Photo sources and cache](docs/MARKER_HINTS.md)

</details>

## Credits and license

Hexen Map is an independent project, unaffiliated with HoYoverse or AppSample. Genshin Impact belongs to HoYoverse. Original code is available under the [MIT license](LICENSE); third-party images, contributions, and data retain their own terms. Personal packs are excluded from Git; the code license does not grant permission to redistribute them.
