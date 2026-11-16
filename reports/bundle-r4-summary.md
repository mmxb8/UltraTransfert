# Recherche R4.1 — regroupement borné des petits fichiers

16 novembre 2026. Application et installateur conservés en 0.4.1. Recherche facultative hors du moteur utilisateur.

## Transfert HTTPS complet

Médianes de cinq répétitions mélangées, processus isolés. La référence directe est la plus rapide réellement mesurée parmi brut (1/4 workers), prédictif, Zstd1 (1/4 workers), Zstd3 et LZMA1 fichier par fichier. Les références groupées sont raw, Zstd1, Zstd3 et LZMA1 ; aucune nouveauté de codec.

| Dossier | Mbit/s | Direct le plus rapide | Direct (s) | Groupé auto (s) | Gain vs direct | Meilleur autre groupé (s) | Gain auto vs autre groupé |
|---|---:|---|---:|---:|---:|---:|---:|
| gzip_noise | 50 | files-raw | 0.195308 | 0.170873 | +12.5 % | 0.162464 | -5.2 % |
| gzip_noise | 1000 | files-raw | 0.146197 | 0.088575 | +39.4 % | 0.082758 | -7.0 % |
| json_related | 50 | files-raw | 0.194466 | 0.084886 | +56.3 % | 0.075502 | -12.4 % |
| json_related | 1000 | files-raw | 0.161476 | 0.081192 | +49.7 % | 0.071352 | -13.8 % |
| mixed_heldout | 50 | files-raw-w4 | 0.397665 | 0.658076 | -65.5 % | 0.652862 | -0.8 % |
| mixed_heldout | 1000 | files-raw | 0.279645 | 0.179720 | +35.7 % | 0.186022 | +3.4 % |
| stdlib_real | 50 | files-raw-w4 | 0.252916 | 0.232327 | +8.1 % | 0.221251 | -5.0 % |
| stdlib_real | 1000 | files-raw | 0.161433 | 0.112262 | +30.5 % | 0.099294 | -13.1 % |

## CPU, mémoire et volume à 50 Mbit/s

| Dossier | Méthode | CPU (s) | RSS pic (Mio) | Octets HTTP avant TLS | Requêtes fichiers |
|---|---|---:|---:|---:|---:|
| gzip_noise | files-raw | 0.144416 | 27.09 | 636993 | 161 |
| gzip_noise | bundle-auto | 0.092784 | 28.86 | 526458 | 1 |
| json_related | files-raw | 0.147640 | 27.07 | 612833 | 161 |
| json_related | bundle-auto | 0.080685 | 27.93 | 33855 | 1 |
| mixed_heldout | files-raw-w4 | 0.415266 | 28.73 | 4898093 | 241 |
| mixed_heldout | bundle-auto | 0.218468 | 36.78 | 3108480 | 1 |
| stdlib_real | files-raw-w4 | 0.273305 | 29.08 | 2725340 | 142 |
| stdlib_real | bundle-auto | 0.112328 | 32.48 | 796875 | 1 |

## Optimisation de la restitution isolée

32 Mio, 512 fichiers pseudoaléatoires distincts, sept répétitions par révision. Pic Python : 64.55 → 40.47 Mio (37.3 % de baisse). RSS : 79.89 → 55.87 Mio (30.1 % de baisse).
Durée instrumentée tracemalloc : 0.156699 → 0.124040 s. Ce microbanc décode/hache/indexe, sans transfert ni écritures destination ; ne pas présenter ce gain comme un gain réseau.

## Validations et limites

