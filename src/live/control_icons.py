"""Scalable UI silhouettes based on Genshin's Elemental Sight symbol.

Reference: https://genshin-impact.fandom.com/wiki/Elemental_Sight
"""


def draw_elemental_sight(canvas,color,background,visible=True,scale=1):
    # Four pointed extensions surround the almond and its ring-shaped pupil.
    canvas.create_polygon(14,1,18,8,22,10,27,14,22,18,18,20,
                          14,27,10,20,6,18,1,14,6,10,10,8,
                          fill=color,outline='')
    canvas.create_polygon(5,14,9,10,14,8,19,10,23,14,19,18,14,20,9,18,
                          smooth=True,splinesteps=24,fill=background,outline='')
    canvas.create_oval(9.5,9.5,18.5,18.5,fill=color,outline='')
    canvas.create_oval(12,12,16,16,fill=background,outline='')
    if not visible:
        canvas.create_line(4,25,25,4,fill=background,width=4)
        canvas.create_line(4,25,25,4,fill=color,width=1.7)
    if scale!=1:canvas.scale('all',0,0,scale,scale)
