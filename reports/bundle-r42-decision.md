# R4.2 — manifeste comprimé, bilan du 16 novembre 2026

Application et installateur : 0.4.1. Révision du laboratoire : R4.2.

## Critères fixés avant les changements

- Conserver la lecture UTSB1, les empreintes, limites, publication et reprise du moteur.
- Refuser bombes de décompression, suffixes, trames concaténées, corruption et tailles excessives.
- Mesurer temps complet, volume, CPU et mémoire face au brut, tar+Zstd1, tar+LZMA1 et ZIP.
- Ne promouvoir aucun nouveau mode utilisateur sans gain représentatif et protocole négocié.

## Réconciliation

Base GitHub main : f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53. Archive relue : version 28, R4.1.
Ajouts de recherche R4.1 conservés ; ultra/engine.py, tests/test_engine.py et installer/Valider_Windows.ps1 viennent du dépôt.
Les anciens rapports sont historiques ; ils ne valident pas les nouveaux octets.
La session navigateur est déconnectée ; le connecteur est maher8-git et son contrôle de droits mmxb8 renvoie 403.
Commit local et patch préparés ; aucun push ni nouveau workflow Windows revendiqué.

## Implémentation et deuxième cycle

UTSB2 est facultatif et séparé du produit : manifeste zlib niveau 1 avec repli brut, tailles bornées avant lecture, sortie bornée sans flush non borné, EOF strict et SHA-256.
Le lecteur conserve UTSB1 ; un ancien lecteur refuse UTSB2. L’identité logique dérive du manifeste décodé, identique entre les deux représentations.
Après le banc exploratoire de 144 copies TLS, le deuxième cycle supprime une compression du manifeste répétée pour les seules métriques et remplace asdict récursif par la projection des champs immuables.
Les deux variantes finales utilisent la même sérialisation optimisée : la comparaison isole le format du manifeste. Le banc final ci-dessous est distinct du banc exploratoire et conserve les régressions. Aucune négociation UTSB2 ajoutée au protocole utilisateur.

## Mesures complètes

Médianes de cinq répétitions mélangées, processus isolés. Pourcentages : baisse positive. Les bornes min/max restent dans le JSON.
Le plafond est par connexion, le brut 4 workers peut atteindre quatre fois le débit agrégé. Caches chauds, Linux local TLS authentifié, pas de RTT ni pertes physiques.
Préparation, inventaire/SHA-256, compression, conteneur fsync, transport, reconstruction et vérification du moteur sont chronométrés. Fixtures, certificats et contrôle indépendant supplémentaire exclus.
RSS : processus isolé incluant imports et deux extrémités ; CPU : les deux extrémités sur cet hôte.

| Corpus | Mbit/s | UTSB1 JSON (s) | UTSB2 deflate (s) | Baisse temps | Baisse HTTP | Meilleure référence (s) |
|---|---:|---:|---:|---:|---:|---|
| gzip_noise | 50 | 0.204800 | 0.193096 | +5.7 % | 4.0 % | tar-zstd1 0.172899 |
| gzip_noise | 1000 | 0.132749 | 0.123150 | +7.2 % | 4.0 % | zip-deflate 0.099798 |
| json_related | 50 | 0.115164 | 0.111994 | +2.8 % | 61.7 % | zip-deflate 0.078830 |
| json_related | 1000 | 0.109504 | 0.110742 | -1.1 % | 61.7 % | zip-deflate 0.071009 |
| metadata_heldout | 50 | 0.821444 | 0.814062 | +0.9 % | 81.8 % | zip-deflate 0.302292 |
| metadata_heldout | 1000 | 0.822048 | 0.775835 | +5.6 % | 81.8 % | zip-deflate 0.326922 |
| mixed_heldout | 50 | 0.720676 | 0.756524 | -5.0 % | 1.0 % | tar-zstd1 0.687744 |
| mixed_heldout | 1000 | 0.306826 | 0.277612 | +9.5 % | 1.0 % | tar-zstd1 0.211487 |
| stdlib_real | 50 | 0.278790 | 0.273451 | +1.9 % | 2.1 % | tar-zstd1 0.268508 |
| stdlib_real | 1000 | 0.148111 | 0.150518 | -1.6 % | 2.1 % | tar-zstd1 0.114169 |

