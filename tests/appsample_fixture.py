"""Small synthetic AppSample package; tests do not require retired providers or personal data."""
import json,hashlib
from src.live.regions import RegionalCatalog
from src.live.appsample_catalog import SPACE

def make_catalog(tmp_path):
    directory=tmp_path/'catalogs/appsample';directory.mkdir(parents=True,exist_ok=True)
    rows=[dict(id='appsample:marker:1',name='Baú',category='common-chest',x=10,y=20,region_id='appsample',map_id='as-map-2',layer_id='surface',rule_id='permanent'),
          dict(id='appsample:marker:2',name='Flor',category='flower',x=30,y=40,region_id='appsample',map_id='as-map-2',layer_id='surface',rule_id='unknown'),
          dict(id='appsample:marker:3',name='Baú subterrâneo',category='common-chest',x=10,y=20,region_id='appsample',map_id='as-map-3',layer_id='as-layer-1-1',layer_ids=['as-layer-1-1'],rule_id='permanent')]
    raw=json.dumps({'items':rows}).encode();(directory/'items.json').write_bytes(raw)
    source={'region_id':'appsample','coordinate_system':SPACE,'version':'test-v1',
            'categories':{'common-chest':{'name':'Baús comuns','group':'Baús'},'flower':{'name':'Flor','group':'Recursos'}},
            'files':[{'file':'items.json','format':'normalized-v1','sha256':hashlib.sha256(raw).hexdigest()}]}
    (directory/'SOURCE.json').write_text(json.dumps(source),encoding='utf-8')
    return RegionalCatalog(tmp_path/'absent-community',tmp_path/'catalogs')
