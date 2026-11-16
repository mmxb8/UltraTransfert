"""Géométrie et événements doublés ; aucun rendu Tk réel revendiqué."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from ultra.viewport import ScrollPanel,initial_size
from ultra.gui import App


class ViewportTests(unittest.TestCase):
    def view(self):
        view=ScrollPanel.__new__(ScrollPanel)
        view.panel=Mock(master=None);view.panel.winfo_rooty.return_value=0;view.panel.winfo_height.return_value=1000
        view.canvas=Mock(master=None);view.canvas.winfo_rooty.return_value=100;view.canvas.winfo_height.return_value=400
        view.item=3
        return view

    def widget(self, view, top=200, height=30, cls='TButton'):
        widget=Mock(master=view.panel)
        widget.winfo_class.return_value=cls;widget.winfo_rooty.return_value=top;widget.winfo_height.return_value=height
        return widget

    def test_initial_size_preserves_large_screen_and_reduces_height(self):
        self.assertEqual(initial_size(1920,1080),'820x740')
        self.assertEqual(initial_size(800,600),'720x500')
        self.assertEqual(initial_size(1024,768),'820x668')
        self.assertEqual(initial_size(640,350),'720x400')  # Limites explicites, pas de promesse sur écran trop petit.

    def test_constructor_uses_local_bindings_and_visible_scrollbar(self):
        root=Mock();shell=Mock();panel=Mock();canvas=Mock();bar=Mock()
        with patch('ultra.viewport.ttk.Frame',side_effect=[shell,panel]),patch('ultra.viewport.tk.Canvas',return_value=canvas),patch('ultra.viewport.ttk.Scrollbar',return_value=bar):
            view=ScrollPanel(root)
        self.assertIs(view.panel,panel)
        bar.pack.assert_called_once_with(side='right',fill='y')
        self.assertEqual(root.bind.call_count,4);root.bind_all.assert_not_called()

    def test_region_and_width_follow_content_and_viewport(self):
        view=self.view();view.canvas.bbox.return_value=(0,0,720,1200)
        view.region();view.canvas.configure.assert_called_with(scrollregion=(0,0,720,1200))
        view.width(SimpleNamespace(width=740));view.canvas.itemconfigure.assert_called_with(3,width=740)

    def test_wheel_directions_and_small_deltas(self):
        view=self.view();widget=self.widget(view)
        for number,delta,expected in ((4,0,-1),(5,0,1),(None,120,-1),(None,-240,2),(None,1,-1),(None,-1,1)):
            self.assertEqual(view.wheel(SimpleNamespace(widget=widget,num=number,delta=delta)),'break')
            view.canvas.yview_scroll.assert_called_with(expected,'units')

    def test_wheel_does_not_capture_other_dialog_or_interactive_selection(self):
        view=self.view()
        widgets=[Mock(master=None)]+[self.widget(view,cls=c) for c in ('TCombobox','Text','Listbox','Spinbox','TSpinbox')]
        for widget in widgets:
            self.assertIsNone(view.wheel(SimpleNamespace(widget=widget,delta=120)))
        view.canvas.yview_scroll.assert_not_called()

    def test_zero_wheel_has_no_effect(self):
        view=self.view();view.wheel(SimpleNamespace(widget=self.widget(view),delta=0))
        view.canvas.yview_scroll.assert_not_called()

    def test_keyboard_focus_reveals_hidden_controls(self):
        view=self.view()
        view.focus(SimpleNamespace(widget=self.widget(view,top=50)))
        view.canvas.yview_moveto.assert_called_with(.044)
        view.focus(SimpleNamespace(widget=self.widget(view,top=800)))
        view.canvas.yview_moveto.assert_called_with(.436)

    def test_visible_focus_or_small_content_does_not_jump(self):
        view=self.view();view.focus(SimpleNamespace(widget=self.widget(view,top=200)))
        view.panel.winfo_height.return_value=300
        view.focus(SimpleNamespace(widget=self.widget(view,top=800)))
        view.focus(SimpleNamespace(widget=Mock(master=None)))
        view.canvas.yview_moveto.assert_not_called()

    def test_app_uses_scroll_panel_and_smaller_minimum_height(self):
        root=Mock();root.winfo_screenwidth.return_value=800;root.winfo_screenheight.return_value=600
        viewport=Mock()
        with ExitStack() as stack:
            stack.enter_context(patch('ultra.gui.ScrollPanel',return_value=viewport))
            stack.enter_context(patch('ultra.gui.installation_notice',return_value=None))
            for n in ('StringVar','BooleanVar'):stack.enter_context(patch('ultra.gui.tk.'+n))
            for n in ('Frame','Label','Button','Notebook','Entry','Checkbutton','Combobox','Progressbar'):
                stack.enter_context(patch('ultra.gui.ttk.'+n))
            app=App(root)
        root.geometry.assert_called_once_with('720x500');root.minsize.assert_called_once_with(720,400)
        self.assertIs(app.viewport,viewport)
