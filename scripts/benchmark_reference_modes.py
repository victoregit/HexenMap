"""Compare recognition on identical local captures; never controls the game."""
import argparse,gc,json,time,subprocess,types
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np,psutil
from src.live.reference import load_pack
from src.live.reference_store import read_spec
from src.live.budget_vision import BudgetRecognizer
from src.live.vision import ScreenRecognizer

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--reference',type=Path,required=True)
 parser.add_argument('--capture',type=Path,required=True)
 parser.add_argument('--mode',choices=['baseline','light','global'],required=True)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--frames',type=int,default=30)
 parser.add_argument('--baseline-ref',default='b0428a6')
 args=parser.parse_args();meta=json.loads((args.reference/'manifest.json').read_text(encoding='utf-8'))
 process=psutil.Process();start=time.perf_counter();cpu=time.process_time()
 if args.mode=='baseline':
  source=subprocess.run(['git','show',args.baseline_ref+':src/live/vision.py'],check=True,capture_output=True,text=True,encoding='utf-8').stdout
  module=types.ModuleType('hexen_benchmark_baseline');sys.modules[module.__name__]=module
  exec(compile(source,'<baseline-vision>','exec'),module.__dict__)
  recognizer=module.ScreenRecognizer(load_pack(args.reference,meta['region'],meta['map_id'],meta['layer'],meta['coordinate_system']))
 else:
  spec=read_spec(args.reference,meta['region'],meta['map_id'],meta['layer'],meta['coordinate_system'])
  recognizer=BudgetRecognizer([spec],Path('userData/cache/references'),args.mode)
 startup=time.perf_counter()-start;startup_cpu=time.process_time()-cpu
 sequence=None
 if args.capture.suffix=='.npz':
  with np.load(args.capture) as archive:
   shape=tuple(int(v) for v in archive['shape']);all_frames=archive['frames']
   indices=np.linspace(0,len(all_frames)-1,args.frames).astype(int)
   sequence=all_frames[indices].copy()
  del all_frames
  frame=np.zeros(shape,np.uint8)
 else:frame=cv2.imread(str(args.capture))
 results=[]
 for n in range(args.frames):
  if sequence is not None:
   frame.fill(0);crop=sequence[n];frame[:crop.shape[0],:crop.shape[1]]=crop
  tick=time.perf_counter();cpu=time.process_time();obs=recognizer.observe(frame,time.monotonic())
  results.append({'surface':obs.surface,'elapsed_ms':(time.perf_counter()-tick)*1000,'cpu_ms':(time.process_time()-cpu)*1000,'error_px':obs.error_px if np.isfinite(obs.error_px) else None,
                  'matrix':obs.world_to_screen.tolist() if obs.world_to_screen is not None else None})
  if n%10==0:print(args.mode,n,obs.surface,round(process.memory_info().rss/1024**2,1),flush=True)
 memory=process.memory_info()
 result={'mode':args.mode,'startup_s':startup,'startup_cpu_s':startup_cpu,'rss_MiB':memory.rss/1024**2,'peak_rss_MiB':getattr(memory,'peak_wset',memory.rss)/1024**2,
         'threads':cv2.getNumThreads(),'results':results,'diagnostics':recognizer.diagnostics() if hasattr(recognizer,'diagnostics') else {}}
 if hasattr(recognizer,'close'):recognizer.close()
 gc.collect();result['released_rss_MiB']=process.memory_info().rss/1024**2
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='results'}),flush=True)
if __name__=='__main__':main()
