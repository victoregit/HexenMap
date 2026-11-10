"""Own-window QA with existing tiles and a temporary copy of progress; no game capture."""
from pathlib import Path
import sys,tempfile,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.preview_lunar import PreviewApp
from src.live.regions import RegionalCatalog
from src.live.storage import bundle_dir,install_dir
from src.live.session import Session
from src.progress.progress_manager import ProgressManager
from src.live.native import Windows


if __name__=='__main__':
    temporary=tempfile.TemporaryDirectory(prefix='hexen-map-qa-')
    progress=Path(temporary.name)/'progress.json'
    shutil.copy2(install_dir()/'userData/progress.json',progress)
    app=PreviewApp(1.,(1366,768),visible=True)
    native=Windows();native.capture_visible=True;app.native=native;app.root._lunar_native=native
    catalogs=RegionalCatalog(bundle_dir()/'data/community',install_dir()/'userData/catalogs')
    package=catalogs.load_package('appsample');app.session=Session(package.items,ProgressManager(str(progress)))
    app.session.rules=catalogs.rules;app.session.selected={'common-chest','anemoculus','cryoculus'}
    app.category_metadata=package.categories;app.build_category_rows(package.categories)
    app.marker_hints=None;app.world_map=None
    def close():
        if app.world_map:app.world_map.close()
        app.compact.stop();app.root.destroy()
    app.root.protocol('WM_DELETE_WINDOW',close)
    app.open_world_map();app.world_map.window.title('Teyvat · PRÉVIA (coletas temporárias)');app.root.mainloop();temporary.cleanup()
