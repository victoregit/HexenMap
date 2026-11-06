# Task Specification: Build Standalone Windows Executable (.exe)

## Objective
Build and place a standalone Windows executable `GenshinOverlay.exe` directly in the root of the project directory (`/mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe` / `D:\Projects\GenshinGemWish\GenshinOverlay.exe`) so the user can run the overlay by simply double-clicking the file on Windows without installing Python or running terminal commands.

---

## Workspace Root
Absolute path: `/mnt/d/Projects/GenshinGemWish`

---

## Technical Details & Environment
- Windows Python 3.12 is located at:
  `/mnt/c/Users/Usuario/AppData/Local/Programs/Python/Python312/python.exe`
- When invoking Windows executables from bash, always redirect standard input `< /dev/null` to prevent stdin blocking.
- Install PyInstaller and requirements in Windows Python:
  `"/mnt/c/Users/Usuario/AppData/Local/Programs/Python/Python312/python.exe" -m pip install pyinstaller opencv-python Pillow numpy psutil < /dev/null`

---

## Requirements

### 1. Build Script (`scripts/build_exe.py`)
Create a robust build script that:
- Collects `data/demo_markers.json` and embeds it in the executable (`--add-data` specification).
- Configures PyInstaller options:
  - Entry point: `src/app.py`
  - Name: `GenshinOverlay`
  - Mode: `--onefile`
  - Hidden imports for Tkinter, OpenCV, ctypes, and psutil.
  - Generates the `.exe` into `dist/GenshinOverlay.exe` and automatically copies it to the workspace root:
    `/mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe`

### 2. Standalone Executable Delivery
- Ensure the final standalone binary is created at:
  `/mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe`
- Verify with `file /mnt/d/Projects/GenshinGemWish/GenshinOverlay.exe` (should report `PE32+ executable (GUI) x86-64, for MS Windows`).
- Also create a convenient `Iniciar_Overlay.bat` batch script in the root directory that allows launching with specific options (e.g. `--demo --tracking simulated`).

### 3. Verification & Documentation
- Test running the build script.
- Verify that `pytest tests/` still passes 100%.
- Update `README.md` to document the presence of `GenshinOverlay.exe` and `Iniciar_Overlay.bat`.
- Return a summary with the exact file size and verification details.
