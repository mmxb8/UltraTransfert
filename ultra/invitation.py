"""Invitation secrète hors bande ; la confiance doit être confirmée par le receveur."""
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import tempfile
from urllib.parse import urlsplit

from .engine import TransferError, install_no_replace

LIMIT = 32768
FORMAT = "ultratransfert-invitation-1"


def origin(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) <= 32 for c in url) or any(c in url for c in "\\%"):
        raise TransferError("Adresse HTTPS d'invitation invalide.")
    try:
        parsed = urlsplit(url)
        port = parsed.port
        host = parsed.hostname
    except ValueError:
        raise TransferError("Adresse HTTPS d'invitation invalide.") from None
    if (parsed.scheme != "https" or not host or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or (port is not None and not 1 <= port <= 65535)):
        raise TransferError("L'invitation exige une origine HTTPS sans chemin ni identifiants.")
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise TransferError("Nom d'hôte d'invitation invalide.") from None
    if not re.fullmatch(r"[a-z0-9.:-]+", host):
        raise TransferError("Nom d'hôte d'invitation invalide.")
    host = f"[{host}]" if ":" in host else host
    return f"https://{host}:{port or 443}"


def certificate_fingerprint(pem):
    if not isinstance(pem, str) or len(pem) > 16384 or not re.fullmatch(
            r"-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*", pem):
        raise TransferError("L'invitation doit contenir un seul certificat public PEM, sans clé privée.")
    try:
        context = ssl.create_default_context(cadata=pem)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        der = ssl.PEM_cert_to_DER_cert(pem)
    except (ValueError, ssl.SSLError):
        raise TransferError("Certificat public d'invitation invalide.") from None
    return hashlib.sha256(der).hexdigest()


@dataclass(frozen=True)
class Invitation:
    url: str
    certificate_pem: str = field(repr=False)
    token: str = field(repr=False)
    certificate_sha256: str

    def remote_source(self, compression="auto"):
        from .network import RemoteSource
        return RemoteSource(self.url, self.token, None, compression, cadata=self.certificate_pem)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TransferError("Champ dupliqué dans l'invitation.")
        result[key] = value
    return result


def parse_invitation(raw):
    if not isinstance(raw, bytes) or len(raw) > LIMIT:
        raise TransferError("Invitation trop volumineuse (maximum 32 Kio).")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    except (ValueError, UnicodeError, RecursionError):
        raise TransferError("Fichier d'invitation illisible.") from None
    keys = {"format", "url", "certificate_pem", "token", "certificate_sha256"}
    if not isinstance(data, dict) or set(data) != keys or data["format"] != FORMAT:
        raise TransferError("Format d'invitation inconnu ou incomplet.")
    token = data["token"]
    if not isinstance(token, str) or not 32 <= len(token) <= 512 or any(not 33 <= ord(c) <= 126 for c in token):
        raise TransferError("Jeton d'invitation invalide.")
    url = origin(data["url"])
    fingerprint = certificate_fingerprint(data["certificate_pem"])
    if fingerprint != data["certificate_sha256"]:
        raise TransferError("L'empreinte de l'invitation ne correspond pas au certificat.")
    return Invitation(url, data["certificate_pem"], token, fingerprint)


def read_invitation(path):
    with open(path, "rb") as stream:
        return parse_invitation(stream.read(LIMIT+1))


def write_invitation(url, certfile, tokenfile, output):
    with open(certfile, "rb") as stream:
        pem_bytes = stream.read(16385)
    try:
        pem = pem_bytes.decode("ascii")
    except UnicodeError:
        raise TransferError("Certificat public PEM ASCII requis.") from None
    with open(tokenfile, "rb") as stream:
        token_bytes = stream.read(515)
    if len(token_bytes) > 514:
        raise TransferError("Fichier de jeton trop volumineux.")
    try:
        token = token_bytes.decode("ascii").strip()
    except UnicodeError:
        raise TransferError("Jeton ASCII requis.") from None
    data = {"format": FORMAT, "url": origin(url), "certificate_pem": pem,
            "certificate_sha256": certificate_fingerprint(pem), "token": token}
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    invitation = parse_invitation(raw)
    output = Path(output).absolute()
    fd, pending = tempfile.mkstemp(prefix=".invitation-", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        install_no_replace(pending, output)
    finally:
        Path(pending).unlink(missing_ok=True)
    return invitation
