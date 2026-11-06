"""Production entry point. The former simulation lives in legacy_app.py."""
from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live.catalog import load_catalog
from src.live.reference import load_pack, ReferenceUnavailable
from src.live.storage import bundle_dir, install_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Ícones nos mapas nativos do Genshin")
    parser.add_argument("--references", type=Path, help="Pasta de referências visuais pessoais")
    parser.add_argument("--diagnose", action="store_true", help="Verificar dados sem abrir interface")
    args = parser.parse_args()
    references = args.references or install_dir()/"userData/references/mondstadt"
    if args.diagnose:
        try:
            items = load_catalog(bundle_dir()/"data/community/mondstadt")
            load_pack(references)
            print(json.dumps({"items": len(items), "references": "available", "live_validated": False}))
            return 0
        except (ReferenceUnavailable, ValueError, OSError) as exc:
            print(json.dumps({"ready": False, "reason": str(exc)}, ensure_ascii=True))
            return 2
    if sys.platform != "win32":
        parser.error("O overlay ao vivo requer Windows 10/11")
    user_dir = install_dir()/"userData"
    user_dir.mkdir(exist_ok=True)
    logging.basicConfig(filename=user_dir/"overlay.log", encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from src.live.desktop import DesktopApp
    try:
        DesktopApp(references).run()
        return 0
    except Exception as exc:
        logging.exception("Não foi possível iniciar")
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Genshin Gem Wish", f"Não foi possível iniciar: {exc}", parent=root)
        root.destroy()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
