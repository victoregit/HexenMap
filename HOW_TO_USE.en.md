# Hexen Map — User Guide, Local Execution & Independent Build / How to Use

[Português (Brasil)](HOW_TO_USE.md) · **English**

Practical guide for players, software engineers, and security auditors to run, inspect, test, and build **Hexen Map** in a transparent, reproducible, and verifiable manner.

---

## Table of Contents

1. [Architecture & Overview](#architecture--overview)
2. [Quick Start & Official Releases](#1-quick-start--official-releases)
3. [Running Directly from Source Code](#2-running-directly-from-source-code)
4. [Understanding Data Architecture & `userData`](#3-understanding-data-architecture--userdata)
5. [Running the Automated Test Suite (604 Tests)](#4-running-the-automated-test-suite-604-tests)
6. [Independent Build with PyInstaller](#5-independent-build-with-pyinstaller)
7. [Running the Performance Benchmark Suite](#6-running-the-performance-benchmark-suite)
8. [Security & Privacy Audit Verification](#7-security--privacy-audit-verification)

---

## Architecture & Overview

**Hexen Map** is a desktop exploration overlay for Genshin Impact. It operates **100% as an external transparent overlay window**:
- **Does NOT read game process RAM** (`ReadProcessMemory` / `OpenProcess` do not exist in the codebase).
- **Does NOT inject DLLs** or alter game installation files.
- **Does NOT simulate automated inputs** or bot actions.
- Target detection and alignment rely solely on **passive computer vision** (`Windows.Graphics.Capture`, GDI `BitBlt`, and OpenCV).
- Exploration markings, profiles, and preferences are stored exclusively on your local machine at `%LOCALAPPDATA%\HexenMap\state`.

---

## 1. Quick Start & Official Releases

For most players, there is no need to install Python, Node.js, or build tools:

1. Download the complete portable release package (`HexenMap-VERSION-Windows-x64.zip`) or installer (`HexenMap-VERSION-Setup-x64.exe`) from [Official GitHub Releases](https://github.com/victoregit/HexenMap-Releases).
2. Extract the `.zip` archive to a folder of your choice (e.g., `C:\Games\Hexen Map`). **Keep the `userData` directory alongside `HexenMap.exe`**.
3. Launch **Genshin Impact** in **Windowed** or **Borderless** display mode.
4. Run `HexenMap.exe` (or use the Start menu shortcut created by the installer).
5. In the Hexen Map overlay controls:
   - **F8**: Toggle the item selection panel.
   - **Ctrl + click**: Mark or unmark items on the map.
   - **Ctrl + Alt + F12**: Show or hide all map pins on screen.
   - **F9**: Confirm quick collection of a nearby pin.
   - **F10**: Undo the last collection registered in the session.

---

## 2. Running Directly from Source Code

If you prefer to inspect and run the application directly using Python:

### Prerequisites
- **Windows 10 or 11** (64-bit).
- **Python 3.10 to 3.12** installed with Tkinter support and added to your system PATH.

### Step-by-Step

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/victoregit/HexenMap.git
   cd HexenMap
   ```

2. **Create a virtual environment (recommended):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. **Map Datasets (`userData` setup):**
   Hexen Map's code is 100% open source under the MIT license. However, due to third-party copyright restrictions (HoYoverse / AppSample), raw in-game map tiles, minimap textures, and satellite datasets are not committed directly to the Git repository.
   - Download the latest official portable `.zip` release and copy its `userData` folder into the root directory of your cloned repository.

5. **Verify data readiness (diagnostics):**
   Before launching the full graphical interface, confirm that local references and catalogs are recognized:
   ```powershell
   python src/app.py --diagnose
   ```
   *Expected output:* `{"items": 88957, "region": "appsample", ... "references": "available"}`.

6. **Launch the application:**
   ```powershell
   python src/app.py
   ```

---

## 3. Understanding Data Architecture & `userData`

The directory layout adheres strictly to security, privacy, and open-source licensing boundaries:

- `data/`: Contains verified permissible brand assets, SVG/PNG group icons, bilingual localization bundles (`ui-en-US.json`, `appsample-pt-BR.json`), license texts, and demo markers (`demo_markers.json`).
- `userData/`: Houses external catalogs, visual detector models (`automark/`), and local map tile caches. Excluded from Git tracking via `.gitignore`.
- `%LOCALAPPDATA%\HexenMap\state`: The persistent location for your actual collected item records (`progress.json`) and personal settings. Updating or reinstalling the application never overwrites this directory.

---

## 4. Running the Automated Test Suite (604 Tests)

Hexen Map features a comprehensive test suite of **604 automated unit and integration tests** validating computer vision tracking, import/export integrity, overlay behavior, and safety invariants.

To execute all tests with `pytest`:

```powershell
$env:LANG="en_US.UTF-8"
python -m pytest
```

> [!NOTE]
> Setting `$env:LANG="en_US.UTF-8"` prevents a known Windows Python 3.12 Tcl/Tk 8.6 issue where non-English system locales attempt to locate missing localization message files (`msgs/pt.msg`).

---

## 5. Independent Build with PyInstaller

You can independently compile standalone Windows binaries directly from the repository's source code:

### 1. Build the Main Overlay Executable (`HexenMap.exe`):
```powershell
python scripts/build_exe.py --build-only
```
The compiled standalone binary will be generated at `build/release-staging/HexenMap.exe`.

### 2. Build the Native Messaging Extension Host (`HexenMapBridge.exe`):
```powershell
python -m PyInstaller --noconfirm --distpath build/release-staging HexenMapBridge.spec
```

### 3. Build the Elevated Launcher (`HexenMapLauncher.exe`):
```powershell
python -m PyInstaller --noconfirm --distpath build/release-staging HexenMapLauncher.spec
```

### 4. Package the Companion Browser Extension:
```powershell
python -c "import scripts.package_exporter; print(scripts.package_exporter.package())"
```

---

## 6. Running the Performance Benchmark Suite

To measure runtime CPU load, RAM footprint, and computer vision latency:

```powershell
python scripts/run_benchmarks.py
```

Standard performance profile on modern hardware:
- **Memory Consumption (RSS):** ~38 MB idle / ~48 MB under peak stress workload.
- **CV Template Matching:** ~4.9 ms per minimap frame.
- **HUD Render Latency:** < 0.1 ms per frame (capable of > 1000 FPS without impacting game frame rates).

---

## 7. Security & Privacy Audit Verification

Independent technical audit verified:
- **Restricted Network Access:** Outbound HTTPS calls occur exclusively on direct demand for official GitHub releases (cryptographically verified via SHA-256 digests), public marker hints/photos (`game-cdn.appsample.com`), and voluntary user-initiated feedback (`formsubmit.co`).
- **Zero Telemetry:** No user credentials, cookies, in-game UIDs, or hardware identifiers are ever collected or transmitted.
- **Zero Stealth Persistence:** The software installs no background services, no Task Scheduler entries, and no Windows autostart keys (`Run` registry entries).
- Full security details are documented in [SECURITY.md](SECURITY.md).
