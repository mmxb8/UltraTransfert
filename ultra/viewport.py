"""Contenu principal défilant, y compris sur une session distante peu haute."""
import tkinter as tk
from tkinter import ttk


def initial_size(width, height):
    # Marge pour les décorations/barres système ; largeur minimale du formulaire.
    return f'{min(820,max(720,width-80))}x{min(740,max(400,height-100))}'


class ScrollPanel:
    def __init__(self, root):
        shell=ttk.Frame(root)
        shell.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(shell,highlightthickness=0,takefocus=0)
        scrollbar=ttk.Scrollbar(shell,orient='vertical',command=self.canvas.yview)
        scrollbar.pack(side='right',fill='y')
        self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.panel=ttk.Frame(self.canvas,padding=24)
        self.item=self.canvas.create_window((0,0),window=self.panel,anchor='nw')
        self.panel.bind('<Configure>',self.region)
        self.canvas.bind('<Configure>',self.width)
        # Bindings du seul toplevel principal : pas de bind_all, ni de dialogue capturé.
        root.bind('<MouseWheel>',self.wheel,add='+')
        root.bind('<Button-4>',self.wheel,add='+')
        root.bind('<Button-5>',self.wheel,add='+')
        root.bind('<FocusIn>',self.focus,add='+')

    def contains(self, widget):
        while widget is not None:
            if widget is self.panel or widget is self.canvas:return True
            widget=getattr(widget,'master',None)
        return False

    def region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def width(self, event):
        self.canvas.itemconfigure(self.item,width=event.width)

    def wheel(self, event):
        if not self.contains(event.widget):return
        # Ces widgets gèrent déjà leur molette (sélection, texte défilant).
        if event.widget.winfo_class() in ('TCombobox','Text','Listbox','Spinbox','TSpinbox'):return
        number=getattr(event,'num',None)
        delta=getattr(event,'delta',0)
        if number in (4,5):
            units=-1 if number==4 else 1
        elif delta:
            units=(-1 if delta>0 else 1)*max(1,int(abs(delta)/120))
        else:
            units=0
        if units:
            self.canvas.yview_scroll(units,'units')
            return 'break'

    def focus(self, event):
        widget=event.widget
        if not self.contains(widget) or widget is self.canvas:return
        top=widget.winfo_rooty()-self.panel.winfo_rooty()
        bottom=top+widget.winfo_height()
        offset=self.canvas.winfo_rooty()-self.panel.winfo_rooty()
        viewport=self.canvas.winfo_height()
        total=self.panel.winfo_height()
        if total<=viewport or total<=0:return
        if top<offset:
            self.canvas.yview_moveto(max(0,(top-6)/total))
        elif bottom>offset+viewport:
            self.canvas.yview_moveto(max(0,(bottom-viewport+6)/total))
