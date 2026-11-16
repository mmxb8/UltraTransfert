"""Réception par blocs SHA-256, réutilisés dans une référence locale en lecture seule.

Le dossier destination reste complet et indépendant : aucune copie par référence,
aucun lien physique, aucun écrasement de l'ancienne version.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import threading
import time

from .engine import TransferError, inventory, is_link


class DeltaSource:
    def __init__(self, remote, reference, cancel=None, phase=None):
        if remote.block_size is None or remote.chunks is None:
            raise TransferError("Le serveur doit être lancé avec --delta pour réutiliser les blocs.")
        raw = Path(reference).absolute()
        if is_link(raw.lstat()):
            raise TransferError("La référence ne doit pas être un lien.")
        self.root = raw.resolve(strict=True)
        self.remote = remote
        self.entries, self.identity = remote.entries, remote.identity
        self.block_size = remote.block_size
        self.cancel = cancel or threading.Event()
        self.mutex = threading.Lock()
        self.locations = {}
        self.stats = {"reference_scanned_bytes": 0, "reused_payload_bytes": 0,
                      "downloaded_payload_bytes": 0, "reused_blocks": 0,
                      "downloaded_blocks": 0, "index_seconds": 0.0}
        started = time.perf_counter()
        if phase:
            phase("Indexation SHA-256 des blocs de la référence locale")
        # Ne conserve que les empreintes utiles au transfert en cours.
        wanted = {h for hashes in remote.chunks.values() for h in hashes}
        for entry in inventory(self.root, exclude_state=True):
            if entry.kind != "file":
                continue
            path = self.root/entry.path
            with path.open("rb", buffering=0) as stream:
                offset = 0
                while offset < entry.size:
                    self.stopped()
                    data = stream.read(min(self.block_size, entry.size-offset))
                    if not data:
                        raise TransferError(f"Référence tronquée pendant l'indexation : {entry.path}")
                    key = hashlib.sha256(data).hexdigest()
                    if key in wanted:
                        self.locations.setdefault(key, (path, offset, len(data)))
                    offset += len(data)
                    self.stats["reference_scanned_bytes"] += len(data)
        self.stats["index_seconds"] = time.perf_counter()-started

    def stopped(self):
        if self.cancel.is_set():
            raise TransferError("Transfert delta interrompu ; reprise possible.")

    def validate_destination(self, destination):
        if self.root == destination or self.root in destination.parents or destination in self.root.parents:
            raise TransferError("La référence et la destination delta ne doivent pas se contenir.")

    def block(self, entry, index):
        self.stopped()
        offset = index*self.block_size
        length = min(self.block_size, entry.size-offset)
        expected = self.remote.chunks[entry.path][index]
        with self.mutex:
            location = self.locations.get(expected)
        if location:
            path, position, size = location
            try:
                # Nouvelle lecture + SHA à chaque réutilisation : l'index n'est pas cru aveuglément.
                if size == length and not is_link(path.lstat()):
                    with path.open("rb", buffering=0) as stream:
                        stream.seek(position)
                        data = stream.read(length)
                    if len(data) == length and hashlib.sha256(data).hexdigest() == expected:
                        self.count("reused", length)
                        return data
            except OSError:
                pass
        # Une référence disparue/corrompue est simplement remplacée par un bloc distant vérifié.
        with self.remote.open_range(entry, offset, length) as stream:
            data = stream.read(length+1)
        if len(data) != length or hashlib.sha256(data).hexdigest() != expected:
            raise TransferError(f"Bloc distant corrompu ou incomplet : {entry.path}, bloc {index}")
        self.count("downloaded", length)
        return data

    def count(self, kind, size):
        with self.mutex:
            self.stats[kind+"_payload_bytes"] += size
            self.stats[kind+"_blocks"] += 1

    def statistics(self):
        with self.mutex:
            return dict(self.stats)

    def open(self, entry, offset=0):
        if not 0 <= offset <= entry.size:
            raise TransferError("Position delta invalide.")
        return DeltaStream(self, entry, offset)

    def check(self, entry):
        self.remote.check(entry)

    def release_connections(self):
        self.remote.release_connections()

    def check_all(self, cancel=None):
        self.remote.check_all(cancel=cancel)


class DeltaStream:
    def __init__(self, source, entry, offset):
        self.source, self.entry, self.position = source, entry, offset
        self.current_index = None
        self.current = b""
        self.closed = False

    def read(self, count):
        if self.closed:
            raise ValueError("Flux delta fermé")
        if count < 0:
            raise ValueError("Lecture delta non bornée interdite")
        if not count or self.position == self.entry.size:
            return b""
        self.source.stopped()
        remaining = min(count, self.entry.size-self.position)
        pieces = []
        while remaining:
            self.source.stopped()
            index, inside = divmod(self.position, self.source.block_size)
            if index != self.current_index:
                self.current = self.source.block(self.entry, index)
                self.current_index = index
            data = self.current[inside:inside+remaining]
            self.position += len(data)
            remaining -= len(data)
            pieces.append(data)
        return b"".join(pieces)

    def close(self):
        self.closed = True
        self.current = b""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
