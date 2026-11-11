from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from src.live.automark import AutoMark,ChestSignals,OpeningEvent
from src.live.catalog import Item
from src.live.session import Session
from src.live.vision import Observation
from src.live.storage import read_settings,write_json
from src.live.chest_types import CHEST_NAMES
from src.progress.progress_manager import ProgressManager


def setup(tmp_path,positions):
    items=[Item(f'appsample:marker:{n}','Baú','common-chest',x,y,region_id='appsample',map_id='as-map-2')
           for n,(x,y) in enumerate(positions)]
    session=Session(items,ProgressManager(str(tmp_path/'progress.json')))
    session.region_id='appsample';session.map_id='as-map-2';session.layer_id='surface'
    obs=Observation('minimap',10,np.eye(2,3),.95,.4,(100,100,60),(100,100),map_id='as-map-2',layer_id='surface')
    return session,OpeningEvent(1,10,obs)


def test_clear_opening_marks_even_when_chest_filter_is_off_and_undo_restores(tmp_path):
    session,event=setup(tmp_path,[(102,100)])
    auto=AutoMark();assert not session.selected
    assert auto.apply(event,session,11)=='marked'
    assert session.is_collected(session.items[0].id)
    assert auto.apply(event,session,11.1)=='duplicate'
    session.undo();assert not session.is_collected(session.items[0].id)


@pytest.mark.parametrize('category',list(CHEST_NAMES))
def test_all_five_chest_categories_can_be_confirmed_without_a_gem_signal(tmp_path,category):
    from dataclasses import replace
    session,event=setup(tmp_path,[(102,100)])
    session.items=[replace(session.items[0],category=category)]
    signals=ChestSignals(tmp_path);signals.ready=True
    signals.advance({'opening':True},event.observation,10)
    signals.advance({'opening':True},event.observation,10.1)
    assert signals.advance({'loot':True},event.observation,10.2) is None
    detected=signals.advance({'adventure_exp':True},event.observation,10.3)
    assert detected is not None
    assert AutoMark().apply(detected,session,10.3)=='marked'
    session.undo();assert not session.is_collected(session.items[0].id)


def test_chest_prompt_followed_only_by_generic_plant_loot_is_insufficient(tmp_path):
    session,event=setup(tmp_path,[(102,100)])
    signals=ChestSignals(tmp_path);signals.ready=True
    signals.advance({'opening':True},event.observation,10)
    signals.advance({'opening':True},event.observation,10.1)
    for stamp in (10.2,10.3,10.4):
        assert signals.advance({'loot':True},event.observation,stamp) is None


def test_many_nearby_chests_require_explicit_choice_and_expire(tmp_path):
    session,event=setup(tmp_path,[(102,100),(103,100)])
    auto=AutoMark();assert auto.apply(event,session,11)=='ambiguous'
    assert len(auto.choices(session,11))==2
    assert not session.progress.get_collected_ids()
    session.layer_id='other';assert not auto.choices(session,12)
    session.layer_id='surface';auto=AutoMark();auto.apply(event,session,11)
    assert not auto.choices(session,21.1)


def test_nearest_already_collected_never_selects_the_next_chest(tmp_path):
    session,event=setup(tmp_path,[(101,100),(113,100)])
    session.set_collected(session.items[0].id,True)
    assert AutoMark().apply(event,session,11)=='ignored'
    assert not session.is_collected(session.items[1].id)


def test_stale_or_other_map_evidence_never_changes_progress(tmp_path):
    session,event=setup(tmp_path,[(102,100)])
    assert AutoMark().apply(event,session,16.1)=='ignored'
    session.map_id='as-map-3'
    assert AutoMark().apply(event,session,11)=='ignored'


def test_failed_save_is_rolled_back_and_cannot_skip_to_another_chest(tmp_path,monkeypatch):
    session,event=setup(tmp_path,[(102,100)])
    monkeypatch.setattr(session.progress,'save',lambda:(_ for _ in ()).throw(OSError('disk')))
    auto=AutoMark()
    with pytest.raises(OSError):auto.apply(event,session,11)
    assert not session.progress.get_collected_ids()
    assert auto.apply(event,session,11)=='duplicate'


