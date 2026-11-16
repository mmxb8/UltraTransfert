"""Source distante HTTPS en lecture seule, authentifiée par jeton hors URL."""
from __future__ import annotations

from dataclasses import asdict, replace
import gzip
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import socket
from pathlib import Path
import ssl
import threading
import zlib
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPSHandler, HTTPRedirectHandler

from .engine import Entry, LocalSource, TransferError, digest, validate_entries, check_cancel
from .blockstream import BlockReader, ENCODING, write_stream
from .compression import AdaptiveEncoder, codecs
from .https_pool import HTTPSPool
from .predictive_budget import BudgetEncoder
from .predictive_stream import LeanBlockReader, raw_view_unframe

PREDICTIVE_ENCODING = "x-ultra-predictive-v1"


def read_token(path):
    token = Path(path).read_text(encoding="utf-8").strip()
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise TransferError("Le jeton doit contenir au moins 32 caractères ASCII sans espace.")
    return token


class ChunkedWriter:
    """Framing HTTP/1.1 borné, sans tampon du fichier comprimé complet."""
    def __init__(self, output):
        self.output = output
        self.pending = bytearray()

    def emit(self):
        if self.pending:
            # Une écriture, au plus 64 Kio de charge, sans fichier entier en mémoire.
            self.output.write(f"{len(self.pending):x}\r\n".encode("ascii") + self.pending + b"\r\n")
            self.pending.clear()

    def write(self, data):
        view = memoryview(data)
        position = 0
        while position < len(view):
            size = min(65536-len(self.pending), len(view)-position)
            self.pending.extend(view[position:position+size])
            position += size
            if len(self.pending) == 65536:
                self.emit()
        return len(data)

    def flush(self):
        self.emit()
        self.output.flush()

    def finish(self):
        self.emit()
        self.output.write(b"0\r\n\r\n")


class TransferHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, context):
        self.context = context
        self._connections = set()
        self._connections_lock = threading.Lock()
        self._closing = False
        super().__init__(address, handler)

    def get_request(self):
        raw, address = super().get_request()
        try:
            request = self.context.wrap_socket(raw, server_side=True, do_handshake_on_connect=False)
        except BaseException:
            raw.close()
            raise
        request.settimeout(5)
        with self._connections_lock:
            if self._closing or len(self._connections) >= 64:
                request.close()
                raise OSError("Serveur arrêté ou limite de connexions atteinte")
            self._connections.add(request)
        return request, address

    def process_request_thread(self, request, address):
        try:
            request.do_handshake()
            request.settimeout(120)
            request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            self.shutdown_request(request)
            return
        super().process_request_thread(request, address)

    def shutdown_request(self, request):
        with self._connections_lock:
            self._connections.discard(request)
        super().shutdown_request(request)

    def close_connections(self):
        with self._connections_lock:
            self._closing = True
            connections = list(self._connections)
        for request in connections:
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()

    def server_close(self):
        self.close_connections()
        super().server_close()


