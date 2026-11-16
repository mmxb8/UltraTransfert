"""Préparation locale, sans écoute réseau ni modification du magasin TLS système."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from .engine import TransferError
from .invitation import origin, write_invitation


@dataclass(frozen=True)
class PreparedShare:
    directory: Path
    invitation_path: Path
    url: str
    certificate_sha256: str


def _protect_windows(directory):
    """Restreindre le nouveau dossier avant d'y écrire le moindre secret."""
    system = Path(os.environ["SystemRoot"])/"System32"
    identity = subprocess.run([str(system/"whoami.exe"), "/user", "/fo", "csv", "/nh"],
                              check=True, capture_output=True, text=True, errors="replace", timeout=10)
    matches = re.findall(r"S-1-\d+(?:-\d+)+", identity.stdout)
    if len(matches) != 1:
        raise TransferError("Impossible d'identifier le compte Windows ; aucun secret créé.")
    # Le dossier vient d'être créé : il ne contient aucune autorisation explicite.
    subprocess.run([str(system/"icacls.exe"), str(directory), "/inheritancelevel:r", "/grant:r",
                    f"*{matches[0]}:(OI)(CI)F"], check=True, capture_output=True, timeout=10)


def _write_private(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def prepare_share(url, directory):
    """Créer un dossier neuf de confiance ; ne jamais réutiliser/écraser un état."""
    canonical = origin(url)
    host = urlsplit(canonical).hostname
    try:
        address = ipaddress.ip_address(host)
        if address.is_unspecified or address.is_multicast:
            raise TransferError("Utilisez l'adresse précise du poste, pas une adresse d'écoute générale.")
    except ValueError:
        address = None
        if len(host) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                  for label in host.split('.')):
            raise TransferError("Nom d'hôte DNS invalide pour le certificat.")
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        raise TransferError("Composant de préparation absent. Sous Windows, relancez Installer_Windows.bat ; sinon, installez le complément sharing décrit dans README.md. Aucune clé créée.") from None
    directory = Path(directory).absolute()
    # Les chemins de configuration doivent rester hors des dossiers à partager.
    # Le dossier cible lui-même ne doit exister sous aucune forme, lien compris.
    directory.mkdir(mode=0o700)
    try:
        if sys.platform == "win32":
            try:
                _protect_windows(directory)
            except (OSError, subprocess.SubprocessError, KeyError) as exc:
                raise TransferError("Protection du dossier Windows impossible ; préparation annulée sans écrire de secret.") from exc
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        now = datetime.now(timezone.utc)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "UltraTransfert")])
        subject_key_id = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=7))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address) if address else x509.DNSName(host)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(subject_key_id, critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(subject_key_id), critical=False)
            .sign(key, hashes.SHA256()))
        cert_path, key_path, token_path = (directory/n for n in ("server-cert.pem", "server-key.pem", "token.txt"))
        _write_private(cert_path, certificate.public_bytes(serialization.Encoding.PEM))
        _write_private(key_path, key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        _write_private(token_path, secrets.token_urlsafe(48).encode("ascii"))
        invitation_path = directory/"acces.utconnect"
        invitation = write_invitation(canonical, cert_path, token_path, invitation_path)
        return PreparedShare(directory, invitation_path, canonical, invitation.certificate_sha256)
    except BaseException:
        # Seulement le dossier neuf possédé par cette tentative ; jamais un état antérieur.
        shutil.rmtree(directory)
        raise
