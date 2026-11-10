"""Render a safe UI-only preview of the real collapse transition and badge handoff."""
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
from src.live.brand import badge_frames,animation_frame
from src.live.panel_transition import DURATION_MS,HANDOFF_MS,handoff_frame,transition_frame

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/panel-transition'


def sample_panel():
    """Illustrative UI in the real theme, using fictional data; no screen reads."""
    from src.live.theme import BG,SURFACE,TEXT,MUTED,ACCENT,BORDER
    image=Image.new('RGBA',(360,540),BG);draw=ImageDraw.Draw(image)
    regular=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13)
    small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',11)
    bold=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',19)
    draw.polygon([(29,17),(34,29),(43,33),(34,37),(29,49),(24,37),(15,33),(24,29)],fill=ACCENT)
    draw.text((51,16),'Hexen Map',font=bold,fill=TEXT)
    draw.text((51,43),'Seu companheiro de exploração',font=small,fill=MUTED)
    draw.rounded_rectangle((310,18,345,49),radius=7,fill=SURFACE)
    draw.text((322,22),'—',font=regular,fill=TEXT)
    draw.rounded_rectangle((16,78,344,116),radius=7,fill=SURFACE)
    draw.rounded_rectangle((19,81,177,113),radius=6,fill='#332E46')
    draw.text((76,88),'Itens',font=regular,fill=TEXT);draw.text((235,88),'Ajustes',font=regular,fill=MUTED)
    draw.rounded_rectangle((16,133,344,171),radius=8,fill=SURFACE)
    draw.text((30,144),'O que você quer encontrar?',font=regular,fill=MUTED)
    draw.text((18,190),'Seleção',font=small,fill=MUTED)
    draw.text((242,190),'Limpar seleção',font=small,fill=MUTED)
    draw.text((22,222),'Baús',font=regular,fill=TEXT)
    for y,label,checked in [(252,'Baús comuns',True),(291,'Baús sofisticados',False),(330,'Baús luxuosos',True)]:
        draw.rounded_rectangle((17,y-6,343,y+26),radius=6,fill=SURFACE)
        draw.rectangle((29,y+1,43,y+15),outline=ACCENT,fill=ACCENT if checked else BG)
        if checked:draw.line([(32,y+8),(36,y+12),(41,y+4)],fill=BG,width=2)
        draw.text((55,y-1),label,font=regular,fill=TEXT)
    draw.text((22,380),'Oculi',font=regular,fill=TEXT)
    draw.rounded_rectangle((17,408,343,440),radius=6,fill=SURFACE)
    draw.rectangle((29,418,43,432),outline=ACCENT)
    draw.text((55,416),'Anemoculus',font=regular,fill=TEXT)
    draw.line((16,459,344,459),fill=BORDER)
    draw.text((18,470),'Coletados: 12 de 60',font=small,fill=MUTED)
    draw.text((18,509),'Ocultar ícones',font=regular,fill=MUTED)
    draw.rounded_rectangle((266,497,344,530),radius=8,fill=ACCENT)
    draw.text((287,505),'Jogar',font=regular,fill=BG)
    return image


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    snapshot=sample_panel()
    snapshot.save(OUT/'panel-preview.png')
    w,h=snapshot.size;compact=76;origin=(12,12);target=(50,50);size=(w+24,h+24)
    poster=handoff_frame();badges,durations=badge_frames(compact)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    frames=[]
    def append(layer,label):
        layer.putalpha(layer.getchannel('A').point(lambda alpha:255 if alpha>=128 else 0))
        canvas=Image.new('RGBA',(size[0],size[1]+50),'#100b19')
        canvas.alpha_composite(layer,(0,44))
        ImageDraw.Draw(canvas).text((size[0]/2,12),label+' · ilustração',font=font,fill='#e6dafb',anchor='mt')
        frames.append(canvas.convert('RGB'))
    for _ in range(10):
        layer=Image.new('RGBA',size);layer.alpha_composite(snapshot,origin);append(layer,'Painel aberto')
    steps=21
    for i in range(steps):
        p=i/(steps-1)
        layer=transition_frame(snapshot,poster,p,size,origin,target,compact)
        append(layer,'Corte e fechamento' if p<.6 else 'Recolhendo para a miniatura')
    for i in range(36):
        index,_=animation_frame(durations,HANDOFF_MS+i*1000/24)
        layer=Image.new('RGBA',size);layer.alpha_composite(badges[index],(12,12))
        append(layer,'Miniatura do overlay')
    timing=[round((i+1)*1000/24)-round(i*1000/24) for i in range(len(frames))]
    frames[0].save(OUT/'panel-collapse.webp',save_all=True,append_images=frames[1:],duration=timing,loop=0,lossless=True)
    selected=[(0,'Aberto'),(18,'Corte'),(25,'Fenda'),(34,'Miniatura')]
    strip=Image.new('RGB',(size[0]*4,size[1]+50),'#100b19')
    for col,(index,label) in enumerate(selected):strip.paste(frames[index],(col*size[0],0))
    strip.save(OUT/'panel-collapse-sequence.png')
    print(OUT/'panel-collapse.webp')


if __name__=='__main__':main()
