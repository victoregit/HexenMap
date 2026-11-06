"""Original vector chest symbols, shared by the game overlay and filter legend."""
from __future__ import annotations

from dataclasses import dataclass


# Includes the outer dark stroke and the feet at the largest live icon scale.
ICON_MARGIN=12


@dataclass(frozen=True)
class ChestStyle:
    wood: str
    lid: str
    side: str
    metal: str
    lock: str
    ornate: bool = False


CHEST_STYLES={
    "common-chest": ChestStyle("#805537","#ad8152","#503726","#b1b6ba","#d7d9d7"),
    "exquisite-chest": ChestStyle("#744339","#ad6650","#452e2c","#a8d5e5","#e1f5fc"),
    "precious-chest": ChestStyle("#486480","#7dacc2","#2b3e5a","#e9cd82","#fff1b7",True),
    "luxurious-chest": ChestStyle("#813e36","#bb7050","#4e2928","#ffcf61","#fff1ba",True),
    # Supported artwork only; no invented positions for unavailable categories.
    "remarkable-chest": ChestStyle("#346c5c","#68a78e","#20473e","#bddf9c","#e1f2bd",True),
}


def draw_marker(canvas, category: str, x: float, y: float, scale: float = 1.0,
                collected: bool = False):
    """Draw with Canvas primitives: crisp at runtime DPI, no external game assets.

    All coordinates fit within a 10 px half-extent before scaling. The same
    symbol is shown in the panel so color isn't the only clue to its meaning.
    """
    outline="#101e29"
    def tone(color):
        if not collected or not color:
            return color
        value=round(sum(int(color[i:i+2],16) for i in (1,3,5))/3*.7)
        return f"#{value:02x}{value:02x}{value:02x}"
    def coords(points):
        return [value for a,b in points for value in (x+a*scale,y+b*scale)]
    def polygon(points,fill,edge=outline,width=1):
        canvas.create_polygon(*coords(points),fill=tone(fill),outline=tone(edge),width=width*scale)
    def line(points,color,width=1):
        canvas.create_line(*coords(points),fill=tone(color),width=width*scale)
    def box(a,b,c,d,fill,edge=""):
        canvas.create_rectangle(x+a*scale,y+b*scale,x+c*scale,y+d*scale,
                                fill=tone(fill),outline=tone(edge),width=scale)
    from src.live.catalog import CATEGORY_GROUPS
    group=CATEGORY_GROUPS.get(category,"")
    if category=="anemoculus" or group=="Oculi":
        polygon([(0,-9),(3,-3),(8,0),(3,3),(0,9),(-3,3),(-8,0),(-3,-3)],"#6ee7c5")
        polygon([(0,-4),(3,0),(0,4),(-3,0)],"#d3fff1",edge="#268c82")
        line([(-5,-1),(-7,-5),(-3,-3)],"#b4f7e6")
        line([(5,1),(7,5),(3,3)],"#b4f7e6")
        return
    if category not in CHEST_STYLES and group!="Baús":
        if group=="Recursos":
            polygon([(-7,5),(-7,-2),(-1,-8),(6,-5),(5,2)],"#83cbb1")
            line([(-7,7),(3,-4)],"#c9efe1",1.5)
        elif group=="Seelies":
            polygon([(0,-9),(6,-2),(4,4),(0,7),(-5,3),(-5,-3)],"#8dd9ed")
            line([(-3,7),(-6,9)],"#c9f4fa",2)
        elif group=="Desafios":
            polygon([(-6,-8),(6,-8),(1,0),(6,8),(-6,8),(-1,0)],"#e9cd82")
        elif group=="Santuários":
            polygon([(-9,-3),(0,-9),(9,-3)],"#c4a8e5")
            box(-7,-2,7,7,"#64799d",outline)
            box(-2,0,2,7,"#203341")
        else:
            polygon([(0,-8),(8,0),(0,8),(-8,0)],"#a8b6d5")
            box(-2,-2,2,2,"#203341")
        return
    style=CHEST_STYLES.get(category,CHEST_STYLES["common-chest"])
    # Raised, rounded lid and visible side give a chest silhouette at small size.
    polygon([(-9,-2),(-8,-6),(-5,-8),(5,-8),(8,-5),(9,-2)],style.lid)
    polygon([(-9,-2),(6,-2),(6,6),(-9,6)],style.wood)
    polygon([(6,-2),(9,-4),(9,4),(6,6)],style.side)
    line([(-9,-2),(6,-2),(9,-4)],style.metal,1.5)
    # Metal bands follow the curved lid and continue down the body.
    for offset in (-6,4):
        line([(offset,5),(offset,-5),(offset+1,-7)],style.metal,1.5)
    line([(-8,5),(5,5)],style.metal)
    box(-2,-3,1,2,style.lock,outline)
    box(-1,-1,0,1,outline)
    box(-8,6,-5,7,style.side)
    box(3,6,6,7,style.side)
    if style.ornate:
        polygon([(-1,-8),(1,-10),(3,-8),(1,-6)],style.lock)
        line([(-4,1),(-3,3),(-4,4)],style.metal)
        line([(2,1),(3,3),(2,4)],style.metal)
