"""Opt-in chest guidance in minimap coordinates; no camera or game input control."""
from dataclasses import dataclass
import math
import logging
import numpy as np

CHESTS=frozenset(('common-chest','exquisite-chest','precious-chest','luxurious-chest','remarkable-chest'))
CHEST_NAMES={'common-chest':'Baú comum','exquisite-chest':'Baú sofisticado','precious-chest':'Baú precioso',
             'luxurious-chest':'Baú luxuoso','remarkable-chest':'Baú extraordinário'}


@dataclass(frozen=True)
class Guidance:
    target_id: str
    category: str
    direction: tuple[float,float]
    north: tuple[float,float]
    nearby: bool
    proximity: str = 'Mais distante'
    arrived: bool = False


class ChestFarm:
    def __init__(self):
        self.enabled=False
        self.target_id=None
        self.origin=None
        self.context=None
        self.surface_context=None
        self.skipped=set()
        self.status=''
        self.search_key=None
        self.last_search=-math.inf
        self.arrival_target=None
        self.arrived=False

    @property
    def status(self):return self._status

    @status.setter
    def status(self,value):
        if value!=getattr(self,'_status',None):
            logging.getLogger(__name__).info('Farm state=%s target=%s',value,getattr(self,'target_id',None))
        self._status=value

    @staticmethod
    def scope(session):
        return (id(session.items),session.region_id,session.map_id,session.layer_id,session.area_id)

    def start(self,session):
        self.enabled=True;self.target_id=None;self.origin=None
        self.context=self.scope(session);self.surface_context=None;self.skipped.clear()
        self.search_key=None;self.last_search=-math.inf
        self.arrival_target=None;self.arrived=False
        self.status='Volte ao jogo para iniciar a bússola.'

    def stop(self):
        self.enabled=False;self.target_id=None;self.status=''
        self.arrival_target=None;self.arrived=False

    def skip(self):
        if self.target_id:self.skipped.add(self.target_id)
        self.target_id=None

    def update(self,session,observation,now):
        if not self.enabled:return None
        if self.context!=self.scope(session):
            self.stop();self.status='Farm encerrado: mapa ou seleção territorial alterados.';return None
        obs=observation
        if (session.hidden or obs.surface!='minimap' or not obs.fresh(now) or obs.player is None
                or not np.isfinite(obs.player).all() or obs.circle is None):
            self.status='Bússola aguardando localização no minimapa.';return None
        if ((session.map_id and obs.map_id!=session.map_id) or not obs.map_id or not obs.layer_id
                or (session.layer_id and obs.layer_id!=session.layer_id)):
            self.status='Bússola aguardando o mapa e a camada selecionados.';return None
        surface=(obs.map_id,obs.layer_id)
        if self.surface_context is not None and surface!=self.surface_context:
            self.stop();self.status='Farm encerrado: mapa ou camada alterados.';return None
        self.surface_context=surface
        if self.origin is None:self.origin=tuple(obs.player)
        selected=session.selected & CHESTS
        if not selected:
            self.target_id=None;self.status='Selecione ao menos um tipo de baú.';return None
        target=session.item_by_id(self.target_id) if self.target_id else None
        def eligible(item):
            return (item is not None and bool(set(item.category_ids or (item.category,)) & selected)
                    and item.map_id==obs.map_id and obs.layer_id in (item.layer_ids or (item.layer_id,))
                    and item.id not in self.skipped and not session.is_collected(item.id))
        if not eligible(target):
            key=(frozenset(selected),len(self.skipped),session.progress.collected_count)
            if self.target_id is None and key==self.search_key and 0<=now-self.last_search<.5:return None
            self.search_key=key;self.last_search=now
            candidates=(i for i in session.scoped_items() if eligible(i))
            px,py=obs.player
            target=min(candidates,key=lambda i:((i.x-px)**2+(i.y-py)**2,i.id),default=None)
            self.target_id=target.id if target else None
        if target is None:
            self.status='Nenhum baú disponível nos filtros. Reinicie para rever os pulados.';return None
        if obs.heading_screen is None or not math.isfinite(obs.heading_screen) or obs.heading_confidence<.7:
            self.status='Bússola aguardando a direção do personagem.';return None
        vector=obs.world_to_screen[:,:2]@np.array([target.x-obs.player[0],target.y-obs.player[1]])
        distance=float(np.linalg.norm(vector))
        if self.arrival_target!=target.id:self.arrived=False;self.arrival_target=target.id
        if distance<=6:self.arrived=True
        elif distance>9:self.arrived=False
        direction=tuple(vector/max(distance,1e-9)) if distance>.01 else (0.,-1.)
        north=obs.world_to_screen[:,:2]@np.array([0.,-1.])
        north=tuple(north/max(float(np.linalg.norm(north)),1e-9))
        angle=math.radians(obs.heading_screen)
        rotation=np.array([[math.cos(angle),math.sin(angle)],[-math.sin(angle),math.cos(angle)]])
        direction=tuple(rotation@direction);north=tuple(rotation@north)
        self.status='No local do baú · confirme a coleta.' if self.arrived else 'Baú próximo · confirme a coleta.' if distance<=22 else 'Siga a bússola · confirme cada coleta.'
        category=next((c for c in (target.category,*target.category_ids) if c in selected),target.category)
        proximity='Próximo' if distance<=22 else 'Na vizinhança' if distance<=obs.circle[2] else 'Mais distante'
        return Guidance(target.id,category,direction,north,distance<=22,'No local' if self.arrived else proximity,self.arrived)


