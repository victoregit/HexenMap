"""Install only the approved transparent Traveler constellation into the launcher."""
from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'artifacts/HexenMap_Traveler_Loading/loading/frames'
BRAND=ROOT/'data/assets/brand'


def main():
    atlas=Image.new('RGBA',(48*192,192))
    (BRAND/'loading').mkdir(exist_ok=True)
    for index in range(48):
        with Image.open(SOURCE/f'frame_{index:03}.png') as image:
            frame=image.convert('RGBA').resize((192,192),Image.Resampling.LANCZOS)
        frame.save(BRAND/'loading'/f'{index:02}.png')
        atlas.paste(frame,(index*192,0))
    atlas.save(BRAND/'loading.png')
    path=BRAND/'animations.json';metadata=json.loads(path.read_text(encoding='utf-8'))
    metadata['loading_frames']=48
    metadata['loading_identity']='traveler-viator-transparent-v3'
    metadata['loading_durations_ms']=[round((i+1)*1000/24)-round(i*1000/24) for i in range(48)]
    path.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print('Launcher installed: transparent Traveler constellation only, 24 FPS, 2 seconds')


if __name__=='__main__':main()
