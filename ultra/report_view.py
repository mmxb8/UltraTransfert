"""Bilan borné en mémoire : ne jamais déduire une réussite d'un ancien fichier."""
import math
from pathlib import Path

from .engine import STATE

COUNTS=('files','directories','bytes','copied','reused','resumed_bytes')


def capture_result(result):
    # Pas de copie de la table d'empreintes, qui peut contenir des millions de noms.
    data={name:getattr(result,name) for name in COUNTS}
    data.update(seconds=result.seconds,max_bytes_per_second=result.max_bytes_per_second,
                verified_files=len(result.hashes),error_count=len(result.errors))
    return data


def volume(size):
    return f'{size:,} octets'.replace(',',' ') if size<1000000 else f'{size/1e6:.2f} Mo'.replace('.',',')


def render_report(data,kind,destination,message=''):
    """Données du moteur courant seulement ; aucun accès au système de fichiers."""
    destination=str(destination or 'Destination non renseignée')
    valid=isinstance(data,dict)
    if valid:
        valid=all(type(data.get(k)) is int and data[k]>=0 for k in (*COUNTS,'verified_files','error_count'))
        valid=valid and all(type(data.get(k)) in (int,float) and math.isfinite(data[k]) and data[k]>=0 for k in ('seconds','max_bytes_per_second'))
        valid=valid and data['copied']+data['reused']==data['verified_files']<=data['files']
    complete=valid and kind=='done' and data['error_count']==0 and data['verified_files']==data['files']
    if complete:
        title='Copie terminée et vérifiée'
    elif kind=='stopped':
        title='Copie interrompue'
    elif kind=='error':
        title='Copie non confirmée'
    else:
        title='Résultat non confirmé'
    lines=[title,'',f'Destination : {destination}','Bilan de cette tentative à sa fin ; aucune nouvelle vérification à l’ouverture.','']
    if valid:
        lines.extend([f"Fichiers inventoriés : {data['files']}",f"Dossiers : {data['directories']}",
                      f"Volume inventorié : {volume(data['bytes'])}",f"Fichiers copiés : {data['copied']}",
                      f"Fichiers déjà présents et identiques : {data['reused']}",
                      f"Fichiers contrôlés pendant la copie : {data['verified_files']}",
                      f"Données reprises pour les fichiers achevés : {volume(data['resumed_bytes'])}",
                      f"Copie et vérifications : {data['seconds']:.2f} s (hors préparation de la source)"])
        if data['max_bytes_per_second']:
            lines.append(f"Limite choisie : {data['max_bytes_per_second']/1e6:g} Mo/s de contenu logique")
    else:
        lines.append('Aucun bilan complet du moteur pour cette tentative. Un ancien fichier sur disque ne confirme pas sa réussite.')
    if not complete:
        detail=str(message)
        if len(detail)>4000:detail=detail[:2500]+'\n… Détails abrégés …\n'+detail[-1000:]
        lines.extend(['',detail or 'Conservez les données et vérifiez le dernier message avant de reprendre.'])
    if kind=='stopped':
        lines.append('Pour reprendre : garder les mêmes dossiers et cliquer sur Reprendre. Ne pas supprimer les données partielles.')
    lines.extend(['','Source conservée. Les ACL, flux NTFS alternatifs et attributs étendus ne sont pas copiés.',
                  'Emplacement habituel du rapport technique (si enregistré) :',
                  str(Path(destination)/STATE/'last-result.json')])
    return title,'\n'.join(lines)
