"""Produce descriptive tables; keep every unfavorable cell visible."""
import json
from pathlib import Path


def main():
    r=json.loads(Path('reports/bundle-r41-final.json').read_text());rows=r['summary']
    lines=['# Recherche R4.1 — regroupement borné des petits fichiers','',
           '16 novembre 2026. Application et installateur conservés en 0.4.1. Recherche facultative hors du moteur utilisateur.', '',
           '## Transfert HTTPS complet', '',
           'Médianes de cinq répétitions mélangées, processus isolés. La référence directe est la plus rapide réellement mesurée parmi brut (1/4 workers), prédictif, Zstd1 (1/4 workers), Zstd3 et LZMA1 fichier par fichier. Les références groupées sont raw, Zstd1, Zstd3 et LZMA1 ; aucune nouveauté de codec.', '',
           '| Dossier | Mbit/s | Direct le plus rapide | Direct (s) | Groupé auto (s) | Gain vs direct | Meilleur autre groupé (s) | Gain auto vs autre groupé |',
           '|---|---:|---|---:|---:|---:|---:|---:|']
    for name in sorted({x['dataset'] for x in rows}):
        for rate in (50,1000):
            cells=[x for x in rows if x['dataset']==name and x['mbps']==rate]
            direct=min((x for x in cells if x['method'].startswith('files-')),key=lambda x:x['median_seconds'])
            auto=next(x for x in cells if x['method']=='bundle-auto')
            other=min((x for x in cells if x['method'].startswith('bundle-') and x['method']!='bundle-auto'),key=lambda x:x['median_seconds'])
            lines.append(f"| {name} | {rate} | {direct['method']} | {direct['median_seconds']:.6f} | {auto['median_seconds']:.6f} | {100*(1-auto['median_seconds']/direct['median_seconds']):+.1f} % | {other['median_seconds']:.6f} | {100*(1-auto['median_seconds']/other['median_seconds']):+.1f} % |")
    lines += ['', '## CPU, mémoire et volume à 50 Mbit/s', '',
              '| Dossier | Méthode | CPU (s) | RSS pic (Mio) | Octets HTTP avant TLS | Requêtes fichiers |',
              '|---|---|---:|---:|---:|---:|']
    for name in sorted({x['dataset'] for x in rows}):
        cells=[x for x in rows if x['dataset']==name and x['mbps']==50]
        direct=min((x for x in cells if x['method'].startswith('files-')),key=lambda x:x['median_seconds'])
        for x in (direct,next(x for x in cells if x['method']=='bundle-auto')):
            lines.append(f"| {name} | {x['method']} | {x['median_cpu_seconds']:.6f} | {x['median_max_rss_kib']/1024:.2f} | {x['median_http_plaintext_bytes']:.0f} | {x['median_requests']:.0f} |")
    mem=json.loads(Path('reports/bundle-r4-memory.json').read_text())['summary']
    before,after=mem
    lines += ['', '## Optimisation de la restitution isolée', '',
              f"32 Mio, 512 fichiers pseudoaléatoires distincts, sept répétitions par révision. Pic Python : {before['peak_python_bytes']/1048576:.2f} → {after['peak_python_bytes']/1048576:.2f} Mio ({100*(1-after['peak_python_bytes']/before['peak_python_bytes']):.1f} % de baisse). RSS : {before['max_rss_kib']/1024:.2f} → {after['max_rss_kib']/1024:.2f} Mio ({100*(1-after['max_rss_kib']/before['max_rss_kib']):.1f} % de baisse).",
              f"Durée instrumentée tracemalloc : {before['seconds']:.6f} → {after['seconds']:.6f} s. Ce microbanc décode/hache/indexe, sans transfert ni écritures destination ; ne pas présenter ce gain comme un gain réseau.", '',
              '## Validations et limites', '',
              '- 285 tests Linux réussis avec cryptography 50.0.2 et helper C++ compilé ; 14 tests nouveaux de regroupement, dont TLS authentifié avec refus 401, interruption/reprise du conteneur et restitution par le moteur.',
              '- Corruption/troncature/trailing data, limites avant allocation, chemins dangereux, collisions, liens, source modifiée, non-écrasement, arrêt/reprise et espace insuffisant simulé couverts. Toutes les copies finales sont comparées par inventaire et SHA-256 indépendants.',
              '- Débit applicatif par connexion ; les références directes à quatre workers peuvent atteindre quatre fois le débit agrégé du groupé à un worker. Cela les avantage, sans simuler une capacité de lien physique commune.',
              '- Préparation groupée, métadonnées/recettes, fsync du conteneur, inventaire source et SHA-256/TLS, copie réseau avec contrôles moteur, décompression et contrôle de chaque fichier, restitution avec écritures/fsync et vérification finale inclus dans le temps complet.',
              '- Création des fixtures/certificats, imports, arrêt serveur et contrôle indépendant supplémentaire exclus des temps. CPU émetteur+récepteur ; RSS processus isolé incluant imports et espaces natifs. Caches chauds, boucle Linux, sans RTT/pertes, machines distinctes, USB physique, Windows ou RDP.',
              '- stdlib_real contient des fichiers réellement installés localement, non tronqués, de 64 Kio maximum. Les autres dossiers sont synthétiques. mixed_heldout utilise une graine et une structure distinctes, sans ajustement des réglages après son évaluation. Aucun corpus externe public téléchargé.',
              '- Auto compare uniquement brut et Zstd1 sur le groupe entier ; il évite une expansion en volume mais paie toujours un essai de compression. Il ne bat pas systématiquement la meilleure recette groupée. LZMA est la bibliothèque Python/XZ niveau 1, pas 7-Zip ; pas de Blosc2/TurboPFor/SPDP mesurés.',
              '- Conteneur de recherche borné : fichiers ≤64 Kio, groupes ≤1 Mio dans le banc (limite format 4 Mio), ≤256 fichiers/groupe, ≤4096 entrées et ≤64 Mio au total. La restitution reste en mémoire ; pas de diffusion en continu pour gros dossiers.',
              '- La reprise HTTPS est celle du fichier conteneur ; la restitution peut ensuite reprendre par fichier. Aucun journal unique, manifeste signé indépendant du transport, reprise de groupe à groupe ou canal natif RDP livré. Pas de négociation de ce conteneur dans le protocole utilisateur.',
              '- Le groupement et la compression solide sont des techniques connues. Ces mesures ne démontrent ni codec révolutionnaire ni supériorité générale face aux outils de transfert/archivage existants.',
              '- Première suite système : deux échecs avec cryptography 50.0.0 ; suite finale intégrale réussie avec 50.0.2 sans réduire les attentes. Le banc initial est exploratoire seulement : une partie chevauche les tests et une révision de lecture ; aucun gain retenu à partir de cette campagne.',
              '- L’installateur 0.4.1 existant est conservé octet pour octet. Bêta non signée, aucune installation Windows/RDP réelle ni scan antivirus supplémentaire.', '',
              '## Reprise', '',
              'Conserver R4.1 comme expérience. Prochain cycle : comparer au groupement standard tar/ZIP/7-Zip avec les mêmes garanties, puis développer un index de groupes authentifié/fragmenté et une restitution en flux borné avant toute intégration. Mesurer latence et réseau entre hôtes ; la reprise par fichiers individuels doit rester avantageuse lorsque peu de fichiers manquent. Ne pas intégrer uniquement sur la base du gain face au transfert fichier par fichier.', '',
              'Reproduction : `python3 -m research.benchmark_bundle_r4 --rounds 5` puis `python3 -m research.benchmark_bundle_memory` et `python3 -m research.summarize_bundle_r4`. Les JSON conservent toutes les répétitions, bornes, empreintes et cas défavorables.']
    archive_path=Path('reports/bundle-r41-archives.json')
    if archive_path.exists():
        ar=json.loads(archive_path.read_text())
        lines += ['', '## Références standard tar et ZIP, campagne distincte', '',
                  'Cinq répétitions par méthode ; auto est remesuré dans la même campagne. tar PAX + Zstd1/Zstd3/LZMA1 et ZIP Deflate1, préparation source/SHA-256, création/fsync archive, transfert TLS vérifié, extraction dans un dossier neuf, fsync des fichiers, inventaire et SHA-256 de sortie inclus. Les helpers d’archive n’acceptent que les fixtures de confiance du banc. Aucune conclusion de sécurité sur un importateur de fichiers arbitraires.', '',
                  '| Dossier | Mbit/s | Meilleure référence standard | Standard (s) | Groupé auto (s) | Gain auto vs standard |',
                  '|---|---:|---|---:|---:|---:|']
        for name in sorted({x['dataset'] for x in ar['summary']}):
            for rate in (50,1000):
                cells=[x for x in ar['summary'] if x['dataset']==name and x['mbps']==rate]
                auto=next(x for x in cells if x['method']=='bundle-auto')
                best=min((x for x in cells if x['method']!='bundle-auto'),key=lambda x:x['median_seconds'])
                lines.append(f"| {name} | {rate} | {best['method']} | {best['median_seconds']:.6f} | {auto['median_seconds']:.6f} | {100*(1-auto['median_seconds']/best['median_seconds']):+.1f} % |")
        lines += ['', 'Les références standard restituent dans un dossier neuf, sans journal de reprise ni publication temporaire par fichier du moteur. Leur contrôle final vérifie les octets et l’inventaire avant réussite, mais leurs garanties de reprise/publication ne sont pas équivalentes. Les différences de coût doivent rester visibles ; aucun contrôle du moteur candidat n’a été supprimé pour gagner.', '', 'Décision : les gains face au fichier par fichier ne suffisent pas à promouvoir le conteneur maison. Garder les résultats standard favorables comme défavorables ; privilégier une intégration seulement après avantage face à ces références et reprise logique efficace. Les références standard ont un format, une granularité et des contrôles internes différents ; les contrôles de sortie et coûts ajoutés sont explicités ci-dessus.']
    Path('reports/bundle-r4-summary.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
