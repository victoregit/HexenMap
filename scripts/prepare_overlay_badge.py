"""Install the approved Electro rift as the collapsed overlay badge only."""
from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/HexenMap_Electro_Rift_Spin/electro_spin/frames'
BRAND=ROOT/'data/assets/brand'
COUNT=120
SIDE=192
COLS=8


def main():
    atlas=Image.new('RGBA',(COLS*SIDE,15*SIDE))
    for index in range(COUNT):
        with Image.open(SOURCE/f'frame_{index:03}.png') as frame:
            if frame.size!=(512,512):raise ValueError('Unexpected approved frame size')
            tile=frame.convert('RGBA').resize((SIDE,SIDE),Image.Resampling.LANCZOS)
            atlas.paste(tile,(index%COLS*SIDE,index//COLS*SIDE))
    atlas.save(BRAND/'minimized.png')
    path=BRAND/'animations.json'
    metadata=json.loads(path.read_text(encoding='utf-8'))
    metadata['minimized_frames']=COUNT
    metadata.pop('minimized_keyframes',None)
    metadata['minimized']={
        'file':'minimized.png','frame_size':SIDE,'columns':COLS,'frames':COUNT,
        'durations_ms':[round((i+1)*1000/24)-round(i*1000/24) for i in range(COUNT)],
        'duration_ms':5000,'fps':24,'identity':'electro-rift-spin-v3',
    }
    path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print('Installed approved collapsed badge: 120 frames, 24 FPS, 5000 ms')


if __name__=='__main__':main()