- 285 tests Linux réussis avec cryptography 50.0.2 et helper C++ compilé ; 14 tests nouveaux de regroupement, dont TLS authentifié avec refus 401, interruption/reprise du conteneur et restitution par le moteur.
- Corruption/troncature/trailing data, limites avant allocation, chemins dangereux, collisions, liens, source modifiée, non-écrasement, arrêt/reprise et espace insuffisant simulé couverts. Toutes les copies finales sont comparées par inventaire et SHA-256 indépendants.
- Débit applicatif par connexion ; les références directes à quatre workers peuvent atteindre quatre fois le débit agrégé du groupé à un worker. Cela les avantage, sans simuler une capacité de lien physique commune.
- Préparation groupée, métadonnées/recettes, fsync du conteneur, inventaire source et SHA-256/TLS, copie réseau avec contrôles moteur, décompression et contrôle de chaque fichier, restitution avec écritures/fsync et vérification finale inclus dans le temps complet.
- Création des fixtures/certificats, imports, arrêt serveur et contrôle indépendant supplémentaire exclus des temps. CPU émetteur+récepteur ; RSS processus isolé incluant imports et espaces natifs. Caches chauds, boucle Linux, sans RTT/pertes, machines distinctes, USB physique, Windows ou RDP.
- stdlib_real contient des fichiers réellement installés localement, non tronqués, de 64 Kio maximum. Les autres dossiers sont synthétiques. mixed_heldout utilise une graine et une structure distinctes, sans ajustement des réglages après son évaluation. Aucun corpus externe public téléchargé.
- Auto compare uniquement brut et Zstd1 sur le groupe entier ; il évite une expansion en volume mais paie toujours un essai de compression. Il ne bat pas systématiquement la meilleure recette groupée. LZMA est la bibliothèque Python/XZ niveau 1, pas 7-Zip ; pas de Blosc2/TurboPFor/SPDP mesurés.
- Conteneur de recherche borné : fichiers ≤64 Kio, groupes ≤1 Mio dans le banc (limite format 4 Mio), ≤256 fichiers/groupe, ≤4096 entrées et ≤64 Mio au total. La restitution reste en mémoire ; pas de diffusion en continu pour gros dossiers.
- La reprise HTTPS est celle du fichier conteneur ; la restitution peut ensuite reprendre par fichier. Aucun journal unique, manifeste signé indépendant du transport, reprise de groupe à groupe ou canal natif RDP livré. Pas de négociation de ce conteneur dans le protocole utilisateur.
- Le groupement et la compression solide sont des techniques connues. Ces mesures ne démontrent ni codec révolutionnaire ni supériorité générale face aux outils de transfert/archivage existants.
- Première suite système : deux échecs avec cryptography 50.0.0 ; suite finale intégrale réussie avec 50.0.2 sans réduire les attentes. Le banc initial est exploratoire seulement : une partie chevauche les tests et une révision de lecture ; aucun gain retenu à partir de cette campagne.
- L’installateur 0.4.1 existant est conservé octet pour octet. Bêta non signée, aucune installation Windows/RDP réelle ni scan antivirus supplémentaire.

## Reprise

Conserver R4.1 comme expérience. Prochain cycle : comparer au groupement standard tar/ZIP/7-Zip avec les mêmes garanties, puis développer un index de groupes authentifié/fragmenté et une restitution en flux borné avant toute intégration. Mesurer latence et réseau entre hôtes ; la reprise par fichiers individuels doit rester avantageuse lorsque peu de fichiers manquent. Ne pas intégrer uniquement sur la base du gain face au transfert fichier par fichier.

Reproduction : `python3 -m research.benchmark_bundle_r4 --rounds 5` puis `python3 -m research.benchmark_bundle_memory` et `python3 -m research.summarize_bundle_r4`. Les JSON conservent toutes les répétitions, bornes, empreintes et cas défavorables.

## Références standard tar et ZIP, campagne distincte

Cinq répétitions par méthode ; auto est remesuré dans la même campagne. tar PAX + Zstd1/Zstd3/LZMA1 et ZIP Deflate1, préparation source/SHA-256, création/fsync archive, transfert TLS vérifié, extraction dans un dossier neuf, fsync des fichiers, inventaire et SHA-256 de sortie inclus. Les helpers d’archive n’acceptent que les fixtures de confiance du banc. Aucune conclusion de sécurité sur un importateur de fichiers arbitraires.

| Dossier | Mbit/s | Meilleure référence standard | Standard (s) | Groupé auto (s) | Gain auto vs standard |
|---|---:|---|---:|---:|---:|
| gzip_noise | 50 | zip-deflate | 0.138557 | 0.165197 | -19.2 % |
| gzip_noise | 1000 | zip-deflate | 0.061160 | 0.081160 | -32.7 % |
| json_related | 50 | zip-deflate | 0.052658 | 0.091943 | -74.6 % |
| json_related | 1000 | zip-deflate | 0.044281 | 0.077752 | -75.6 % |
| mixed_heldout | 50 | tar-zstd3 | 0.620460 | 0.674212 | -8.7 % |
| mixed_heldout | 1000 | tar-zstd3 | 0.150599 | 0.171223 | -13.7 % |
| stdlib_real | 50 | tar-zstd3 | 0.193797 | 0.228885 | -18.1 % |
| stdlib_real | 1000 | tar-zstd1 | 0.087040 | 0.101949 | -17.1 % |

Les références standard restituent dans un dossier neuf, sans journal de reprise ni publication temporaire par fichier du moteur. Leur contrôle final vérifie les octets et l’inventaire avant réussite, mais leurs garanties de reprise/publication ne sont pas équivalentes. Les différences de coût doivent rester visibles ; aucun contrôle du moteur candidat n’a été supprimé pour gagner.

Décision : les gains face au fichier par fichier ne suffisent pas à promouvoir le conteneur maison. Garder les résultats standard favorables comme défavorables ; privilégier une intégration seulement après avantage face à ces références et reprise logique efficace. Les références standard ont un format, une granularité et des contrôles internes différents ; les contrôles de sortie et coûts ajoutés sont explicités ci-dessus.
