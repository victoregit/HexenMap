"""Source IDs and coordinates remain untouched; index only the Teyvat surface."""
from collections import defaultdict
import numpy as np


class WorldIndex:
    def __init__(self,items,map_id='as-map-2',layer='surface'):
        self.items=[i for i in items if i.map_id==map_id and layer in (i.layer_ids or (i.layer_id,))]
        self.xy=np.asarray([(i.x,i.y) for i in self.items],dtype=np.float64).reshape(-1,2)
        self.by_id={item.id:index for index,item in enumerate(self.items)}
        members=defaultdict(list)
        for index,item in enumerate(self.items):
            for category in item.category_ids or (item.category,):members[category].append(index)
        self.members={key:np.asarray(value,np.int32) for key,value in members.items()}
        self.selection=None;self.selected=np.zeros(len(self.items),bool)
    def query(self,bounds,selection,collected=()):
        selection=frozenset(selection)
        if selection!=self.selection:
            self.selection=selection;self.selected[:]=False
            for category in selection:
                if category in self.members:self.selected[self.members[category]]=True
        left,top,right,bottom=bounds
        visible=(self.selected & (self.xy[:,0]>=left)&(self.xy[:,0]<=right)&(self.xy[:,1]>=top)&(self.xy[:,1]<=bottom))
        for identifier in collected:
            if identifier in self.by_id:visible[self.by_id[identifier]]=False
        return np.flatnonzero(visible)
