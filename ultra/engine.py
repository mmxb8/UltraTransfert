from __future__ import annotations

import concurrent.futures as futures
import ctypes
import errno
import hashlib
import json
import math
import os
import shutil
from pathlib import Path
import stat
import subprocess
import sys
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from .pacing import BytePacer

STATE = ".ultratransfert-state"
VERSION = 1


class TransferError(Exception):
    pass


class OperationCancelled(TransferError):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise OperationCancelled("Préparation du partage annulée ; aucun transfert annoncé prêt.")


def signature(s):
    return (s.st_size, s.st_mtime_ns, s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode))


@dataclass(frozen=True)
class Entry:
    path: str
    kind: str
    size: int
    mtime_ns: int
    mode: int
    identity: tuple = ()
    sha256: str | None = None


def validate_entries(entries):
    keys = {}
    paths = set()
    for e in entries:
        parts = e.path.split("/")
        if not e.path or any(p in ("", ".", "..") for p in parts):
            raise TransferError(f"Chemin relatif interdit : {e.path!r}")
        if "\\" in e.path or ":" in e.path or e.path.startswith("/"):
            raise TransferError(f"Chemin non portable interdit : {e.path!r}")
        if parts[0].casefold() == STATE:
            raise TransferError(f"Nom réservé à l'état du transfert : {STATE}")
        if e.kind not in ("file", "dir") or e.size < 0 or e.size > 2**63-1:
            raise TransferError(f"Entrée invalide : {e.path}")
        if e.sha256 is not None and (len(e.sha256) != 64 or any(c not in "0123456789abcdef" for c in e.sha256)):
            raise TransferError(f"Empreinte invalide : {e.path}")
        key = unicodedata.normalize("NFC", e.path).casefold()
        if key in keys:
            raise TransferError(f"Collision casse/Unicode : {keys[key]} / {e.path}")
        keys[key] = e.path
        paths.add(e.path)
        for p in parts:
            if p.endswith((" ", ".")) or any(ord(c) < 32 for c in p) or any(c in '<>"|?*' for c in p):
                raise TransferError(f"Nom non portable : {e.path!r}")
            if p.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
                raise TransferError(f"Nom réservé Windows : {e.path}")
    types = {e.path: e.kind for e in entries}
    for e in entries:
        parent = Path(e.path).parent
        while str(parent) != ".":
            if types.get(parent.as_posix()) != "dir":
                raise TransferError(f"Dossier parent absent ou invalide : {e.path}")
            parent = parent.parent


def is_link(s):
    return stat.S_ISLNK(s.st_mode) or bool(getattr(s, "st_file_attributes", 0) & 0x400)


def inventory(root: Path, exclude_state=False, cancel=None):
    check_cancel(cancel)
    root = Path(root)
    rs = root.lstat()
    if is_link(rs) or not stat.S_ISDIR(rs.st_mode):
        raise TransferError("La source/destination doit être un dossier réel, sans lien.")
    entries = []

    def walk(directory):
        check_cancel(cancel)
        with os.scandir(directory) as it:
            for item in sorted(it, key=lambda x: x.name):
                check_cancel(cancel)
                rel = Path(item.path).relative_to(root).as_posix()
                if exclude_state and rel == STATE:
                    continue
                # Windows DirEntry.stat may omit the device and file identity.
                # Use the same authoritative metadata as LocalSource.check/open.
                s = (os.stat(item.path, follow_symlinks=False) if sys.platform == 'win32'
                     else item.stat(follow_symlinks=False))
                if is_link(s):
                    raise TransferError(f"Lien symbolique/jonction non pris en charge : {rel}")
                if stat.S_ISDIR(s.st_mode):
                    entries.append(Entry(rel, "dir", 0, s.st_mtime_ns, stat.S_IMODE(s.st_mode)))
                    walk(item.path)
                elif stat.S_ISREG(s.st_mode):
                    entries.append(Entry(rel, "file", s.st_size, s.st_mtime_ns, stat.S_IMODE(s.st_mode), signature(s)))
                else:
                    raise TransferError(f"Fichier spécial non pris en charge : {rel}")

    walk(root)
    entries.sort(key=lambda e: e.path)
    validate_entries(entries)
    check_cancel(cancel)
    return entries


