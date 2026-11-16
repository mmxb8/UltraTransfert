"""Construire sur Windows, tester le ZIP extrait, puis publier le portable."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

from ultra import __version__

ROOT = Path(__file__).resolve().parent


def bundle_zip(folder, output):
    folder, output = Path(folder), Path(output)
    if not (folder/"UltraTransfert.exe").is_file():
        raise RuntimeError("Exécutable absent : aucun paquet portable créé.")
    files = sorted(folder.rglob("*"))
    if any(p.is_symlink() for p in files):
        raise RuntimeError("Lien interdit dans le paquet portable.")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.is_file():
                archive.write(path, Path("UltraTransfert")/path.relative_to(folder))


def validate_smoke(report):
    if (report.get("status") != "passed" or report.get("version") != __version__
            or report.get("platform") != "win32" or report.get("frozen") is not True
            or report.get("gui_created") is not True or report.get("sharing_prepared") is not True
            or report.get("sharing_session_checked") is not True
            or report.get("sharing_restore_checked") is not True
            or report.get("resumed_bytes", 0) <= 0):
        raise RuntimeError("Le contrôle Windows embarqué n'est pas valide : aucune publication.")


def main():
    if sys.platform != "win32":
        raise SystemExit("Construction Windows uniquement. Aucun EXE Windows ne sera produit sur cet hôte.")
    if platform.machine().upper() not in ("AMD64", "X86_64") or sys.maxsize <= 2**32:
        raise SystemExit("Première cible : Python Windows x64 sur hôte x64.")
    lock = ROOT/".cycle.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit("Un cycle détient le verrou du projet. Attendez sa fin.")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        with tempfile.TemporaryDirectory(prefix="UltraTransfert build ") as temp:
            tmp = Path(temp)
            subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                            "--onedir", "--windowed", "--noupx", "--name", "UltraTransfert",
                            "--distpath", str(tmp/"dist"), "--workpath", str(tmp/"work"),
                            "--specpath", str(tmp), "--paths", str(ROOT), str(ROOT/"launch_gui.py")],
                           cwd=ROOT, check=True)
            folder = tmp/"dist"/"UltraTransfert"
            (folder/"LIRE_MOI.txt").write_text((ROOT/"PORTABLE_UTILISATEUR.txt").read_text(encoding="utf-8"), encoding="utf-8")
            candidate = tmp/"portable.zip"
            bundle_zip(folder, candidate)
            extracted = tmp/"Essai extrait été 日本語"
            with zipfile.ZipFile(candidate) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError("Archive corrompue.")
                archive.extractall(extracted)
            report_path = tmp/"smoke.json"
            env = os.environ.copy()
            for key in ("PYTHONPATH", "PYTHONHOME"):
                env.pop(key, None)
            # Aucun interpréteur ou outil du poste de construction dans PATH.
            env["PATH"] = str(Path(os.environ["SystemRoot"])/"System32")
            subprocess.run([str(extracted/"UltraTransfert"/"UltraTransfert.exe"),
                            "--smoke-test", str(report_path)], cwd=tmp, env=env,
                           check=True, timeout=60)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            validate_smoke(report)
            dist = ROOT/"dist"
            dist.mkdir(exist_ok=True)
            output = dist/f"UltraTransfert-{__version__}-windows-x64-portable.zip"
            if output.exists():
                raise RuntimeError("Un paquet de cette version existe déjà ; archive précédente conservée.")
            # Publication sans écrasement, après validation des mêmes octets extraits.
            from ultra.engine import install_no_replace
            pending = dist/(output.name+".pending")
            created_pending = False
            try:
                with pending.open("xb") as f:
                    created_pending = True
                    f.write(candidate.read_bytes())
                    f.flush()
                    os.fsync(f.fileno())
                install_no_replace(pending, output)
            finally:
                if created_pending:
                    pending.unlink(missing_ok=True)
            report["archive_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
            (dist/(output.name+".validation.json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
            (dist/(output.name+".sha256")).write_text(report["archive_sha256"]+"  "+output.name+"\n", encoding="ascii")
            print(f"Portable créé après contrôle embarqué : {output}")
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
