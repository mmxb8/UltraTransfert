"""Build the R2 report from retained individual observations."""
import json
from pathlib import Path


def main():
    files=['budget-r2-https','budget-r22-https','budget-validation-https']
    https=[json.loads(Path('reports',f+'.json').read_text()) for f in files]
    cpus=[json.loads(Path('reports',f+'.json').read_text()) for f in
          ('budget-r2-cpu','budget-r22-cpu','budget-validation-cpu')]
    assert https[0]['dataset_sha256']==https[1]['dataset_sha256']
    lines=['# Bilan R2.2 — sélection bornée de compression', '',
           '16 novembre 2026. Recherche seulement ; moteur et installateur 0.4.0 inchangés.', '',
           f'{sum(len(r["raw"]) for r in https)} copies HTTPS vérifiées au total : '
           f'{len(https[0]["raw"])} en R2.1, {len(https[1]["raw"])} en R2.2 et '
           f'{len(https[2]["raw"])} sur cinq nouveaux jeux indépendants du réglage. '
           f'{sum(len(r["raw"]) for r in cpus)} mesures CPU avec restitution exacte. '
           'Cinq répétitions par configuration, ordre mélangé. Médianes descriptives, '
           'pas de preuve de significativité statistique pour les petits écarts.', '',
           'Le sélecteur R2.2 est conservé comme candidat expérimental. Il améliore '
           'plusieurs cas face à R1, mais reste souvent plus lent que le brut HTTPS '
           'ou une recette connue. Aucun remplacement général, codec nouveau ou '
           'supériorité générale démontré.', '']
    criteria=[]
    for title,report in [('Jeux de réglage R1 — R2.2',https[1]),('Validation indépendante — R2.2',https[2])]:
        lines += ['## '+title, '',
          '| Données | Mbit/s | R1 (s) | R2.2 (s) | Gain vs R1 | Meilleure référence mesurée | Référence (s) | Gain vs référence |',
          '|---|---:|---:|---:|---:|---|---:|---:|']
        for name in report['dataset_sha256']:
            for rate in (50,1000):
                rows={r['method']:r for r in report['summary'] if r['dataset']==name and r['link_mbps']==rate}
                old,new=rows['predictive'],rows['budget_R2']
                ref=min((r for m,r in rows.items() if m not in ('predictive','budget_R2')),key=lambda r:r['median_total_seconds'])
                a,b,c=(r['median_total_seconds'] for r in (old,new,ref))
                gain=100*(1-b/a);gain_ref=100*(1-b/c)
                if report is https[2]:criteria.append(gain>=-5)
                lines.append(f'| {name} | {rate} | {a:.6f} | {b:.6f} | {gain:+.1f} % | {ref["method"]} | {c:.6f} | {gain_ref:+.1f} % |')
        lines += ['']
    lines += ['## Analyse et critères', '',
              'Le gain spécialisé du signal R1 à 50 Mbit/s reste supérieur au seuil de 10 % '
              'face à la meilleure référence mesurée. À 1000 Mbit/s, son gain face à R1 '
              'dépasse également le seuil visé de 10 %, mais le brut normal reste meilleur.', '',
              f'Validation indépendante : {sum(criteria)}/{len(criteria)} combinaisons respectent '
              'la cible de ne pas régresser de plus de 5 % face à R1. Cela ne signifie pas '
              'que R2.2 bat les références : le nouveau signal bruité à 50 Mbit/s reste '
              'moins bon que Zstd3+shuffle4. Le gzip à haut débit reste défavorable.', '',
              'R2.1 avait régressé sur JSON à 1000 Mbit/s ; l’échantillon plus grand '
              'corrige ce choix en R2.2. Les deux campagnes défavorables et favorables '
              'restent intégralement conservées. Le coût de framing/vérification UTCP1 '
              'subsiste même lorsque son sélecteur choisit le brut ; éviter uniquement '
              'la recherche ne suffit donc pas à rejoindre le HTTPS brut normal.', '',
              '## CPU et mémoire sur les jeux indépendants à 50 Mbit/s', '',
              '| Données | Méthode | CPU encodage + reconstruction (ms) | Pic tracé Python (Mio) |',
              '|---|---|---:|---:|']
    cpu=cpus[2]
    for name in cpu['dataset_sha256']:
        for method in ('predictive','budget_R2'):
            r=next(r for r in cpu['summary'] if r['dataset']==name and r['method']==method and r['link_mbps']==50)
            mem=next(r for r in cpu['memory'] if r['dataset']==name and r['method']==method)
            lines.append(f'| {name} | {method} | {r["median_cpu_seconds"]*1000:.3f} | {mem["python_traced_peak_bytes"]/2**20:.3f} |')
    lines += ['', 'Le temps CPU HTTPS des deux extrémités figure aussi dans les JSON. '
              'Le pic tracé exclut les espaces natifs et ne mesure pas la RSS totale.', '',
              '## Validation et limites', '',
              'Voir reports/budget-r2-full-tests.txt pour la suite complète et '
              'reports/budget-r2-build.log pour compilation Python/C++ Linux. '
              'Sept nouveaux tests couvrent budget rapide, recettes autorisées, tailles '
              'arbitraires, changement de contenu, recherche périodique, corruption et '
              'HTTPS avec interruption/reprise, Unicode, vides et plage non alignée.', '',
              'Brut, Zstd1/3 avec/sans permutation, LZMA/XZ stdlib et Blosc1 '
              'font partie des références CPU. Le banc HTTPS retient brut, version publiée '
              'et référence choisie par le banc CPU pour chaque jeu/débit. Ce n’est '
              'pas une comparaison exhaustive des codecs. Pas de Blosc2, TurboPFor ou SPDP.', '',
              'Boucle TLS locale Linux, débit applicatif plafonné, caches chauds, '
              'un worker fichier, même processeur aux deux extrémités. Préparation source '
              'et SHA-256, TLS, sélection, compression, transport, reconstruction, '
              'écriture/fsync et contrôles moteur inclus. Création des corpus/certificat, '
              'arrêt du serveur et hash indépendant supplémentaire exclus. Aucun test '
              'Windows/RDP, réseau distant, disque USB ou antivirus réel.', '',
              'Les trois fichiers réels indépendants proviennent de cette installation '
              'locale ; aucun corpus externe public n’a été téléchargé. Empreintes dans '
              'les JSON. Les métadonnées de compression sont comptées ; aucun dictionnaire '
              'préentraîné ni recette gratuite. Pas de modification du QR ou des dons.', '',
              '## Reprise', '',
              '1. Mesurer sur corpus externes et hôtes distincts, avec RSS native et codecs spécialisés.',
              '2. Séparer coût de framing brut, hachage redondant et transport ; définir une négociation explicite avant un repli HTTP brut par fichier.',
              '3. Mesurer la pénalité de retard (jusqu’à 15 blocs) après passage brut → compressible, puis les mélanges et nombreux petits fichiers.',
              '4. Tester le véritable installateur et les lecteurs redirigés sur Windows ; canal natif RDP toujours absent.', '',
              'Reproduction et hypothèses : RECHERCHE_BUDGET_R2.md. Aucun réglage n’a '
              'été changé après ouverture des résultats de validation indépendante.']
    Path('reports/budget-r2-summary.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
