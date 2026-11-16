"""Connexions TLS réutilisables, uniquement après réponse entièrement consommée.

Pas de retry implicite, redirection, désactivation TLS ou partage entre origines.
Les réponses tronquées/abandonnées ferment leur connexion.
"""
import http.client
import threading
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from .engine import TransferError


class Response:
    def __init__(self, pool, connection, response):
        self.pool, self.connection, self.response = pool, connection, response
        self.headers = response.headers
        self.closed = False
        self.failed = False

    def read(self, n=None):
        try:
            return self.response.read(n)
        except BaseException:
            self.failed = True
            raise

    def readinto(self, buffer):
        try:
            return self.response.readinto(buffer)
        except BaseException:
            self.failed = True
            raise

    def close(self):
        if self.closed:
            return
        self.closed = True
        reusable = (not self.failed and not self.response.will_close and
                    (self.response.length == 0 or (self.response.chunked and self.response.isclosed())))
        self.response.close()
        self.pool.release(self.connection, reusable)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class HTTPSPool:
    def __init__(self, origin, context, max_idle=8):
        parsed = urlsplit(origin)
        self.host, self.port = parsed.hostname, parsed.port
        self.context, self.max_idle = context, max_idle
        self.idle = []
        self.lock = threading.Lock()

    def request(self, path, headers):
        with self.lock:
            connection = self.idle.pop() if self.idle else None
        if connection is None:
            connection = http.client.HTTPSConnection(self.host, self.port, context=self.context, timeout=120)
        try:
            connection.request('GET', path, headers=headers)
            response = connection.getresponse()
            if response.status != 200:
                # No error body or redirect target is trusted or followed.
                code, reason, result_headers = response.status, response.reason, response.headers
                response.close()
                if 300 <= code < 400:
                    raise TransferError("Redirection HTTPS refusée ; vérifiez l’adresse de l’émetteur.")
                raise HTTPError(path, code, reason, result_headers, None)
            return Response(self, connection, response)
        except OSError as exc:
            connection.close()
            if isinstance(exc, HTTPError):
                raise
            raise URLError(exc) from exc
        except BaseException:
            connection.close()
            raise

    def __del__(self):
        if hasattr(self, "lock"):
            self.close()

    def release(self, connection, reusable):
        with self.lock:
            if reusable and len(self.idle) < self.max_idle:
                self.idle.append(connection)
                return
        connection.close()

    def close(self):
        with self.lock:
            connections, self.idle = self.idle, []
        for connection in connections:
            connection.close()
