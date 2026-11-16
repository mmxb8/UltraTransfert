# R4.3 — restitution indexée et préparation bornée

16 novembre 2026. Application/EXE 0.4.1 inchangés ; laboratoire seulement.

## Objectif et garanties

Partir de main f95b002 et du checkpoint R4.2 actuel, archive version 29. Préserver tous les SHA-256, validations, bornes, conflits, journaux et publications temporaires.
Mesurer temps complet contre R4.2 et références brutes/tar+Zstd1/tar+LZMA1/ZIP ; mesurer séparément la mémoire de préparation.
Conserver le gain localisé sans promouvoir le regroupement comme mode utilisateur. Une économie mémoire ne suffit pas à imposer le spool sur tous les transferts.

## Profilage puis développement

Le profil initial du cas 1024 petits fichiers attribue 0,511 s sur 1,425 s instrumentées à BundleSource.check : 1 049 600 égalités d’entrées. Le journal représente 0,109 s. Les durées sous profileur ne sont pas des débits.
L’index par chemin remplace la recherche linéaire ; l’égalité du record immuable complet demeure exigée (taille, dates, mode, identité, SHA-256). Les entrées inconnues/malformées sont refusées. Aucun contrôle de contenu ou fsync du moteur n’a été retiré.
Le producteur facultatif spool=True compresse et écrit chaque groupe dans un fichier privé temporaire au lieu de retenir tous les groupes en RAM. Il écrit ensuite manifeste et groupes dans le .part exclusif, fsync, contrôle à nouveau la source et publie sans remplacement.
Une seconde optimisation libère le bytearray avant les allocations du codec ; en brut, l’écriture/hachage consomme ce bytearray sans copie de groupe supplémentaire. Le fichier temporaire peut occuper un conteneur supplémentaire sur le disque de sortie. Il est fermé/supprimé sur succès ou exception. Le prototype conserve les limites de 64 Mio, 4096 entrées, 4 Mio/groupe et 64 Kio/fichier. Le lecteur garde encore ses groupes décodés en mémoire ; aucune réception en flux n’est revendiquée.
Les octets des conteneurs UTSB1/UTSB2 sont identiques à R4.2 pour tous les codecs testés. Aucun nouveau format, négociation de production ou rattachement entre transports.

## Première passe complète : cinq répétitions par cellule

TLS authentifié en boucle locale Linux, caches chauds, processus isolés. Inclut préparation, SHA-256/inventaire, compression, écriture/publication du conteneur, transport, décodage, restitution via moteur et vérifications finales. Le contrôle indépendant supplémentaire et les fixtures/certificats sont hors temps.
Débit applicatif par connexion : le brut 4 workers peut atteindre quatre fois la limite nominale totale. Ni réseau physique partagé, ni RDP, ni USB réel. RSS inclut les deux extrémités/imports ; CPU chronométré pour les deux extrémités.
La colonne « gain » compare R4.3 mémoire à R4.2 ; le spool est affiché séparément. Les deux méthodes R4.3 partagent le nouvel index.

| Corpus | Mbit/s | R4.2 (s) | R4.3 (s) | Gain | R4.3 spool (s) | Meilleure référence (s) |
|---|---:|---:|---:|---:|---:|---|
| gzip_noise | 50 | 0.206615 | 0.208029 | -0.7 % | 0.187546 | zip-deflate 0.175515 |
| gzip_noise | 1000 | 0.222065 | 0.124829 | +43.8 % | 0.133827 | tar-zstd1 0.118127 |
| json_related | 50 | 0.124900 | 0.278844 | -123.3 % | 0.116013 | zip-deflate 0.093029 |
| json_related | 1000 | 0.124427 | 0.121094 | +2.7 % | 0.238202 | tar-lzma1 0.096559 |
| metadata_heldout | 50 | 0.880489 | 0.621210 | +29.4 % | 0.654442 | zip-deflate 0.332576 |
| metadata_heldout | 1000 | 1.373171 | 0.709163 | +48.4 % | 0.583846 | zip-deflate 0.322430 |
| mixed_heldout | 50 | 0.760948 | 0.770754 | -1.3 % | 0.739714 | zip-deflate 0.738617 |
| mixed_heldout | 1000 | 0.298715 | 0.265270 | +11.2 % | 0.292710 | zip-deflate 0.219655 |
| stdlib_real | 50 | 0.383016 | 0.281737 | +26.4 % | 0.320058 | zip-deflate 0.274068 |
| stdlib_real | 1000 | 0.173183 | 0.154905 | +10.6 % | 0.163296 | zip-deflate 0.154632 |

## Corpus indépendant de montée en nombre

Graine 98766121 distincte. Mélange de données aléatoires et structurées, fichiers courts, noms Unicode, fichier caché vide et dossier vide. 1 Gbit/s applicatif, cinq répétitions mélangées par méthode. Le nombre affiché exclut le fichier caché supplémentaire.

