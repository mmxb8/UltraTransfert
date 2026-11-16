"""Mesure de géométrie simulée, sans serveur graphique ni mesure RDP."""
import json
from pathlib import Path
from types import SimpleNamespace

from ultra.viewport import initial_size,ScrollPanel


def main():
    rows=[]
    for width,height in ((800,600),(1024,768),(1920,1080)):
        size=initial_size(width,height);new_width,new_height=map(int,size.split('x'))
        # Formulaire synthétique haut de 1200 px, commande de 30 px à y=1100.
        # Ce ne sont pas les positions de widgets Tk mesurées à l'écran.
        state={'offset':0.0}
        panel=SimpleNamespace(master=None,winfo_rooty=lambda:-state['offset'],winfo_height=lambda:1200)
        canvas=SimpleNamespace(master=None,winfo_rooty=lambda:0,winfo_height=lambda:new_height,
                               yview_moveto=lambda fraction:state.update(offset=fraction*1200))
        button=SimpleNamespace(master=panel,winfo_rooty=lambda:1100-state['offset'],winfo_height=lambda:30)
        view=ScrollPanel.__new__(ScrollPanel);view.panel=panel;view.canvas=canvas
        view.focus(SimpleNamespace(widget=button))
        visible=0<=button.winfo_rooty() and button.winfo_rooty()+30<=new_height
        assert visible
        rows.append(dict(screen_width=width,screen_height=height,old_requested_size='820x740',
                         old_minimum_height=700,new_requested_size=size,new_minimum_height=400,
                         synthetic_button_y=1100,synthetic_content_height=1200,
                         simulated_scroll_offset=state['offset'],button_visible_after_focus=visible))
    report=dict(scope='Pure geometry simulation using the actual focus handler and supplied synthetic widget positions. No Tk layout, screenshot, DPI, window manager, Windows, RDP responsiveness or transfer throughput measured. Initial margins 80 horizontal/100 vertical; width below 720 or height below 400 not supported.',rows=rows)
    Path('reports/viewport-0.3.18.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
