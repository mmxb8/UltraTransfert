"""Un partage explicite, une seule interface IPv4, arrêt des connexions suivies."""
import hmac
import ipaddress
import threading
from urllib.parse import urlsplit

from .engine import LocalSource, TransferError, signature, is_link, check_cancel
from .invitation import read_invitation, certificate_fingerprint
from .network import make_server, read_token


class ShareSession:
    def __init__(self):
        self._server = None
        self._thread = None
        self._lock = threading.Lock()

    @property
    def active(self):
        return self._server is not None

    def start(self, source_path, prepared, *, cancel=None, compression="auto"):
        with self._lock:
            check_cancel(cancel)
            if self.active:
                raise TransferError("Un partage est déjà ouvert. Arrêtez-le avant d'en créer un autre.")
            configuration_paths = [prepared.invitation_path, *(prepared.directory/n for n in ("server-cert.pem", "server-key.pem", "token.txt"))]
            snapshots = {path: signature(path.lstat()) for path in configuration_paths}
            def configuration_unchanged():
                check_cancel(cancel)
                for path, expected in snapshots.items():
                    current = path.lstat()
                    if is_link(current) or signature(current) != expected:
                        raise TransferError("La connexion a changé pendant le démarrage ; rechargez-la avant de partager.")
            from .share_restore import load_prepared_share
            checked = load_prepared_share(prepared.directory, invitation_path=prepared.invitation_path)
            if checked.url != prepared.url or checked.certificate_sha256 != prepared.certificate_sha256:
                raise TransferError("La connexion a changé depuis sa sélection. Rechargez-la avant de partager.")
            configuration_unchanged()
            profile = read_invitation(prepared.invitation_path)
            if profile.url != prepared.url:
                raise TransferError("L'invitation ne correspond plus à la préparation choisie.")
            parsed = urlsplit(profile.url)
            host = parsed.hostname
            if host == "localhost":
                bind = "127.0.0.1"
            else:
                try:
                    address = ipaddress.IPv4Address(host)
                except ipaddress.AddressValueError:
                    raise TransferError("Ce parcours de partage attend une adresse IPv4 précise de ce poste ou localhost.") from None
                if address.is_unspecified or address.is_multicast or address.is_reserved:
                    raise TransferError("Adresse d'écoute générale ou réservée refusée.")
                bind = str(address)
            cert, key, tokenfile = (prepared.directory/n for n in ("server-cert.pem", "server-key.pem", "token.txt"))
            token = read_token(tokenfile)
            if (not hmac.compare_digest(token, profile.token)
                    or certificate_fingerprint(cert.read_text(encoding="ascii")) != profile.certificate_sha256):
                raise TransferError("Certificat ou accès différent de l'invitation. Préparez une nouvelle connexion.")
            server = make_server(LocalSource(source_path, cancel=cancel), (bind, parsed.port), cert, key, token, compression, before_bind=configuration_unchanged, cancel=cancel)
            thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.1), daemon=True)
            try:
                check_cancel(cancel)
                thread.start()
            except BaseException:
                server.server_close()
                raise
            self._server, self._thread = server, thread
            return profile.url

    def stop(self):
        with self._lock:
            if not self.active:
                return
            server, thread = self._server, self._thread
            server.close_connections()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            if thread.is_alive():
                raise TransferError("L'arrêt de l'écoute n'est pas confirmé. Conservez cette fenêtre ouverte.")
            self._server = self._thread = None