def make_server(source, address, certfile, keyfile, token, compression="none", block_size=None, link_mbps=100, *, before_bind=None, cancel=None, selection_pruning=False):
    check_cancel(cancel)
    if selection_pruning and compression!='ultra':
        raise TransferError("L'élagage de sélection exige le mode expérimental --compression ultra.")
    if source.root in Path(keyfile).resolve().parents:
        raise TransferError("La clé privée ne doit pas se trouver dans le dossier partagé. Placez la configuration hors des données à partager.")
    if compression not in ("none", "gzip", "auto", "ultra", "predictive"):
        raise TransferError("Compression réseau inconnue.")
    if not math.isfinite(link_mbps) or link_mbps <= 0:
        raise TransferError("Le débit estimé doit être positif et fini.")
    if block_size is not None and not 65536 <= block_size <= 16*1024*1024:
        raise TransferError("Taille de bloc delta invalide.")
    # Une empreinte de référence précède l'exposition des données.
    entries = []
    chunks = {}
    for e in source.entries:
        check_cancel(cancel)
        if e.kind == "file":
            source.check(e)
            if block_size:
                full = hashlib.sha256()
                blocks = []
                with source.open(e) as stream:
                    while block := stream.read(block_size):
                        check_cancel(cancel)
                        full.update(block)
                        blocks.append(hashlib.sha256(block).hexdigest())
                sha = full.hexdigest()
                chunks[e.path] = blocks
            else:
                sha = digest(source.root/e.path, cancel=cancel)
            source.check(e)
            entries.append(replace(e, sha256=sha))
        else:
            entries.append(e)
    if cancel is None:
        source.check_all()
    else:
        source.check_all(cancel=cancel)
    manifest = {"version": 1, "entries": [asdict(e) for e in entries]}
    if block_size:
        manifest.update(block_size=block_size, chunks=chunks)
    payload = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
    metrics = {"file_payload_bytes": 0, "file_requests": 0, "block_wire_bytes": 0,
               "recipe_searches": 0, "recipe_reused_blocks": 0}
    metrics_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        def log_message(self, *args):
            pass  # Aucun jeton ni chemin dans un journal HTTP implicite.

        def do_GET(self):
            if not hmac.compare_digest(self.headers.get("Authorization", "").encode("utf-8"), ("Bearer " + token).encode("utf-8")):
                self.send_error(401, "Authentification requise")
                return
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/manifest":
                    source.check_all()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                if parsed.path != "/file":
                    self.send_error(404)
                    return
                query = parse_qs(parsed.query, strict_parsing=True)
                index, offset = int(query["id"][0]), int(query.get("offset", ["0"])[0])
                if not 0 <= index < len(entries):
                    raise ValueError("index")
                e = entries[index]
                if e.kind != "file" or not 0 <= offset <= e.size:
                    raise ValueError("offset/type")
                length = int(query.get("length", [str(e.size-offset)])[0])
                if not 0 <= length <= e.size-offset:
                    raise ValueError("length")
                with metrics_lock:
                    metrics["file_requests"] += 1
                original = source.entries[index]
                with source.open(original, offset) as src:
                    accepted = {s.strip() for s in self.headers.get("Accept-Encoding", "").split(',')}
                    selected_encoding = PREDICTIVE_ENCODING if compression == "predictive" else ENCODING
                    if compression in ("ultra", "predictive") and selected_encoding in accepted:
                        peer_codecs = self.headers.get("X-Ultra-Codecs", "raw,zlib1").split(',')
                        allowed = [c for c in codecs() if c in peer_codecs]
                        if 'raw' not in allowed:
                            raise ValueError('Codec brut obligatoire')
                        encoder = (BudgetEncoder(link_mbps, allowed) if compression == "predictive" else
                                   AdaptiveEncoder(link_mbps, allowed, prune=True) if selection_pruning else AdaptiveEncoder(link_mbps, allowed))
                        self.send_response(200)
                        self.send_header("Content-Type", "application/octet-stream")
                        bounded = length <= 65536
                        if bounded:
                            self.send_header("Transfer-Encoding", "chunked")
                        else:
                            self.send_header("Connection", "close")
                            self.close_connection = True
                        self.send_header("Content-Encoding", selected_encoding)
                        self.end_headers()
                        def count_block(n):
                            with metrics_lock:
                                metrics["file_payload_bytes"] += n
                        output = ChunkedWriter(self.wfile) if bounded else self.wfile
                        wire = write_stream(src, output, length, encoder, count_block)
                        with metrics_lock:
                            metrics["block_wire_bytes"] += wire
                            metrics["recipe_searches"] += encoder.searches
                            metrics["recipe_reused_blocks"] += encoder.reused
                        source.check(original)
                        if bounded:
                            output.finish()
                        return
                    compress = compression != "none" and "gzip" in self.headers.get("Accept-Encoding", "")
                    if compress and compression == "auto":
                        sample = src.read(min(65536, length))
                        compress = len(sample) >= 1024 and len(zlib.compress(sample, 1)) < len(sample)*0.90
                        src.seek(offset)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    bounded = compress and length <= 65536
                    if compress:
                        if bounded:
                            self.send_header("Transfer-Encoding", "chunked")
                        else:
                            self.send_header("Connection", "close")
                            self.close_connection = True
                        self.send_header("Content-Encoding", "gzip")
                    else:
                        self.send_header("Content-Length", str(length))
                    self.end_headers()
                    chunked = ChunkedWriter(self.wfile) if bounded else None
                    output = gzip.GzipFile(fileobj=chunked if bounded else self.wfile, mode="wb", compresslevel=1) if compress else self.wfile
                    try:
                        remaining = length
                        while remaining:
                            data = src.read(min(4*1024*1024, remaining))
                            if not data:
                                raise TransferError("Source tronquée pendant la réponse.")
                            output.write(data)
                            with metrics_lock:
                                metrics["file_payload_bytes"] += len(data)
                            remaining -= len(data)
                    finally:
                        if compress:
                            output.close()
                    source.check(original)
                    if chunked is not None:
                        chunked.finish()
            except (KeyError, ValueError, IndexError):
                self.send_error(400)
            except (OSError, TransferError):
                # Si les en-têtes sont déjà partis, le client vérifiera longueur et SHA.
                self.close_connection = True

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile, keyfile, password=lambda: "")
    if before_bind is not None:
        before_bind()
    check_cancel(cancel)
    server = TransferHTTPServer(address, Handler, context)
    try:
        check_cancel(cancel)
    except BaseException:
        server.server_close()
        raise
    server.transfer_metrics = metrics
    return server


