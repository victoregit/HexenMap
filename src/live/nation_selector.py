"""Nation picker with cached, locally bundled emblems; no network on UI interaction."""
import hashlib
import json
import tkinter as tk

from PIL import Image, ImageTk

from src.live.storage import bundle_dir

COLORS={'mondstadt':'#52bea2','liyue':'#d9ae48','inazuma':'#bd8dde',
        'sumeru':'#a1bf4f','fontaine':'#58b9e2','natlan':'#eb846d',
        'snezhnaya':'#94d9dd','nod_krai':'#c4bafa'}


def icon_image(region, size=24):
    region='mondstadt' if region=='legacy-mondstadt' else region
    directory=bundle_dir()/'data/assets/nations'
    metadata=json.loads((directory/'SOURCE.json').read_text(encoding='utf-8'))[region]
    path=directory/metadata['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256']:
        raise ValueError('Emblema de nação alterado: '+region)
    with Image.open(path) as source:
        alpha=source.convert('RGBA').getchannel('A')
        bounds=alpha.getbbox()
        if not bounds:raise ValueError('Emblema vazio: '+region)
        alpha=alpha.crop(bounds)
        alpha.thumbnail((size,size),Image.Resampling.LANCZOS)
        # Tint only at presentation time. Original downloaded files stay byte-identical.
        image=Image.new('RGBA',(size,size),(0,0,0,0))
        emblem=Image.new('RGBA',alpha.size,COLORS[region]);emblem.putalpha(alpha)
        image.alpha_composite(emblem,((size-alpha.width)//2,(size-alpha.height)//2))
        return image


class NationSelector(tk.Frame):
    """All nations visible in one row; click selects and exposes the name below."""
    def __init__(self, parent, variable, options, changed, on_select):
        super().__init__(parent,bg='#141e2d')
        self.variable=variable;self.options=options;self.changed=changed;self.on_select=on_select
        self.names=list(options)
        self.images={region:ImageTk.PhotoImage(icon_image(region,22),master=self)
                     for region in set(options.values())}
        self.index=self.names.index(variable.get()) if variable.get() in self.names else 0
        self.hovered=None
        self.button=tk.Canvas(self,width=1,height=32,bg='#141e2d',highlightthickness=0,cursor='hand2',takefocus=1)
        self.button.pack(fill='x',expand=True)
        self.caption=tk.Label(self,bg='#141e2d',fg='#a0adbd',font=('Segoe UI',8),anchor='w')
        self.caption.pack(fill='x',padx=4)
        self.button.bind('<Configure>',lambda e:self.draw())
        self.button.bind('<Button-1>',self.click)
        self.button.bind('<Motion>',self.hover)
        self.button.bind('<Leave>',lambda e:self.leave())
        self.button.bind('<FocusIn>',lambda e:self.draw())
        self.button.bind('<FocusOut>',lambda e:self.draw())
        self.button.bind('<Right>',lambda e:self.move(1))
        self.button.bind('<Left>',lambda e:self.move(-1))
        self.button.bind('<Return>',lambda e:self.choose(self.index))
        self.button.bind('<space>',lambda e:self.choose(self.index))
        self.trace=variable.trace_add('write',self.selection_changed)
        self.draw()

    def selection_changed(self,*args):
        if self.variable.get() in self.names:self.index=self.names.index(self.variable.get())
        self.draw()

    def draw(self):
        c=self.button;c.delete('all');width=max(1,c.winfo_width());cell=width/len(self.names)
        for index,name in enumerate(self.names):
            x=index*cell;selected=name==self.variable.get()
            if selected or index==self.hovered:
                c.create_rectangle(x+1,1,x+cell-1,30,fill='#293c51' if selected else '#1c2a3b',outline='')
            c.create_image(x+cell/2,15,image=self.images[self.options[name]])
            if selected:c.create_line(x+5,31,x+cell-5,31,fill=COLORS.get(self.options[name],'#cbb88a'),width=2)
            if index==self.index and c.focus_get()==c:
                c.create_rectangle(x+1,1,x+cell-1,30,outline='#cbb88a')
        name=self.names[self.hovered] if self.hovered is not None else self.variable.get()
        self.caption.configure(text=name)

    def click(self,event):
        self.button.focus_set()
        self.choose(min(len(self.names)-1,int(event.x*len(self.names)/max(1,self.button.winfo_width()))))

    def hover(self,event):
        index=min(len(self.names)-1,max(0,int(event.x*len(self.names)/max(1,self.button.winfo_width()))))
        if index!=self.hovered:self.hovered=index;self.draw()

    def leave(self):self.hovered=None;self.draw()

    def move(self,delta):
        self.index=(self.index+delta)%len(self.names);self.hovered=None;self.draw()
        self.caption.configure(text=self.names[self.index]);return 'break'

    def choose(self,index):
        if not 0<=index<len(self.names):return 'break'
        self.index=index;self.hovered=None;name=self.names[index]
        self.on_select()
        if self.variable.get()!=name:
            self.variable.set(name);self.changed()
        self.draw();return 'break'

    def destroy(self):
        self.variable.trace_remove('write',self.trace)
        super().destroy()