class CompassCanvas:
    """Retained, click-through 2D compass near the default character foot position."""
    TAG='farm-compass'

    def __init__(self,canvas):self.canvas=canvas

    def hide(self):self.canvas.itemconfigure(self.TAG,state='hidden')

    def render(self,guidance,width,height,dpi=1.,controls=()):
        c=self.canvas
        if guidance is None:self.hide();return
        scale=max(.75,min(dpi,2.5));x,y=width*.5,height*.78;r=25*scale
        box=(x-100*scale,y-r-12*scale,x+100*scale,y+r+46*scale)
        if any(box[0]<b[2] and box[2]>b[0] and box[1]<b[3] and box[3]>b[1] for b in controls):
            self.hide();return
        if not c.find_withtag(self.TAG):
            c.create_oval(0,0,1,1,fill='#182739',outline='#cbb88a',width=1,tags=(self.TAG,'farm-ring'))
            c.create_polygon(0,0,1,1,2,2,fill='#eee9df',outline='#cbb88a',tags=(self.TAG,'farm-arrow'))
            c.create_text(0,0,text='N',fill='#eee9df',tags=(self.TAG,'farm-north'))
            c.create_text(0,0,text='Baú',fill='#eee9df',tags=(self.TAG,'farm-caption'))
        c.itemconfigure(self.TAG,state='normal')
        c.coords('farm-ring',x-r,y-r,x+r,y+r)
        dx,dy=guidance.direction;px,py=-dy,dx
        points=[]
        for forward,side in ((.83,0),(-.48,.39),(-.22,0),(-.48,-.39)):
            points.extend((x+r*(forward*dx+side*px),y+r*(forward*dy+side*py)))
        if guidance.arrived:points=[x,y-r*.22,x+r*.22,y,x,y+r*.22,x-r*.22,y]
        c.coords('farm-arrow',*points)
        c.itemconfigure('farm-arrow',fill='#8fe3bd' if guidance.nearby else '#eee9df')
        nx,ny=guidance.north;c.coords('farm-north',x+nx*(r+8*scale),y+ny*(r+8*scale))
        c.coords('farm-caption',x,y+r+21*scale)
        c.itemconfigure('farm-caption',text=CHEST_NAMES.get(guidance.category,'Baú')+'\n'+guidance.proximity,font=('Segoe UI',max(8,round(9*scale))))
        c.itemconfigure('farm-north',font=('Segoe UI',max(8,round(8*scale)),'bold'))
        c.tag_raise(self.TAG)


class TargetHighlight:
    """A retained visual ring; input still uses the original pin geometry."""
    TAG='farm-target'
    def __init__(self,canvas):self.canvas=canvas

    def render(self,guidance,pins,observation,dpi=1.,controls=()):
        c=self.canvas;c.itemconfigure(self.TAG,state='hidden')
        if guidance is None or observation.surface!='minimap' or not observation.circle:return
        pin=next((p for p in pins if p.item.id==guidance.target_id),None)
        if pin is None:return
        a,b,d,e=pin.geometry.bounds(pin.x,pin.y);pad=2*max(.75,min(dpi,2.5))
        box=(a-pad,b-pad,d+pad,e+pad)
        cx,cy,r=observation.circle
        if any(math.hypot(x-cx,y-cy)>r for x in (box[0],box[2]) for y in (box[1],box[3])):return
        if any(box[0]<v[2] and box[2]>v[0] and box[1]<v[3] and box[3]>v[1] for v in controls):return
        if not c.find_withtag(self.TAG):c.create_oval(0,0,1,1,outline='#ffe299',width=2,tags=(self.TAG,))
        c.coords(self.TAG,*box);c.itemconfigure(self.TAG,state='normal',width=max(2,round(2*dpi)))
        c.tag_raise(self.TAG)
