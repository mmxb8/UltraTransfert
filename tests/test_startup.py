import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import launch_gui
from ultra.startup import diagnostic, launch_safely, report_failure


class StartupTests(unittest.TestCase):
    def test_diagnostic_unique_unicode_bounded_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'été 日本語'
            a=diagnostic(RuntimeError('échec '+ 'a'*100000),directory)
            b=diagnostic(RuntimeError('autre erreur'),directory)
            self.assertNotEqual(a,b)
            self.assertLess(a.stat().st_size,66000)
            self.assertIn('RuntimeError: autre erreur',b.read_text())
            if os.name!='nt':self.assertEqual(a.stat().st_mode & 0o777,0o600)

    def test_disk_failure_leaves_no_partial_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_fdopen=os.fdopen
            @contextlib.contextmanager
            def full_disk(fd,*args,**kwargs):
                stream=real_fdopen(fd,*args,**kwargs)
                class Full:
                    def write(self,data):raise OSError('espace insuffisant simulé')
                try:yield Full()
                finally:stream.close()
            with patch('ultra.startup.os.fdopen',side_effect=full_disk):
                self.assertIsNone(diagnostic(ValueError('test'),tmp))
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_unwritable_directory_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'file';p.touch()
            self.assertIsNone(diagnostic(RuntimeError('test'),p))

    def test_launch_success_and_failure_exit_codes(self):
        with patch('ultra.startup.report_failure') as report:
            self.assertEqual(launch_safely(lambda:None),0)
            report.assert_not_called()
            def fail():raise ImportError('Tcl manquant')
            self.assertEqual(launch_safely(fail),1)
            self.assertIsInstance(report.call_args.args[0],ImportError)

    def test_windows_native_message_does_not_require_tk(self):
        with patch('ultra.startup.sys.platform','win32'),patch('ultra.startup.diagnostic',return_value=Path('diagnostic.log')),patch('ultra.startup.native_message') as native:
            report_failure(ImportError('tkinter absent'))
        self.assertIn('diagnostic.log',native.call_args.args[0])
        self.assertIn('_internal',native.call_args.args[0])

    def test_no_log_and_no_display_still_explains_action(self):
        with patch('ultra.startup.sys.platform','linux'),patch('ultra.startup.diagnostic',return_value=None),patch('tkinter.Tk',side_effect=RuntimeError('sans écran')),contextlib.redirect_stderr(io.StringIO()) as err:
            report_failure(ImportError('absent'))
        self.assertIn('espace libre',err.getvalue())

    def test_entry_preserves_build_smoke_route(self):
        with patch.object(sys,'argv',['launch_gui.py','--smoke-test','rapport.json']),patch('ultra.smoke.write_report',return_value=1) as smoke,patch('ultra.startup.launch_safely') as launch:
            self.assertEqual(launch_gui.main(),1)
        smoke.assert_called_once_with('rapport.json');launch.assert_not_called()

    @unittest.skipIf(sys.platform=='win32','Absence de DISPLAY Linux seulement')
    def test_actual_headless_start_failure_has_log_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,DISPLAY='',XDG_STATE_HOME=tmp)
            proc=subprocess.run([sys.executable,'launch_gui.py'],env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(proc.returncode,1)
            self.assertIn('ne peut pas ouvrir son interface',proc.stderr)
            logs=list(Path(tmp).rglob('demarrage-*.log'))
            self.assertEqual(len(logs),1)
            self.assertIn('TclError',logs[0].read_text())
