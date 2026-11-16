import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from ultra.engine import Result,Transfer,digest,STATE
from ultra.gui import App
from ultra.report_view import capture_result,render_report
import test_ui_workflow as workflow


class ReportViewTests(unittest.TestCase):
    def result(self):
        return Result(files=2,directories=1,bytes=1230000,copied=1,reused=1,resumed_bytes=65536,
                      seconds=1.25,hashes={'été':'a'*64,'vide':'b'*64},max_bytes_per_second=5e6)

    def view(self,app):
        window,text=Mock(),Mock()
        with patch('ultra.gui.tk.Toplevel',return_value=window),patch('ultra.gui.tk.Text',return_value=text),patch('ultra.gui.ttk.Frame'),patch('ultra.gui.ttk.Scrollbar'),patch.object(Path,'open',side_effect=AssertionError('Lecture disque interdite')):
            app.show_report()
        return window,text

    def test_success_summary_unicode_counts_and_scope(self):
        title,body=render_report(capture_result(self.result()),'done','destination été 日本語')
        self.assertEqual(title,'Copie terminée et vérifiée')
        for text in ('Fichiers inventoriés : 2','65 536 octets','5 Mo/s','ACL','aucune nouvelle vérification','日本語'):self.assertIn(text,body)

    def test_errors_and_stops_never_claim_completion(self):
        data=capture_result(self.result())
        for kind in ('error','stopped'):
            title,body=render_report(data,kind,'dest','Action actuelle')
            self.assertNotIn('terminée et vérifiée',title)
            self.assertIn('Action actuelle',body)
        self.assertIn('Reprendre',render_report(data,'stopped','dest')[1])

    def test_invalid_or_incomplete_summary_cannot_show_success(self):
        good=capture_result(self.result())
        for data in (None,{},dict(good,files=True),dict(good,seconds=float('nan')),dict(good,verified_files=0),dict(good,error_count=1)):
            title,body=render_report(data,'done',None)
            self.assertNotEqual(title,'Copie terminée et vérifiée')

    def test_snapshot_does_not_iterate_large_hash_table(self):
        class Hashes:
            def __len__(self):return 1000000
            def __iter__(self):raise AssertionError('Table copiée')
        result=self.result();result.hashes=Hashes();result.files=1000000;result.copied=999999
        data=capture_result(result)
        self.assertNotIn('hashes',data);self.assertLess(len(json.dumps(data)),1000)
        self.assertEqual(data['verified_files'],1000000)

    def test_long_error_display_is_bounded(self):
        title,body=render_report(None,'error','dest','x'*100000+' Action finale : reprendre')
        self.assertLess(len(body),6000);self.assertIn('ancien fichier',body);self.assertIn('Action finale : reprendre',body)

    def test_report_uses_captured_destination_without_reading_network_path(self):
        app=workflow.WorkflowTests().make_app('source','autre destination')
        app.last_destination='\\\\tsclient\\D\\données'
        app.report_data=capture_result(self.result());app.report_kind='done';app.report_message=''
        window,text=self.view(app)
        body=text.insert.call_args.args[1]
        self.assertIn(app.last_destination,body);self.assertNotIn('autre destination',body)
        text.configure.assert_called_with(state='disabled')

    def test_no_report_window_while_running_or_before_result(self):
        app=workflow.WorkflowTests().make_app('source','dest')
        with patch('ultra.gui.tk.Toplevel') as window:
            app.show_report()
            app.report_kind='done';app.running=True;app.show_report()
        window.assert_not_called()

    def test_old_success_file_not_used_after_prepare_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source';src.mkdir();(src/'f').write_bytes(b'abc');dst=Path(tmp)/'dest'
            app=workflow.WorkflowTests().make_app(src,dst)
            app.start();terminal,error=workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0],'done');self.assertIsNotNone(app.report_data)
            (src/'ajout').write_bytes(b'new')
            app.start();terminal,error=workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0],'error');self.assertIsNone(app.report_data)
            self.assertFalse(json.loads((dst/STATE/'last-result.json').read_text())['errors'])
            window,text=self.view(app)
            window.title.assert_called_with('Copie non confirmée')
            self.assertIn('Aucun bilan complet',text.insert.call_args.args[1])
            self.assertEqual((dst/'f').read_bytes(),b'abc')

    def test_interrupted_then_resumed_gui_summaries_match_real_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source';src.mkdir();(src/'f').write_bytes(b'abcd'*(1024*1024));dst=Path(tmp)/'dest'
            app=workflow.WorkflowTests().make_app(src,dst);real=Transfer.tick
            def tick(transfer,n):
                real(transfer,n)
                if transfer.completed_bytes>=1024*1024:app.request_stop()
            with patch.object(Transfer,'tick',tick):
                app.start();terminal,error=workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0],'stopped');self.assertEqual(app.report_kind,'stopped')
            self.assertEqual(render_report(app.report_data,app.report_kind,str(dst))[0],'Copie interrompue')
            app.start();terminal,error=workflow.WorkflowTests().finish(app)
            self.assertEqual(terminal[0],'done');self.assertGreater(app.report_data['resumed_bytes'],0)
            self.assertEqual(render_report(app.report_data,app.report_kind,str(dst))[0],'Copie terminée et vérifiée')
            self.assertEqual(digest(src/'f'),digest(dst/'f'))