## Coût R4.2 et étapes

| Corpus | Mbit/s | Préparation (s) | Restitution (s) | CPU (s) | RSS (Mio) | HTTP (octets) |
|---|---:|---:|---:|---:|---:|---:|
| json_related | 50 | 0.029591 | 0.058830 | 0.110266 | 27.86 | 12959 |
| json_related | 1000 | 0.029245 | 0.057363 | 0.111542 | 27.86 | 12962 |
| stdlib_real | 50 | 0.045931 | 0.077879 | 0.154518 | 32.25 | 780150 |
| stdlib_real | 1000 | 0.050242 | 0.074967 | 0.148564 | 32.25 | 780150 |
| gzip_noise | 50 | 0.032094 | 0.061060 | 0.118356 | 28.84 | 505473 |
| gzip_noise | 1000 | 0.035304 | 0.055720 | 0.119079 | 28.84 | 505476 |
| mixed_heldout | 50 | 0.076381 | 0.158144 | 0.311155 | 36.74 | 3076187 |
| mixed_heldout | 1000 | 0.071168 | 0.149606 | 0.268224 | 36.74 | 3076190 |
| metadata_heldout | 50 | 0.170439 | 0.631005 | 0.809707 | 29.30 | 35000 |
| metadata_heldout | 1000 | 0.176718 | 0.584116 | 0.778475 | 29.31 | 35000 |

## Validation et décision

294 tests Linux réussis avec cryptography 50.0.2 ; compilation Python et helper C++ réussies.
300 copies finales TLS vérifiées, plus 144 exploratoires. Corpus : JSON synthétique, stdlib installée réelle, bruit gzip, mélange distinct et 1024 fichiers vides/très courts distincts.
Les références tar/ZIP n’ont pas le journal ni les publications temporaires par fichier du moteur ; elles vérifient inventaire et SHA-256 en destination neuve. Aucune égalité des garanties n’est revendiquée.
Conserver UTSB2 pour recherche, défaut inchangé. La baisse de volume est vérifiée ; le gain de temps dépend du corpus et les références standard restent compétitives. Pas de supériorité générale ni de nouveauté algorithmique.
Les groupes restent en mémoire (64 Mio maximum) et la restitution attend la réception complète ; pas de reprise logique en flux ni de manifeste authentifié entre transports.
Prochain cycle : profiler journal/fsync/restitution sur support contrôlé, puis prototype de groupes indépendants avec reprise logique avant intégration ; conserver les deux formats et tous les contrôles.
Windows 10/11, USB physique, hôtes distincts, RDP natif ou redirigé réel et réactivité de session non mesurés.

## Distribution

L’ancien EXE e075b363… de l’archive est remplacé par les octets du runner f95b002, SHA-256 01349c32f77356b0e42062eaa7910ca0f5d4adaf9a3d66e6e1ff1382e41ae835.
https://github.com/mmxb8/UltraTransfert/actions/runs/43844226030
Les deux rapports joints indiquent installation/reprise/TLS/réinstallation/désinstallation réussies, scan Defender installateur et payload sans détection, signature NotSigned.
Ce résultat concerne seulement cet EXE ; le laboratoire R4.2 n’y est pas embarqué. Les assets Bitcoin et la licence MIT sont inchangés.
DEMARRAGE_RAPIDE.md est réécrit en quelques étapes sans commandes ni ancien numéro d’installateur.

## Microbanc de sérialisation isolé

Projection des 4096 entrées immuables : médiane 0.016097 → 0.006738 s (58.1 % de baisse).
Quinze répétitions par méthode, ordre mélangé ; octets JSON strictement égaux.
Ce résultat exclut compression, transport, écritures et restitution : ne pas le
présenter comme un gain de transfert. Aucun gain mémoire significatif revendiqué.
Voir manifest-r42-micro.json et research/benchmark_manifest_r42.py.