def test_rewards_alone_and_repeated_loot_wave_are_not_openings(tmp_path):
    session,event=setup(tmp_path,[(102,100)])
    signals=ChestSignals(tmp_path);assert not signals.ready
    signals.ready=True
    reward={'loot':True,'primogem':True}
    assert signals.advance(reward,event.observation,10) is None
    assert signals.advance({'opening':True},event.observation,10.1) is None
    assert signals.advance({'opening':True},event.observation,10.2) is None
    assert signals.advance({'loot':True},event.observation,10.3) is None
    detected=signals.advance({'primogem':True},event.observation,10.4)
    assert detected and detected.observation is event.observation
    assert signals.advance(reward,event.observation,10.5) is None


def test_unknown_template_pack_cannot_enable_detector(tmp_path):
    write_json(tmp_path/'manifest.json',{'schema':1,'validation':{'approved':True}})
    assert not ChestSignals(tmp_path).ready


def test_single_flash_and_rewards_without_gems_do_not_confirm_chest(tmp_path):
    session,event=setup(tmp_path,[(102,100)]);signals=ChestSignals(tmp_path);signals.ready=True
    assert signals.advance({'opening':True},event.observation,10) is None
    assert signals.advance({'loot':True,'primogem':True},event.observation,10.1) is None
    signals.reset()
    signals.advance({'opening':True},event.observation,10)
    signals.advance({'opening':True},event.observation,10.1)
    assert signals.advance({'loot':True},event.observation,10.2) is None
    assert signals.advance({'loot':True},event.observation,10.3) is None


def test_teleport_or_layer_change_discards_unfinished_reward_sequence(tmp_path):
    from dataclasses import replace
    session,event=setup(tmp_path,[(102,100)])
    for changed in (replace(event.observation,player=(1000,1000)),replace(event.observation,layer_id='cave')):
        signals=ChestSignals(tmp_path);signals.ready=True
        signals.advance({'opening':True},event.observation,10)
        signals.advance({'opening':True},event.observation,10.1)
        assert signals.advance({'loot':True,'primogem':True},changed,10.2) is None


@pytest.mark.parametrize('size',[(1366,768),(1920,1080),(2560,1440),(3840,2160),(2560,1080),(1440,1080)])
def test_hud_scales_with_window_height_and_preserves_side_and_center_anchors(tmp_path,size):
    import cv2
    signals=ChestSignals(tmp_path);signals.ready=True
    frame=np.full((size[1],size[0],3),50,np.uint8)
    for role,x,y,label,roi in [('opening',1200,450,'BAU',(.59,.37,.23,.23)),
                               ('loot',120,500,'EXP',(.045,.27,.22,.49)),
                               ('primogem',120,600,'GEMA',(.045,.27,.22,.49))]:
        template=np.full((40,110,3),50,np.uint8)
        cv2.putText(template,label,(6,28),cv2.FONT_HERSHEY_SIMPLEX,.8,(250,250,250),2,cv2.LINE_AA)
        signals.templates[role]=(cv2.cvtColor(template,cv2.COLOR_BGR2GRAY),roi,.88)
        scale=size[1]/1080
        patch=cv2.resize(template,(round(110*scale),round(40*scale)))
        left=round(x*scale+((size[0]-1920*scale)/2 if role=='opening' else 0));top=round(y*scale)
        frame[top:top+patch.shape[0],left:left+patch.shape[1]]=patch
    assert signals.measure(frame)==dict.fromkeys(signals.templates,True)
    def capture(rect,*,region):
        x,y,w,h=region
        return frame[y:y+h,x:x+w]
    assert signals.capture_signals(SimpleNamespace(capture=capture),SimpleNamespace(width=size[0],height=size[1]))==signals.measure(frame)