def digest(path, buffer_size=4*1024*1024, cancel=None):
    h = hashlib.sha256()
    with open(path, "rb", buffering=0) as f:
        while True:
            if cancel is not None and cancel.is_set():
                raise OperationCancelled("Vérification interrompue ; reprise possible.")
            data = f.read(buffer_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


class LocalSource:
    def __init__(self, root, cancel=None):
        check_cancel(cancel)
        raw = Path(root).absolute()
        if is_link(raw.lstat()):
            raise TransferError("Une source liée n'est pas prise en charge.")
        self.root = raw.resolve(strict=True)
        self.entries = inventory(self.root, cancel=cancel)
        self.identity = "local:" + str(self.root)

    def open(self, e, offset=0):
        self.check(e)
        f = open(self.root / e.path, "rb", buffering=0)
        if signature(os.fstat(f.fileno())) != tuple(e.identity):
            f.close()
            raise TransferError(f"Source remplacée : {e.path}")
        f.seek(offset)
        return f

    def check(self, e):
        s = (self.root / e.path).lstat()
        if is_link(s) or signature(s) != tuple(e.identity):
            raise TransferError(f"Source modifiée : {e.path}")

    def check_all(self, cancel=None):
        if inventory(self.root, cancel=cancel) != self.entries:
            raise TransferError("L'inventaire source a changé pendant le transfert. Relancez avec un nouvel état.")


def safe_parents(root, rel):
    current = Path(root)
    for part in Path(rel).parts:
        current = current / part
        try:
            current.mkdir()
        except FileExistsError:
            pass
        s = current.lstat()
        if is_link(s) or not stat.S_ISDIR(s.st_mode):
            raise TransferError(f"Destination liée ou non-dossier : {current}")


def install_no_replace(src, dst):
    """Publication atomique sans écrasement ; échoue si le FS ne l'autorise pas."""
    if os.name == "nt":
        os.rename(src, dst)  # Windows refuse un nom destination déjà présent.
        return
    if sys.platform.startswith("linux"):
        lib = ctypes.CDLL(None, use_errno=True)
        rename = getattr(lib, "renameat2", None)
        if rename is not None:
            result = rename(-100, os.fsencode(src), -100, os.fsencode(dst), 1)
            if result == 0:
                return
            code = ctypes.get_errno()
            if code not in (errno.ENOSYS, errno.EINVAL, errno.ENOTSUP):
                raise OSError(code, os.strerror(code), str(dst))
    os.link(src, dst, follow_symlinks=False)
    os.unlink(src)


@dataclass
class Options:
    workers: int = 0  # 0 = choix prudent selon l'inventaire ; réglable explicitement.
    buffer_size: int = 1024*1024
    native: str | None = None
    native_threshold: int = 64*1024*1024
    max_bytes_per_second: float = 0


@dataclass
class Result:
    files: int = 0
    directories: int = 0
    bytes: int = 0
    copied: int = 0
    reused: int = 0
    resumed_bytes: int = 0
    seconds: float = 0
    file_work_seconds: float = 0
    final_verify_seconds: float = 0
    errors: list = field(default_factory=list)
    hashes: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)
    max_bytes_per_second: float = 0
    warnings: list = field(default_factory=lambda: ["Cette version copie les flux de données principaux, noms et arborescence. ACL, propriétaires, flux NTFS alternatifs, attributs étendus, dates de création et relations de liens physiques ne sont pas conservés. Liens symboliques/jonctions et noms non portables sont refusés explicitement."])


