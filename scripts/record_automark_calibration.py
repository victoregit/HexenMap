"""Record a short, explicitly requested game-only visual calibration; never sends input."""
import argparse,json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
from src.live.native import Windows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=30)
    parser.add_argument('--kind',choices=['opening','negative'],required=True)
    args=parser.parse_args()
    native=Windows();native.enable_dpi();native.capture_visible=True
    if not native.u.GetForegroundWindow():
        raise RuntimeError('Sessão sem acesso ao desktop interativo; nenhuma captura iniciada.')
    out=Path('userData/automark/calibration')/(time.strftime('%Y%m%d-%H%M%S')+'-'+args.kind)
    out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();frames=[]
    try:
        while time.monotonic()-start<min(45,max(1,args.seconds)):
            tick=time.monotonic();rect=native.game()
            if native.foreground(rect):
                frame=native.capture(rect)
                if frame is not None:
                    name=f'{len(frames):04}.jpg'
                    if not cv2.imwrite(str(out/name),frame,[cv2.IMWRITE_JPEG_QUALITY,90]):
                        raise OSError('Não foi possível salvar a captura')
                    frames.append({'file':name,'elapsed_s':tick-start,'width':rect.width,'height':rect.height})
            time.sleep(max(.001,1/6-(time.monotonic()-tick)))
    finally:native.close_capture()
    manifest={'kind':args.kind,'source':'Game client DC, user-requested personal calibration',
              'reviewed':False,'usable':bool(frames),'frames':frames,'duration_s':time.monotonic()-start}
    (out/'session.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'directory':str(out.resolve()),'frames':len(frames),'reviewed':False}))


if __name__=='__main__':main()