def test_legacy_capture_size_is_metadata_and_full_hd_is_default(tmp_path):
    assert ChestSignals(tmp_path).reference_size==(1920,1080)


@pytest.mark.parametrize('scale',[768/1080,1.,2.])
def test_proximity_and_ambiguity_keep_the_same_territorial_meaning_at_other_resolutions(tmp_path,scale):
    from dataclasses import replace
    session,event=setup(tmp_path,[(114,100),(119,100)])
    obs=replace(event.observation,world_to_screen=np.eye(2,3)*scale,
                circle=(100*scale,100*scale,60*scale))
    assert AutoMark().apply(replace(event,observation=obs,hud_scale=scale),session,11)=='ambiguous'


def test_resizing_during_an_opening_discards_the_old_pixel_context(tmp_path):
    session,event=setup(tmp_path,[(102,100)])
    signals=ChestSignals(tmp_path);signals.ready=True
    signals.advance({'opening':True},event.observation,10)
    signals.advance({'opening':True},event.observation,10.1)
    signals.hud_scale=2.
    assert signals.advance({'loot':True,'primogem':True},event.observation,10.2) is None


def test_reward_text_remains_recognizable_below_fixed_white_threshold(tmp_path):
    import cv2
    signals=ChestSignals(tmp_path)
    template=np.full((32,150),70,np.uint8)
    cv2.putText(template,'EXP AVENTURA',(3,22),cv2.FONT_HERSHEY_SIMPLEX,.48,240,1,cv2.LINE_AA)
    # A different translucent panel reduces all glyph pixels below 205.
    altered=np.rint(150+(template.astype(float)-70)*.3).astype(np.uint8)
    crop=np.full((70,250,3),150,np.uint8)
    crop[20:52,60:210]=altered[:,:,None]
    assert signals.score_crop(crop,template,1080,'local_contrast')>.95
    assert signals.score_crop(crop,template,1080,'white_glyph')<.2
    assert signals.score_crop(np.full_like(crop,150),template,1080,'local_contrast')<.2


def test_checkbox_is_opt_in_and_persisted(tmp_path):
    path=tmp_path/'settings.json';assert read_settings(path)['automark'] is False
    write_json(path,{'categories':[],'automark':True,'regional':None})
    assert read_settings(path)['automark'] is True


@pytest.mark.parametrize('factor',[.8,.9,1.1,1.2])
def test_opening_glyph_calibrates_hud_scale_without_lowering_threshold(tmp_path,factor):
    import cv2
    signals=ChestSignals(tmp_path)
    template=np.full((40,110),50,np.uint8)
    cv2.putText(template,'BAU',(6,28),cv2.FONT_HERSHEY_SIMPLEX,.8,250,2,cv2.LINE_AA)
    signals.templates={'opening':(template,(.4,.2,.5,.6),.88)}
    frame=np.full((1080,1920,3),50,np.uint8)
    patch=cv2.resize(template,(round(110*factor),round(40*factor)),interpolation=cv2.INTER_CUBIC)
    frame[400:400+patch.shape[0],1000:1000+patch.shape[1]]=patch[:,:,None]
    for _ in range(4):
        result=signals.read_signals(1920,1080,lambda box:frame[box[1]:box[1]+box[3],box[0]:box[0]+box[2]])
        if result['opening']:break
    assert result['opening']
    assert signals.detected_hud_height==pytest.approx(1080*factor)
    assert signals.read_signals(1920,1080,lambda b:frame[b[1]:b[1]+b[3],b[0]:b[0]+b[2]])['opening']


def test_old_global_preference_uses_bounded_backend_and_preserves_selection(tmp_path):
    path=tmp_path/'settings.json'
    write_json(path,{'categories':['common-chest'],'performance_mode':'global','automark':True})
    settings=read_settings(path)
    assert settings['performance_mode']=='light'
    assert settings['categories']==['common-chest'] and settings['automark'] is True
