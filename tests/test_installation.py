"""Préparation réelle en venv sans pip/crypto ; scénarios réseau simulés explicitement."""
from contextlib import contextmanager
import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import threading
import unittest
from unittest.mock import patch

from prepare_installation import prepare, main
from ultra.installation_status import installation_notice


class InstallationTests(unittest.TestCase):
    @contextmanager
    def project(self):
        with tempfile.TemporaryDirectory(prefix='Installation été 日本語 ') as tmp:
            root=Path(tmp)
            source=Path(__file__).resolve().parents[1]
            shutil.copytree(source/'ultra',root/'ultra',ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(source/'requirements-sharing.txt',root/'requirements-sharing.txt')
            yield root

    def test_offline_real_venv_without_pip_core_copy_and_resume(self):
        with self.project() as root:
            with patch('prepare_installation.subprocess.run',wraps=subprocess.run) as commands:
                report=prepare(root,offline=True)
            self.assertTrue(report['core_ready'],report)
            self.assertFalse(report['sharing_ready'])
            self.assertEqual(report['status'],'core_ready_without_new_connections')
            self.assertGreater(report['core_probe']['resumed_bytes'],0)
            self.assertFalse(report['core_probe']['gui_created'])
            self.assertFalse(any('pip' in c.args[0] or 'ensurepip' in c.args[0] for c in commands.call_args_list))
            python=root/'.venv-run'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
            proc=subprocess.run([str(python),'-c','import importlib.util; assert importlib.util.find_spec("cryptography") is None; assert importlib.util.find_spec("pip") is None'],env=env,cwd=root,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('Copies et réception',installation_notice(root))
            again=prepare(root,offline=True)
            self.assertTrue(again['core_ready']);self.assertFalse((root/'.cycle.lock').exists())
            # Réception TLS réelle dans le même venv dépourvu de crypto/pip.
            from ultra.share_setup import prepare_share
            from ultra.network import make_server,read_token
            from ultra.engine import LocalSource,digest
            data=root/'donnees';data.mkdir();(data/'été.bin').write_bytes(b'exact'*20000)
            profile=prepare_share('https://localhost:8443',root/'private')
            cert=profile.directory/'server-cert.pem';key=profile.directory/'server-key.pem';token=profile.directory/'token.txt'
            server=make_server(LocalSource(data),('127.0.0.1',0),cert,key,read_token(token),'none')
            thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
            try:
                received=root/'received'
                proc=subprocess.run([str(python),'-m','ultra','pull',f'https://localhost:{server.server_port}',str(received),'--ca',str(cert),'--token-file',str(token)],env=env,cwd=root,capture_output=True,text=True,timeout=15)
                self.assertEqual(proc.returncode,0,proc.stderr)
                self.assertEqual(digest(data/'été.bin'),digest(received/'été.bin'))
            finally:server.shutdown();server.server_close();thread.join(timeout=5)

    def test_optional_download_failure_keeps_core_ready(self):
        with self.project() as root:
            real=subprocess.run
            def run(args,**kw):
                if '-m' in args and args[args.index('-m')+1]=='pip':
                    return subprocess.CompletedProcess(args,0 if '--version' in args else 1,'','réseau indisponible simulé')
                return real(args,**kw)
            with patch('prepare_installation.subprocess.run',side_effect=run):report=prepare(root)
            self.assertTrue(report['core_ready']);self.assertFalse(report['sharing_ready'])
            self.assertFalse(report['sharing_install_succeeded'])
            self.assertIn('simulé',(root/'reports/installation-sharing.log').read_text())

    def test_missing_ensurepip_keeps_core_ready(self):
        with self.project() as root:
            real=subprocess.run
            def run(args,**kw):
                if '-m' in args:return subprocess.CompletedProcess(args,1,'','pip absent simulé')
                return real(args,**kw)
            with patch('prepare_installation.subprocess.run',side_effect=run):report=prepare(root)
            self.assertTrue(report['core_ready']);self.assertFalse(report['sharing_ready'])

    def test_core_failure_does_not_attempt_optional_install(self):
        with self.project() as root:
            with patch('prepare_installation.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','Tcl absent simulé')) as run:
                report=prepare(root)
            self.assertFalse(report['core_ready']);self.assertEqual(report['status'],'failed')
            self.assertEqual(run.call_count,1)
            self.assertFalse((root/'.cycle.lock').exists())

    def test_existing_unknown_environment_not_overwritten(self):
        with self.project() as root:
            environment=root/'.venv-run';environment.mkdir();(environment/'conserver').write_text('intact')
            report=prepare(root,offline=True)
            self.assertFalse(report['core_ready']);self.assertEqual((environment/'conserver').read_text(),'intact')

    def test_environment_creation_space_error_releases_owned_lock(self):
        with self.project() as root:
            with patch('prepare_installation.venv.EnvBuilder.create',side_effect=OSError('espace insuffisant simulé')):
                report=prepare(root,offline=True)
            self.assertFalse(report['core_ready']);self.assertIn('espace insuffisant',report['error'])
            self.assertFalse((root/'.cycle.lock').exists());self.assertTrue((root/'ultra/engine.py').is_file())

    def test_existing_lock_never_removed(self):
        with self.project() as root:
            (root/'.cycle.lock').write_text('autre opération')
            with self.assertRaises(FileExistsError):prepare(root,offline=True)
            self.assertEqual((root/'.cycle.lock').read_text(),'autre opération')

    def test_notice_ignores_invalid_oversize_and_completed_report(self):
        with self.project() as root:
            reports=root/'reports';reports.mkdir();path=reports/'installation.json'
            for data in ('{','x'*32769,json.dumps({'core_ready':True,'sharing_ready':True}),json.dumps({'core_ready':False,'sharing_ready':False})):
                path.write_text(data);self.assertIsNone(installation_notice(root))

    def test_stale_pending_report_not_overwritten(self):
        with self.project() as root:
            reports=root/'reports';reports.mkdir();pending=reports/'installation.pending';pending.write_text('conserver')
            with self.assertRaises(FileExistsError):prepare(root,offline=True)
            self.assertEqual(pending.read_text(),'conserver');self.assertFalse((root/'.cycle.lock').exists())

    def test_own_partial_report_removed_on_write_failure(self):
        with self.project() as root:
            with patch('prepare_installation.json.dump',side_effect=OSError('disque plein simulé')),self.assertRaises(OSError):prepare(root,offline=True)
            self.assertFalse((root/'reports/installation.pending').exists())
            self.assertFalse((root/'.cycle.lock').exists())

    def test_cli_partial_success_and_core_failure_exit_codes(self):
        with patch.object(sys,'argv',['prepare_installation.py','--offline']),contextlib.redirect_stdout(io.StringIO()) as out:
            with patch('prepare_installation.prepare',return_value={'core_ready':True,'sharing_ready':False}):self.assertEqual(main(),0)
            self.assertIn('Création de nouvelles connexions',out.getvalue())
            with patch('prepare_installation.prepare',return_value={'core_ready':False,'sharing_ready':False,'error':'échec moteur'}):self.assertEqual(main(),1)
