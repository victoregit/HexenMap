"""Production entry point. The former simulation lives in legacy_app.py."""
from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live.i18n import tr as _tr
from src.live.regions import RegionalCatalog
from src.live.reference import load_pack, ReferenceUnavailable
from src.live.reference_store import read_spec
from src.live.storage import bundle_dir, install_dir, read_settings
from src.live.identity import DISPLAY_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description="Ícones nos mapas nativos do Genshin")
    parser.add_argument("--references", type=Path, help="Pasta de referências visuais pessoais")
    parser.add_argument("--diagnose", action="store_true", help="Verificar dados sem abrir interface")
    args = parser.parse_args()
    if args.diagnose:
        try:
            catalogs=RegionalCatalog(bundle_dir()/"data/community",install_dir()/'userData/catalogs')
            from src.live.personal_state import state_directory
            settings=read_settings(state_directory()/"settings.json")
            package=settings.get('package',catalogs.default_package(install_dir()/'userData/references'))
            if not catalogs.accepts(package): package='appsample'
            items,region,space=catalogs.load(package)
            from src.live.loading import ProcessCatalogSource
            worker=ProcessCatalogSource(catalogs.community,install_dir()/'userData/catalogs')
            try:
                worker_package=worker(package)
                if [i.id for i in worker_package.items]!=[i.id for i in items]:
                    raise ValueError(_tr('Catálogo do processo auxiliar não corresponde à instalação'))
            finally:worker.close()
            default='as-map-2 / surface'
            layer=settings.get('regional',{}).get(package,{}).get('layer',default)
            mapid,layerid=layer.split(' / ')
            references=args.references or install_dir()/'userData/references/appsample'
            if not args.references and mapid!='*':
                references=references/mapid
                if layerid!='automática':references=references/layerid
            if args.references and (references/'manifest.json').is_file():
                manifest=json.loads((references/'manifest.json').read_text(encoding='utf-8'))
                read_spec(references,region_id=region,map_id=manifest.get('map_id','teyvat') if mapid=='*' else mapid,
                          layer_id=None if layerid=='automática' else layerid,coordinate_system=space)
            elif layerid=='automática':
                candidates=list(references.glob('*/*/manifest.json' if mapid=='*' else '*/manifest.json'))
                if not candidates: raise ReferenceUnavailable(_tr('Nenhuma camada com referência instalada'))
                for candidate in candidates:
                    read_spec(candidate.parent,region_id=region,map_id=candidate.parent.parent.name if mapid=='*' else mapid,
                              layer_id=candidate.parent.name,coordinate_system=space)
            else:
                read_spec(references,region_id=region,map_id=mapid,layer_id=None if layerid=='automática' else layerid,coordinate_system=space)
            from src.live.marker_art import CHESTS,chest_art
            chest_images={category:chest_art(category) is not None for category in sorted(CHESTS)}
            print(json.dumps({"items": len(items),"region":region,"map":mapid,"layer":layerid,"catalog_worker":"available",
                              "personal_chest_art":chest_images,"performance_mode":settings.get("performance_mode","light"),
                              "references": "available", "live_validated": False,
                              "expansion_complete":catalogs.inventory['coverage_complete']}))
            return 0
        except (ReferenceUnavailable, ValueError, OSError, RuntimeError) as exc:
            print(json.dumps({"ready": False, "reason": str(exc)}, ensure_ascii=True))
            return 2
    if sys.platform != "win32":
        parser.error("O overlay ao vivo requer Windows 10/11")
    user_dir = install_dir()/"userData"
    user_dir.mkdir(exist_ok=True)
    logging.basicConfig(filename=user_dir/"overlay.log", encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from src.live.desktop import DesktopApp
    from src.live.native import OverlayAlreadyRunning
    from src.live.personal_state import OpeningCancelled
    try:
        DesktopApp(args.references).run()
        return 0
    except (OverlayAlreadyRunning,OpeningCancelled):
        return 0
    except Exception as exc:
        logging.exception("Não foi possível iniciar")
        from src.live.alerts import showerror
        showerror(_tr(DISPLAY_NAME), _tr('Não foi possível iniciar: {0}\n\nO aplicativo será encerrado. Nenhum progresso vazio substituirá suas marcações.', exc))
        return 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(_tr(main()))