class RemoteStream:
    def __init__(self, response, expected_length=None):
        self.response = response
        encoding = response.headers.get("Content-Encoding")
        if encoding == PREDICTIVE_ENCODING:
            self.reader = LeanBlockReader(response, expected_length, decoder=raw_view_unframe)
        elif encoding == ENCODING:
            self.reader = BlockReader(response, expected_length)
        elif encoding == "gzip":
            self.reader = gzip.GzipFile(fileobj=response)
        elif encoding in (None, "identity"):
            self.reader = response
        else:
            response.close()
            raise TransferError("Encodage distant inconnu.")

    def read(self, n):
        return self.reader.read(n)

    def readinto(self, buffer):
        return self.reader.readinto(buffer)

    def close(self):
        self.reader.close()
        self.response.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise TransferError("Redirection HTTPS refusée ; vérifiez l'adresse de l'émetteur.")


class RemoteSource:
    def __init__(self, url, token, cafile, compression="none", *, cadata=None):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise TransferError("Utilisez une origine HTTPS sans identifiants ni chemin.")
        if compression not in ("none", "gzip", "auto", "ultra", "predictive"):
            raise TransferError("Compression inconnue.")
        self.url = url.rstrip("/")
        self.token = token
        self.compression = compression
        if cafile is not None and cadata is not None:
            raise TransferError("Une seule source de confiance TLS est autorisée.")
        self.context = ssl.create_default_context(cafile=str(cafile) if cafile is not None else None, cadata=cadata)
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.opener = build_opener(HTTPSHandler(context=self.context), NoRedirect())
        self.pool = HTTPSPool(self.url, self.context)
        try:
            self.payload = self.get_manifest()
        except BaseException:
            self.release_connections()
            raise
        data = json.loads(self.payload)
        if data.get("version") != 1:
            raise TransferError("Version de protocole inconnue.")
        self.entries = [Entry(**e) for e in data["entries"]]
        validate_entries(self.entries)
        if any(e.kind == "file" and not e.sha256 for e in self.entries):
            raise TransferError("Empreinte distante manquante.")
        self.block_size = data.get("block_size")
        self.chunks = data.get("chunks")
        if self.block_size is not None or self.chunks is not None:
            self.validate_chunks()
        self.index = {e.path: i for i, e in enumerate(self.entries)}
        self.identity = "https:" + self.url + ":" + hashlib.sha256(self.payload).hexdigest()

    def request(self, path):
        encoding = (PREDICTIVE_ENCODING if self.compression == "predictive" else
                    ENCODING if self.compression == "ultra" else "gzip" if self.compression in ("gzip", "auto") else "identity")
        headers = {"Authorization": "Bearer "+self.token, "Accept-Encoding": encoding,
                   "X-Ultra-Codecs": ','.join(codecs())}
        if self.pool is not None:
            return self.pool.request(path, headers)
        req = Request(self.url+path, headers=headers)
        return self.opener.open(req, timeout=120)

    def release_connections(self):
        if self.pool is not None:
            self.pool.close()

    def get_manifest(self):
        with self.request("/manifest") as response:
            data = response.read(64*1024*1024+1)
        if len(data) > 64*1024*1024:
            raise TransferError("Manifeste distant trop volumineux (>64 Mio).")
        return data

    def open(self, e, offset=0):
        return self.stream(f"/file?id={self.index[e.path]}&offset={offset}", e.size-offset)

    def stream(self, path, length):
        response = self.request(path)
        encoding = response.headers.get("Content-Encoding")
        expected = {"ultra": ENCODING, "predictive": PREDICTIVE_ENCODING}.get(self.compression)
        if ((expected is not None and encoding != expected) or
                (expected is None and encoding in (ENCODING, PREDICTIVE_ENCODING))):
            response.close()
            raise TransferError("Compression expérimentale non négociée : choisir le même mode expérimental aux deux extrémités.")
        return RemoteStream(response, length)

    def validate_chunks(self):
        size, chunks = self.block_size, self.chunks
        if type(size) is not int or not 65536 <= size <= 16*1024*1024 or not isinstance(chunks, dict):
            raise TransferError("Manifeste de blocs invalide.")
        files = {e.path: e for e in self.entries if e.kind == "file"}
        if chunks.keys() != files.keys():
            raise TransferError("Inventaire des blocs incomplet.")
        for path, e in files.items():
            hashes = chunks[path]
            if not isinstance(hashes, list) or len(hashes) != (e.size+size-1)//size:
                raise TransferError(f"Nombre de blocs invalide : {path}")
            if any(not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in hashes):
                raise TransferError(f"Empreinte de bloc invalide : {path}")

    def open_range(self, e, offset, length):
        return self.stream(f"/file?id={self.index[e.path]}&offset={offset}&length={length}", length)

    def check(self, e):
        pass  # SHA-256 initial obligatoire, vérifié par le moteur après la lecture.

    def check_all(self, cancel=None):
        check_cancel(cancel)
        if self.get_manifest() != self.payload:
            raise TransferError("L'inventaire distant a changé.")
        check_cancel(cancel)
