import argparse
from dataclasses import asdict
import json
from pathlib import Path
import signal
import sys
import threading
import time

from . import __version__
from .engine import LocalSource, Options, Transfer, TransferError
from .network import RemoteSource, make_server, read_token
from .delta import DeltaSource


def main():
    parser = argparse.ArgumentParser(description="UltraTransfert : copie contrôlée par SHA-256, sans écrasement.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("copy", "pull"):
        cmd = sub.add_parser(name)
        cmd.add_argument("source")
        cmd.add_argument("destination")
        cmd.add_argument("--workers", type=int, default=0, help="0 = auto, sinon 1–32")
        cmd.add_argument("--buffer-mib", type=int, default=1)
        cmd.add_argument("--limit-mb-s", type=float, default=0, help="Mo/s de contenu logique, total des fichiers ; 0 = sans limite")
        cmd.add_argument("--native", help="Helper natif optionnel (mesurer avant utilisation)")
        if name == "pull":
            cmd.add_argument("--reuse-from", help="Ancienne copie locale, utilisée en lecture seule (serveur --delta)")
            cmd.add_argument("--ca", required=True, help="Certificat de confiance, nom d'hôte vérifié")
            cmd.add_argument("--token-file", required=True)
            cmd.add_argument("--compression", choices=["none", "gzip", "auto", "ultra", "predictive"], default="auto", help="ultra = blocs adaptatifs expérimentaux")
    serve = sub.add_parser("serve")
    serve.add_argument("source")
    serve.add_argument("--bind", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8443)
    serve.add_argument("--cert", required=True)
    serve.add_argument("--key", required=True)
    serve.add_argument("--token-file", required=True)
    serve.add_argument("--compression", choices=["none", "gzip", "auto", "ultra", "predictive"], default="auto", help="ultra = blocs adaptatifs expérimentaux")
    serve.add_argument("--link-mbps", type=float, default=100, help="Débit estimé utilisé par le sélecteur expérimental")
    serve.add_argument("--selection-pruning", action="store_true", help="Essai facultatif d'élagage des candidats (compression ultra uniquement, désactivé par défaut)")
    serve.add_argument("--delta", action="store_true", help="Publier aussi les empreintes des blocs de 4 Mio")
    prepare = sub.add_parser("prepare", help="Créer automatiquement certificat, clé, jeton et invitation sans service")
    prepare.add_argument("url")
    prepare.add_argument("directory", help="Nouveau dossier privé, hors des données à partager")
    invite = sub.add_parser("invite", help="Exporter une invitation secrète, sans ouvrir de service")
    invite.add_argument("url")
    invite.add_argument("output")
    invite.add_argument("--cert", required=True, help="Certificat public PEM existant")
    invite.add_argument("--token-file", required=True)
    sub.add_parser("gui")
    args = parser.parse_args()
    if args.command == "gui":
        from .gui import launch
        launch()
        return 0
    try:
        if args.command == "prepare":
            from .share_setup import prepare_share
            prepared = prepare_share(args.url, args.directory)
            print("Préparation terminée. Aucun service démarré.")
            print("Invitation secrète : "+str(prepared.invitation_path))
            print("Adresse : "+prepared.url)
            print("Empreinte à comparer : "+prepared.certificate_sha256)
            print("Gardez la clé privée et le jeton sur l'émetteur, hors des données à partager.")
            return 0
        if args.command == "invite":
            from .invitation import write_invitation
            invitation = write_invitation(args.url, args.cert, args.token_file, args.output)
            print("Invitation créée. Fichier secret à transmettre par un canal de confiance.")
            print("Adresse : "+invitation.url)
            print("Empreinte du certificat à comparer hors bande : "+invitation.certificate_sha256)
            print("Aucun service démarré. Arrêtez le serveur à la fin du partage.")
            return 0
        if args.command == "serve":
            server = make_server(LocalSource(args.source), (args.bind, args.port), args.cert, args.key, read_token(args.token_file), args.compression, 4*1024*1024 if args.delta else None, args.link_mbps, selection_pruning=args.selection_pruning)
            print(f"Source en lecture seule : HTTPS {args.bind}:{server.server_port}. Ctrl+C pour arrêter.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        source = LocalSource(args.source) if args.command == "copy" else RemoteSource(args.source, read_token(args.token_file), args.ca, args.compression)
        cancel = threading.Event()
        signal.signal(signal.SIGINT, lambda *unused: cancel.set())
        started = time.monotonic()
        if args.command == "pull" and args.reuse_from:
            source = DeltaSource(source, args.reuse_from, cancel)
        last = [0.0]

        def progress(n, total):
            now = time.monotonic()
            if now-last[0] < 0.5:
                return
            last[0] = now
            elapsed = now-started
            speed = n/max(elapsed, 0.001)
            eta = (total-n)/speed if speed else 0
            print(f"\rCopie {n:,}/{total:,} octets | {speed/1e6:.1f} Mo/s | reste estimé {eta:.0f} s (vérification finale ensuite)", file=sys.stderr, end="", flush=True)

        result = Transfer(source, args.destination, Options(args.workers, args.buffer_mib*1024*1024, args.native, max_bytes_per_second=args.limit_mb_s*1e6), progress, cancel).run()
        print(file=sys.stderr)
        output = asdict(result)
        if isinstance(source, DeltaSource):
            output["delta"] = source.statistics()
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1 if result.errors else 0
    except (TransferError, OSError, ValueError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
