"""Opt-in selected-item guidance in minimap coordinates; no camera or game input control."""
from dataclasses import dataclass
import math
import logging
import numpy as np
from src.live.catalog import CATEGORIES
from src.live.labels import portuguese_label
from src.live.respawn import parse_utc

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
    label: str = 'Item'


class ChestFarm:
    def __init__(self):
        self.enabled=False
        self.target_id=None
        self.origin=None
        self.context=None
        self.surface_context=None
        self.skipped=set()
        self.status=''
        self.candidate_key=None;self.candidates=[];self.points=np.empty((0,2));self.availability_key=None;self.next_ready=None
        self.arrival_target=None
        self.arrived=False
        self.availability_key=None;self.next_ready=None

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
        self.candidate_key=None;self.candidates=[];self.points=np.empty((0,2));self.availability_key=None;self.next_ready=None
        self.arrival_target=None;self.arrived=False
        self.status='Volte ao jogo para iniciar a bússola.'

    def stop(self):
        self.enabled=False;self.target_id=None;self.status=''
        self.candidates=[];self.points=np.empty((0,2));self.candidate_key=None;self.availability_key=None;self.next_ready=None
        self.arrival_target=None;self.arrived=False

    def skip(self):
        if self.target_id:self.skipped.add(self.target_id)
        self.target_id=None

    def update(self,session,observation,now):
        if not self.enabled:return None
        if self.context!=self.scope(session):
            self.stop();self.status='Busca encerrada: mapa ou seleção territorial alterados.';return None
        obs=observation
        if (session.hidden or obs.surface!='minimap' or not obs.fresh(now) or obs.player is None
                or not np.isfinite(obs.player).all() or obs.circle is None):
            self.status='Bússola aguardando localização no minimapa.';return None
        if ((session.map_id and obs.map_id!=session.map_id) or not obs.map_id or not obs.layer_id
                or (session.layer_id and obs.layer_id!=session.layer_id)):
            self.status='Bússola aguardando o mapa e a camada selecionados.';return None
        surface=(obs.map_id,obs.layer_id)
        if self.surface_context is not None and surface!=self.surface_context:
            self.stop();self.status='Busca encerrada: mapa ou camada alterados.';return None
        self.surface_context=surface
        if self.origin is None:self.origin=tuple(obs.player)
        selected=set(session.selected)
        if not selected:
            self.target_id=None;self.status='Selecione ao menos um item nos filtros.';return None
        key=(frozenset(selected),surface)
        if key!=self.candidate_key:
            self.candidates=sorted((i for i in session.scoped_items()
                    if set(i.category_ids or (i.category,)) & selected
                    and i.map_id==obs.map_id and obs.layer_id in (i.layer_ids or (i.layer_id,))),key=lambda i:i.id)
            self.points=np.array([(i.x,i.y) for i in self.candidates],dtype=float).reshape(-1,2)
            self.candidate_key=key
        # Re-evaluate from the current position; category/coordinate preparation is cached.
        delta=self.points-np.asarray(obs.player)
        distances=np.einsum('ij,ij->i',delta,delta)
        availability=(key,id(session.progress),session.progress.collected_count,session.collection_epoch,len(self.skipped))
        clock=session.clock()
        if availability!=self.availability_key or self.next_ready is not None and clock>=self.next_ready:
            lookup={item.id:n for n,item in enumerate(self.candidates)}
            self.available=np.ones(len(self.candidates),dtype=bool);self.next_ready=None
            for identifier in session.progress.get_collected_ids():
                n=lookup.get(identifier)
                if n is None:continue
                if session.is_collected(identifier):
                    self.available[n]=False
                    rule=session.rules.get(self.candidates[n].rule_id)
                    if rule and rule.kind in {'elapsed','server_reset'}:
                        deadline=parse_utc(session.progress.get_collection_record(identifier).get('ready_at'))
                        if deadline and clock<deadline:self.next_ready=min(self.next_ready,deadline) if self.next_ready else deadline
            for identifier in self.skipped:
                if identifier in lookup:self.available[lookup[identifier]]=False
            self.availability_key=availability
        distances[~self.available]=np.inf
        nearest=int(np.argmin(distances)) if len(distances) else None
        target=self.candidates[nearest] if nearest is not None and np.isfinite(distances[nearest]) else None
        self.target_id=target.id if target else None
        if target is None:
            self.status='Nenhum item disponível nos filtros. Reinicie para rever os pulados.';return None
        if obs.heading_screen is None or not math.isfinite(obs.heading_screen) or obs.heading_confidence<.7:
            self.status='Bússola aguardando a direção do V no minimapa.';return None
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
        self.status='No local do item · confirme a coleta.' if self.arrived else 'Item próximo · confirme a coleta.' if distance<=22 else 'Siga a bússola · confirme cada coleta.'
        category=next((c for c in (target.category,*target.category_ids) if c in selected),target.category)
        proximity='Próximo' if distance<=22 else 'Na vizinhança' if distance<=obs.circle[2] else 'Mais distante'
        name=CATEGORIES.get(category,(target.name,''))[0]
        label=CHEST_NAMES.get(category) or portuguese_label(name) or name
        return Guidance(target.id,category,direction,north,distance<=22,'No local' if self.arrived else proximity,self.arrived,label)


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
            c.create_text(0,0,text='Item',fill='#eee9df',tags=(self.TAG,'farm-caption'))
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
        c.itemconfigure('farm-caption',text=guidance.label+'\n'+guidance.proximity,font=('Segoe UI',max(8,round(9*scale))))
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
