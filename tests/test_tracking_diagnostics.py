import json
import zipfile

import cv2
import numpy as np
import pytest

from src.live.tracking_diagnostics import MinimapRecording


def test_recording_exports_only_bounded_corner_and_actual_geometry(tmp_path):
    recording=MinimapRecording(tmp_path,{'client_size':[1366,768],'automark':True},clock=lambda:100.)
    image=np.full((768,1366,3),127,np.uint8)
    recording.record(image,100.,{'tracking':{'state':'tracking'}})
    recording.close()
    assert recording.done.is_set() and not recording.error
    frame=cv2.imread(str(recording.directory/'0000.jpg'))
    assert frame.shape==(269,410,3)
    rows=[json.loads(line) for line in (recording.directory/'frames.jsonl').read_text().splitlines()]
    assert rows[0]['captured_shape']==[768,1366,3]
    (recording.directory/'progress.json').write_text('private')
    target=tmp_path/'export.zip'
    recording.export(target)
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist())=={'manifest.json','frames.jsonl','0000.jpg'}
        assert json.loads(archive.read('manifest.json'))['uploaded'] is False


def test_recording_stops_at_duration_and_cannot_export_while_running(tmp_path):
    now=[100.]
    recording=MinimapRecording(tmp_path,{},clock=lambda:now[0])
    try:
        with pytest.raises(ValueError):recording.export(tmp_path/'export.zip')
        now[0]=121.
        recording.record(np.zeros((20,20,3),np.uint8),121.,{})
        assert recording.stopping.is_set()
    finally:recording.close()
    assert not list(recording.directory.glob('*.jpg'))


def test_disk_limit_stops_recording_without_partial_frames(tmp_path):
    recording=MinimapRecording(tmp_path,{},clock=lambda:100.)
    recording.max_bytes=16385
    recording.record(np.zeros((20,20,3),np.uint8),100.,{})
    recording.close()
    assert recording.metadata['stop_reason']=='space_limit'
    assert not list(recording.directory.glob('*.jpg'))
