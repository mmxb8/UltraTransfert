"""Contrôle du contenu installé ; une empreinte ne remplace pas une signature."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify_payload(root):
    root = Path(root).resolve()
    manifest = root/'payload-manifest.json'
    if manifest.is_symlink() or manifest.stat().st_size > 4*1024*1024:
        raise ValueError('Manifeste installé invalide.')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    files = data['files']
    if not isinstance(files, dict) or not files:
        raise ValueError('Inventaire installé vide.')
    for name, expected in files.items():
        path = PurePosixPath(name)
        if (not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                or not isinstance(expected, str) or len(expected) != 64):
            raise ValueError('Chemin ou empreinte invalide dans le manifeste.')
        local = root.joinpath(*path.parts)
        # Refuser également un parent remplacé par un lien/jonction.
        for part in [local, *list(local.parents)[:len(path.parts)-1]]:
            if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
                raise ValueError('Lien ou jonction dans le contenu installé.')
        if not local.resolve().is_relative_to(root):
            raise ValueError('Chemin hors installation.')
        hasher = hashlib.sha256()
        with local.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024), b''):
                hasher.update(block)
        if hasher.hexdigest() != expected:
            raise ValueError('Fichier installé absent ou différent : '+name)
    return len(files)