| Fichiers | R4.2 complet (s) | R4.3 complet (s) | Gain | Restitution R4.2 → R4.3 (s) | ZIP (s) | tar+Zstd1 (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 64 | 0.061417 | 0.068256 | -11.1 % | 0.021885 → 0.022634 | 0.046576 | 0.059895 |
| 256 | 0.431974 | 0.188389 | +56.4 % | 0.271768 → 0.095707 | 0.111958 | 0.135975 |
| 1024 | 0.892473 | 1.380723 | -54.7 % | 0.706362 → 0.888032 | 0.386290 | 0.514093 |
| 3840 | 10.079454 | 2.295244 | +77.2 % | 8.268674 → 1.515006 | 1.544756 | 1.757686 |

## Deuxième cycle, après optimisation de la copie de groupe

Les 350 mesures précédentes restent une campagne distincte, reproductible via research.benchmark_bundle_r43_before_flush. Le deuxième cycle conserve sa révision dans smallfile_bundle_r43_before_flush.py, évite la copie brute du groupe et libère le bytearray avant allocation du codec.
La campagne suivante réexécute les trois candidats sur tous les corpus/débits avec cinq répétitions mélangées, sans réutiliser les anciennes durées comme références synchrones.

| Corpus | Mbit/s | R4.2 (s) | R4.3 (s) | Gain vs R4.2 | R4.3 spool (s) |
|---|---:|---:|---:|---:|---:|
| gzip_noise | 50 | 0.188688 | 0.192982 | -2.3 % | 0.195762 |
| gzip_noise | 1000 | 0.132092 | 0.123081 | +6.8 % | 0.102996 |
| json_related | 50 | 0.108086 | 0.109713 | -1.5 % | 0.151672 |
| json_related | 1000 | 0.115656 | 0.114119 | +1.3 % | 0.113082 |
| metadata_heldout | 50 | 0.929604 | 0.548831 | +41.0 % | 0.535687 |
| metadata_heldout | 1000 | 0.884018 | 0.544738 | +38.4 % | 0.638239 |
| mixed_heldout | 50 | 0.779473 | 0.718886 | +7.8 % | 0.872552 |
| mixed_heldout | 1000 | 0.264107 | 0.294641 | -11.6 % | 0.302813 |
| stdlib_real | 50 | 0.321545 | 0.279207 | +13.2 % | 0.379295 |
| stdlib_real | 1000 | 0.169047 | 0.161550 | +4.4 % | 0.163139 |

## Mémoire du producteur isolé

32 Mio / 512 fichiers par corpus, sept répétitions par révision et codec, ordonnées aléatoirement, processus isolés. Tracemalloc ajoute un coût de temps. RSS relevée avant le contrôle indépendant non chronométré. Réseau/restauration exclus : ce tableau ne mesure pas un gain de transfert.

| Corpus / codec | Pic Python R4.2 → spool (Mio) | Baisse | RSS R4.2 → spool (Mio) | Temps R4.2 → spool (s) |
|---|---:|---:|---:|---:|
| random/raw | 37.21 → 4.47 | 88.0 % | 54.25 → 20.86 | 0.729728 → 0.759109 |
| random/auto | 48.74 → 16.43 | 66.3 % | 66.35 → 32.98 | 0.764725 → 0.854791 |
| repeated/raw | 37.19 → 4.47 | 88.0 % | 54.25 → 20.86 | 0.710876 → 0.742208 |
| repeated/auto | 44.72 → 12.43 | 72.2 % | 62.25 → 28.98 | 0.727108 → 0.716435 |

## Validation, décision et limites

301 tests Linux réussis, compilation Python et helper C++ Linux. Sept nouveaux tests de spool/index, dont égalité binaire tous codecs, SHA-256/inventaire, entrée forgée, source modifiée, ENOSPC simulé dans spool et destination, conservation d’anciens conteneurs et .part, vide/Unicode.
350 copies TLS de première comparaison + 80 de montée en nombre + 150 après optimisation, 36 exploratoires ; 112 préparations 32 Mio isolées avant/après optimisation, chacune décodée et vérifiée indépendamment avec égalité de tous les octets source et du conteneur entre révisions.
Conserver l’index dans le lecteur de laboratoire. Conserver le spool en option de recherche pour sa baisse de mémoire, sans activation automatique : le supplément d’I/O pénalise certains cas.
Les archives standard n’ont ni le même journal ni la même publication temporaire par fichier/reprise. Leurs sorties sont neuves, inventaires et empreintes vérifiés. Aucune équivalence des garanties ou supériorité générale revendiquée.
Les fortes variations sur cet hôte imposent de conserver les régressions (notamment JSON à 50 Mbit/s dans la première passe) et interdisent une promesse de gain global. La montée en nombre et les coûts CPU aident à distinguer l’effet de l’index du bruit d’I/O. Les résultats bruts contiennent CPU, RSS, octets HTTP, préparation, restitution et min/max. Un avantage face à R4.2 n’établit pas un avantage général face à tar/ZIP.
Prochain objectif : poursuivre le traitement des groupes avec un index de fichiers confirmé et un cache de groupes borné côté réception, puis mesurer coût de redécodage/reprise. Avant une intégration : manifeste authentifié et négociation explicite, corpus externes et supports/hôtes réels.

## Distribution et GitHub

Origine publiée recontrôlée : mmxb8/UltraTransfert main f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53. Base de travail locale : 6f1643e1a30299d4daa56b4309c15f32e3028d17 (R4.2 non publié), vérifiée contre le checkpoint de l’archive actuelle.
Le connecteur reste maher8-git ; le contrôle des droits sur mmxb8 répond 403. Aucun push ni nouveau workflow n’est revendiqué. Patch de la série depuis le main publié conservé pour reprise sûre.
L’EXE reste exactement 01349c32f77356b0e42062eaa7910ca0f5d4adaf9a3d66e6e1ff1382e41ae835, validé dans https://github.com/mmxb8/UltraTransfert/actions/runs/43844226030 ; les deux rapports Defender joints restent applicables à ces seuls octets.
Bêta non signée ; le laboratoire R4.3 n’est pas embarqué dans cet EXE. Windows 10/11, SmartScreen après téléchargement, RDP réel et bascule entre transports restent à valider. Le moteur Windows, test de régression, script PowerShell et dons Bitcoin sont inchangés.
