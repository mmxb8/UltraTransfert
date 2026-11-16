"""Recharger une connexion privée sans socket ni ouverture de partage."""
import hmac
import os
from pathlib import Path
import ssl
import stat
from urllib.parse import urlsplit

from .engine import TransferError, is_link, signature
from .invitation import LIMIT, parse_invitation, certificate_fingerprint
from .share_setup import PreparedShare


def _read_file(path, maximum, secret=True):
    before = path.lstat()
    if is_link(before) or not stat.S_ISREG(before.st_mode):
        raise TransferError("Fichier de connexion lié ou non ordinaire refusé : "+path.name)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        actual = os.fstat(stream.fileno())
        if signature(before) != signature(actual):
            raise TransferError("Fichier de connexion remplacé pendant sa lecture.")
        if os.name != "nt" and secret and actual.st_mode & 0o077:
            raise TransferError("Accès trop larges au fichier privé : "+path.name+". Préparez une nouvelle connexion dans un dossier personnel.")
        if actual.st_size > maximum:
            raise TransferError("Fichier de connexion trop volumineux : "+path.name)
        data = stream.read(maximum+1)
        if len(data) > maximum or signature(os.fstat(stream.fileno())) != signature(actual):
            raise TransferError("Fichier de connexion modifié ou trop volumineux.")
    return data, signature(actual)


def _verify_tls(pem, cert_path, key_path, hostname):
    """Négociation TLS en mémoire : vérifie identité, dates et clé sans réseau."""
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.minimum_version = ssl.TLSVersion.TLSv1_2
    # Le callback explicite interdit une demande interactive de mot de passe.
    server_context.load_cert_chain(cert_path, key_path, password=lambda: "")
    client_context = ssl.create_default_context(cadata=pem)
    client_context.minimum_version = ssl.TLSVersion.TLSv1_2
    client_in, client_out, server_in, server_out = [ssl.MemoryBIO() for unused in range(4)]
    client = client_context.wrap_bio(client_in, client_out, server_hostname=hostname)
    server = server_context.wrap_bio(server_in, server_out, server_side=True)
    complete = [False, False]
    transferred = 0
    for unused in range(32):
        for index, peer in enumerate((client, server)):
            if not complete[index]:
                try:
                    peer.do_handshake()
                    complete[index] = True
                except (ssl.SSLWantReadError, ssl.SSLWantWriteError):
                    pass
        for outgoing, incoming in ((client_out, server_in), (server_out, client_in)):
            if outgoing.pending:
                data = outgoing.read(65536)
                transferred += len(data)
                if transferred > 512*1024:
                    raise TransferError("Contrôle TLS local trop volumineux.")
                incoming.write(data)
        if all(complete):
            return
    raise TransferError("Le contrôle TLS local n'a pas abouti.")


def load_prepared_share(directory, *, invitation_path=None):
    directory = Path(directory).absolute()
    root_stat = directory.lstat()
    if is_link(root_stat) or not stat.S_ISDIR(root_stat.st_mode):
        raise TransferError("Choisissez un dossier de connexion réel, sans lien ni jonction.")
    if os.name != "nt" and root_stat.st_mode & 0o077:
        raise TransferError("Le dossier de connexion n'est pas privé. Préparez une nouvelle connexion dans un dossier personnel.")
    paths = {"certificate": directory/"server-cert.pem", "key": directory/"server-key.pem",
             "token": directory/"token.txt", "invitation": Path(invitation_path) if invitation_path is not None else directory/"acces.utconnect"}
    limits = {"certificate": 16384, "key": 16384, "token": 514, "invitation": LIMIT}
    snapshots = {name: _read_file(path, limits[name], name != "certificate") for name, path in paths.items()}
    try:
        key_header = snapshots["key"][0].upper()
        if (b"-----BEGIN ENCRYPTED PRIVATE KEY-----" in key_header
                or (b"PROC-TYPE:" in key_header and b"ENCRYPTED" in key_header)):
            raise TransferError("Clé TLS chiffrée par mot de passe non prise en charge. Utilisez la connexion d'origine ou créez-en une nouvelle.")
        profile = parse_invitation(snapshots["invitation"][0])
        pem = snapshots["certificate"][0].decode("ascii")
        token = snapshots["token"][0].decode("ascii").strip()
        if (certificate_fingerprint(pem) != profile.certificate_sha256
                or not hmac.compare_digest(token, profile.token)):
            raise TransferError("Fichiers de connexion différents : certificat, jeton et invitation ne correspondent pas. Rechargez le dossier complet de l'émetteur.")
        _verify_tls(pem, paths["certificate"], paths["key"], urlsplit(profile.url).hostname)
    except (ssl.SSLError, UnicodeError, ValueError):
        raise TransferError("Connexion TLS sauvegardée invalide ou expirée. Vérifiez l'horloge et les fichiers, ou préparez une nouvelle connexion ; les fichiers existants sont conservés.") from None
    for name, path in paths.items():
        current = path.lstat()
        if is_link(current) or signature(current) != snapshots[name][1]:
            raise TransferError("La connexion a changé pendant sa validation ; rechargez-la.")
    after_root = directory.lstat()
    if is_link(after_root) or (after_root.st_dev, after_root.st_ino, after_root.st_mode) != (root_stat.st_dev, root_stat.st_ino, root_stat.st_mode):
        raise TransferError("Le dossier de connexion a changé pendant sa validation.")
    return PreparedShare(directory, paths["invitation"], profile.url, profile.certificate_sha256)