class Transfer:
    def __init__(self, source, destination, options=None, progress=None, cancel=None, phase=None):
        self.source = source
        raw = Path(destination).absolute()
        if raw.exists() and is_link(raw.lstat()):
            raise TransferError("Destination liée interdite.")
        self.destination = raw.resolve()
        if hasattr(source, "validate_destination"):
            source.validate_destination(self.destination)
        if isinstance(source, LocalSource):
            a, b = source.root, self.destination
            if a == b or a in b.parents or b in a.parents:
                raise TransferError("Source et destination ne doivent pas se contenir.")
        self.options = options or Options()
        rate = self.options.max_bytes_per_second
        if type(rate) not in (int, float) or not math.isfinite(rate) or rate < 0:
            raise TransferError("La limite de vitesse doit être positive et finie, ou 0 pour sans limite.")
        if rate and self.options.native:
            raise TransferError("La limite de vitesse nécessite le moteur Python ; retirez le helper natif.")
        self.pacer = BytePacer(rate) if rate else None
        if not 0 <= self.options.workers <= 32 or not 65536 <= self.options.buffer_size <= 64*1024*1024:
            raise TransferError("Réglages invalides : 0 (auto) ou 1–32 workers, tampon de 64 Kio à 64 Mio.")
        files = [e for e in source.entries if e.kind == "file"]
        mean = sum(e.size for e in files)/max(1, len(files))
        self.workers = self.options.workers or (1 if isinstance(source, LocalSource) and mean < 65536 else 2 if isinstance(source, LocalSource) else 4)
        self.cancel = cancel or threading.Event()
        self.progress = progress
        self.phase = phase or (lambda message: None)
        self.mutex = threading.Lock()
        self.state = self.destination / STATE
        self.result = Result(max_bytes_per_second=rate)
        self.completed_bytes = 0

    def tick(self, n):
        with self.mutex:
            self.completed_bytes += n
            if self.progress:
                self.progress(self.completed_bytes, self.result.bytes)

    def stopped(self):
        if self.cancel.is_set():
            raise TransferError("Transfert interrompu ; les fichiers partiels sont conservés.")

    def read_source(self, stream, count):
        data = stream.read(count)
        if self.pacer is not None and self.pacer.wait(len(data), self.cancel):
            self.stopped()
        return data

    def journal(self, data):
        with self.mutex:
            with open(self.state / "journal.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"time": time.time(), **data}, ensure_ascii=False) + "\n")

    def prepare(self):
        self.destination.mkdir(parents=True, exist_ok=True)
        if self.state.exists():
            if is_link(self.state.lstat()) or not (self.state / "manifest.json").is_file():
                raise TransferError(f"État réservé inconnu : {self.state}")
        else:
            self.state.mkdir(mode=0o700)
        # Exclusivité coopérative ; jamais de suppression automatique d'un verrou.
        try:
            fd = os.open(self.state / "lock", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise TransferError("Transfert déjà verrouillé. Après un arrêt brutal, vérifiez qu'il est arrêté avant de supprimer le fichier lock.")
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        try:
            expected = {"version": VERSION, "source": self.source.identity, "entries": [asdict(e) for e in self.source.entries]}
            # Round-trip JSON pour normaliser les tuples.
            expected = json.loads(json.dumps(expected))
            manifest = self.state / "manifest.json"
            if manifest.exists():
                if json.loads(manifest.read_text(encoding="utf-8")) != expected:
                    raise TransferError("Source ou inventaire différent de l'état de reprise. Utilisez une autre destination.")
            else:
                manifest.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
            safe_parents(self.state, "parts")
            # Estimation prudente : un partiel doit être validé avant d'être crédité.
            required = sum(e.size for e in self.source.entries
                           if e.kind == "file" and not (self.destination/e.path).exists())
            available = shutil.disk_usage(self.destination).free
            if required > available:
                raise TransferError(f"Espace insuffisant : {required:,} octets requis, {available:,} disponibles (estimation prudente).")
        except BaseException:
            (self.state / "lock").unlink(missing_ok=True)
            raise

    def copy_one(self, e):
        self.stopped()
        target = self.destination / e.path
        safe_parents(self.destination, Path(e.path).parent)
        if target.exists() or target.is_symlink():
            s = target.lstat()
            if is_link(s) or not stat.S_ISREG(s.st_mode) or s.st_size != e.size:
                raise TransferError(f"Conflit destination : {e.path}")
            expected = e.sha256
            if expected is None:
                with self.source.open(e) as src:
                    expected = self.hash_stream(src)
                self.source.check(e)
            actual = digest(target, self.options.buffer_size, self.cancel)
            if actual != expected:
                raise TransferError(f"Fichier existant différent, aucun écrasement : {e.path}")
            self.tick(e.size)
            return e.path, expected, False, 0

        part = self.state / "parts" / (hashlib.sha256(e.path.encode("utf-8")).hexdigest() + ".part")
        if part.exists() and (is_link(part.lstat()) or not part.is_file()):
            raise TransferError("Fichier partiel lié ou invalide.")
        h = hashlib.sha256()
        offset = 0
        # Aucun octet déjà présent n'est cru sans comparaison avec la source.
        if part.exists():
            with self.source.open(e) as src, open(part, "rb", buffering=0) as old:
                while offset < min(part.stat().st_size, e.size):
                    self.stopped()
                    n = min(self.options.buffer_size, part.stat().st_size-offset, e.size-offset)
                    a, b = self.read_source(src, n), old.read(n)
                    if len(a) != n or a != b:
                        break
                    h.update(a)
                    offset += n
            with open(part, "r+b", buffering=0) as old:
                old.truncate(offset)

        resumed = offset
        self.tick(offset)
        use_native = self.options.native and isinstance(self.source, LocalSource) and e.size >= self.options.native_threshold
        if use_native:
            # Le helper recalcule SHA-256 sur la totalité de la source, préfixe inclus.
            if not part.exists():
                part.touch()
            proc = subprocess.Popen([self.options.native, "copy", str(self.source.root/e.path), str(part), str(offset), str(self.options.buffer_size)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while True:
                try:
                    out, err = proc.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    pass
                if self.cancel.is_set():
                    proc.terminate()
                    proc.communicate()
                    self.stopped()
            if proc.returncode:
                raise TransferError(err.decode("utf-8", errors="replace"))
            expected = out.decode("ascii").strip()
            if len(expected) != 64:
                raise TransferError("Réponse native invalide.")
            self.tick(e.size-offset)
        else:
            with self.source.open(e, offset) as src, open(part, "ab", buffering=0) as dst:
                count = offset
                while count < e.size:
                    self.stopped()
                    data = self.read_source(src, min(self.options.buffer_size, e.size-count))
                    if not data:
                        raise TransferError(f"Source tronquée : {e.path}")
                    view = memoryview(data)
                    while view:
                        n = dst.write(view)
                        if not n:
                            raise TransferError("Écriture incomplète.")
                        view = view[n:]
                    h.update(data)
                    count += len(data)
                    self.tick(len(data))
                if src.read(1):
                    raise TransferError(f"Source agrandie : {e.path}")
                dst.flush()
                os.fsync(dst.fileno())
            expected = h.hexdigest()

        self.stopped()
        self.source.check(e)
        if e.sha256 and expected != e.sha256:
            raise TransferError(f"Source distante modifiée ou transmission corrompue : {e.path}")
        if part.stat().st_size != e.size or digest(part, self.options.buffer_size, self.cancel) != expected:
            raise TransferError(f"Vérification SHA-256 échouée : {e.path}")
        os.utime(part, ns=(e.mtime_ns, e.mtime_ns))
        os.chmod(part, e.mode)
        install_no_replace(part, target)
        return e.path, expected, True, resumed

    def hash_stream(self, stream):
        h = hashlib.sha256()
        while data := self.read_source(stream, self.options.buffer_size):
            self.stopped()
            h.update(data)
        return h.hexdigest()

    def record(self, outcome):
        path, sha, copied, resumed = outcome
        self.result.hashes[path] = sha
        self.result.copied += int(copied)
        self.result.reused += int(not copied)
        self.result.resumed_bytes += resumed
        self.journal({"event": "verified", "path": path, "sha256": sha,
                      "copied": copied, "resumed_bytes": resumed})

    def run(self):
        started = time.perf_counter()
        validate_entries(self.source.entries)
        self.result.files = sum(e.kind == "file" for e in self.source.entries)
        self.result.directories = sum(e.kind == "dir" for e in self.source.entries)
        self.result.bytes = sum(e.size for e in self.source.entries if e.kind == "file")
        try:
            self.prepare()
        except BaseException:
            if hasattr(self.source, "release_connections"):
                self.source.release_connections()
            raise
        try:
            self.phase("Préparation des dossiers")
            # Tout conflit ou fichier supplémentaire est détecté avant toute copie.
            existing = {e.path: e for e in inventory(self.destination, exclude_state=True, cancel=self.cancel)}
            wanted = {e.path: e for e in self.source.entries}
            for path, e in existing.items():
                if path not in wanted or wanted[path].kind != e.kind:
                    raise TransferError(f"Élément destination non prévu : {path}")
            for e in self.source.entries:
                if e.kind == "dir":
                    safe_parents(self.destination, e.path)
            files = [e for e in self.source.entries if e.kind == "file"]
            work_start = time.perf_counter()
            self.phase("Copie et vérification des fichiers")
            if self.workers == 1:
                for e in files:
                    self.stopped()
                    self.record(self.copy_one(e))
            else:
                with futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
                    # Fenêtre bornée : pas une Future en mémoire pour chaque fichier.
                    iterator = iter(files)
                    pending = set()
                    while True:
                        while len(pending) < self.workers*2 and not self.cancel.is_set():
                            try:
                                e = next(iterator)
                            except StopIteration:
                                break
                            pending.add(pool.submit(self.copy_one, e))
                        if not pending:
                            break
                        done, pending = futures.wait(pending, return_when=futures.FIRST_COMPLETED)
                        for future in done:
                            try:
                                self.record(future.result())
                            except Exception as exc:
                                self.result.errors.append(str(exc))
                                self.cancel.set()
                    self.stopped()
            self.result.file_work_seconds = time.perf_counter()-work_start
            self.source.check_all(cancel=self.cancel)
            verify_start = time.perf_counter()
            self.phase("Vérification finale SHA-256 et inventaire")
            # Seconde lecture complète après publication, avec inventaire exact.
            actual = inventory(self.destination, exclude_state=True, cancel=self.cancel)
            if {(e.path, e.kind, e.size) for e in actual} != {(e.path, e.kind, e.size) for e in self.source.entries}:
                raise TransferError("L'inventaire destination final diffère de la source.")
            def verify(e):
                self.stopped()
                if digest(self.destination/e.path, self.options.buffer_size, self.cancel) != self.result.hashes[e.path]:
                    raise TransferError(f"Corruption après publication : {e.path}")
            if self.workers == 1:
                for e in files:
                    verify(e)
            else:
                with futures.ThreadPoolExecutor(max_workers=self.workers) as pool:
                    iterator = iter(files)
                    pending = set()
                    while True:
                        while len(pending) < self.workers*2:
                            try:
                                e = next(iterator)
                            except StopIteration:
                                break
                            pending.add(pool.submit(verify, e))
                        if not pending:
                            break
                        done, pending = futures.wait(pending, return_when=futures.FIRST_COMPLETED)
                        for future in done:
                            future.result()
            self.result.final_verify_seconds = time.perf_counter()-verify_start
            self.source.check_all(cancel=self.cancel)
            # Réapplique les dates des dossiers, en commençant par les plus profonds.
            for e in sorted(self.source.entries, key=lambda x: x.path.count("/"), reverse=True):
                self.stopped()
                if e.kind == "dir":
                    os.utime(self.destination/e.path, ns=(e.mtime_ns, e.mtime_ns))
                    os.chmod(self.destination/e.path, e.mode)
            self.stopped()
        except OperationCancelled:
            message = "Vérification interrompue ; reprise possible."
            if message not in self.result.errors:
                self.result.errors.append(message)
        except Exception as exc:
            if str(exc) not in self.result.errors:
                self.result.errors.append(str(exc))
        finally:
            if hasattr(self.source, "release_connections"):
                self.source.release_connections()
            self.result.seconds = time.perf_counter()-started
            if hasattr(self.source, "statistics"):
                self.result.delta = self.source.statistics()
            try:
                report = asdict(self.result)
                (self.state / "last-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                self.journal({"event": "complete" if not self.result.errors else "failed", "seconds": self.result.seconds, "errors": self.result.errors})
            finally:
                (self.state / "lock").unlink(missing_ok=True)
        return self.result
