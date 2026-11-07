"""Render actual cached pin assets at native size and an enlarged visual detail."""
from pathlib import Path
import sys

from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.live.marker_art import chest_art,pin_image,marker_geometry


def main():
    names=[('common-chest','Comum'),('exquisite-chest','Sofisticado'),('precious-chest','Precioso'),
           ('luxurious-chest','Luxuoso'),('remarkable-chest','Extraordinário')]
    output=ROOT/'build/chest-pins-preview.png'
    image=Image.new('RGB',(1000,540),'#142231');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
    title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',21)
    draw.text((24,15),'Baús · arte do mapa oficial HoYoLAB',font=title,fill='#eee7ce')
    draw.text((24,47),'Tamanho real à esquerda de cada detalhe ampliado (3×). A ponta é a posição do item.',font=font,fill='#b4c4cf')
    for row,(label,w,h,collected) in enumerate([('Minimapa',24,32,False),('Mapa M',28,36,False),('Revelado com Ctrl · coletado',28,36,True)]):
        y=85+row*150
        draw.rectangle((0,y,999,y+148),fill='#d2d1bd' if row==1 else '#24394a')
        color='#263e4a' if row==1 else '#e7e3d2'
        draw.text((20,y+8),label,font=font,fill=color)
        for col,(category,name) in enumerate(names):
            if chest_art(category) is None:raise ValueError(f'Missing reviewed artwork: {category}')
            pin=pin_image(category,w,h,collected)
            x=25+col*195
            image.paste(pin,(x,y+70-h),pin)
            enlarged=pin.resize((w*3,h*3),Image.Resampling.NEAREST)
            image.paste(enlarged,(x+47,y+25),enlarged)
            draw.text((x,y+124),name,font=font,fill=color)
    image.save(output);print(output)


if __name__=='__main__':main()
