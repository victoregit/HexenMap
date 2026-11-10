from pathlib import Path
import subprocess,sys
from src.live.panel_layout import fitted_size
from src.live.storage import read_settings,write_json


def test_saved_size_scale_validation_and_small_work_area(tmp_path):
    path=tmp_path/'settings.json'
    write_json(path,{'categories':[],'panel':{'width':620,'height':600,'scale':125,'x':-800,'y':0}})
    settings=read_settings(path)['panel']
    assert settings['width']==620 and settings['scale']==125 and settings['x']==-800
    assert fitted_size(100,100,1.,(0,0,1366,728))==(360,440)
    width,height=fitted_size(9000,9000,1.5,(0,0,1366,728))
    assert width<=1350 and height<=656


def test_real_tk_resize_scale_roundtrip_and_restore():
    code='''
from scripts.preview_lunar import PreviewApp
app=PreviewApp(1.,(1366,768));root=app.root;root.attributes('-alpha',0);root.deiconify();root.update()
root.geometry('620x620');root.update();assert app.panel_normal_size==(620,620)
for percent in (125,150,100,125,100):
 app.panel_scale_var.set(str(percent)+'%');app.change_panel_scale();root.update()
 assert root.winfo_width()<=1350 and root.winfo_height()<=680
 assert app.category_browser.font_scale==percent/100
app.reset_panel_size();root.update();assert app.panel_normal_size==(360,540)
assert root.resizable()==(1,1)
app.toggle_panel(save=False);root.update();assert root.resizable()==(0,0)
app.toggle_panel(save=False);root.update();assert app.panel_normal_size==(360,540)
app.compact.stop();root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=True,timeout=30)


def test_version_footer_and_no_blank_strip_after_scrolling_short_list():
    code='''
from scripts.preview_lunar import PreviewApp
from src.live.identity import VERSION
app=PreviewApp(1.,(1366,768));root=app.root
root.attributes('-alpha',0);root.deiconify();root.geometry('360x620');root.update()
assert app.version_label.cget('text')=='v'+VERSION
assert app.version_label.winfo_ismapped()
c=app.category_browser
c.rows=(c.rows*7)[:7];c.sync_scrollregion();root.update()
assert len(c.rows)*c.HEIGHT<c.winfo_height()
for direction in (-1,1,-1):
 c.yview_scroll(direction,'units');root.update()
 assert c.canvasy(0)==0
app.show_settings();root.update()
assert app.version_label.winfo_ismapped()
app.compact.stop();root.destroy()
'''
    subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,check=True,timeout=30)


def test_release_version_is_consistent():
    import tomllib
    from src.live.identity import VERSION
    root=Path(__file__).resolve().parents[1]
    assert VERSION=='1.0.3'
    assert tomllib.loads((root/'pyproject.toml').read_text())['project']['version']==VERSION
    resource=(root/'data/windows/version_info.txt').read_text()
    assert f"StringStruct('ProductVersion','{VERSION}')" in resource
    assert 'filevers=(1,0,3,0)' in resource
