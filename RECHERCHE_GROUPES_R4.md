# R4.1 — petits fichiers regroupés, expérience bornée

Le laboratoire explore deux effets distincts : réduire les requêtes HTTPS et
compresser les répétitions entre petits fichiers. Ce sont des techniques connues,
pas une compression inédite. Le mode n’est pas proposé dans l’interface ni dans
l’installateur ; il ne remplace pas les copies habituelles.

Les résultats complets sont dans `reports/bundle-r4-summary.md`, les observations
individuelles dans `reports/bundle-r41-final.json`. Le programme reste en 0.4.1 ;
le numéro R4.1 désigne uniquement cette révision de recherche.

## Conception et garanties exercées

`research/smallfile_bundle.py` crée un instantané borné : inventaire du moteur,
refus des liens et noms non portables, ouverture contrôlée des sources,
empreintes par fichier, groupes avec taille/codec/SHA-256, manifeste borné et
vérification de stabilité de la source avant publication du conteneur.
L’écriture temporaire est exclusive et la publication utilise la primitive
sans remplacement du moteur. Une erreur ne supprime pas un ancien conteneur ou
un ancien fichier temporaire. Le mode auto essaie Zstd1 et conserve le brut si
le payload comprimé ne réduit pas le volume ; il ne prédit pas le CPU distant.

Le transport du conteneur utilise le HTTPS authentifié existant. Le parseur
borne les longueurs, refuse les clés JSON dupliquées, chemins dangereux,
collisions, tailles incohérentes, dépassements LZMA, corruption et fin excessive.
Il n’ouvre aucun chemin d’extraction : il expose les octets vérifiés au moteur
`Transfer`, qui fait la restitution avec ses fichiers temporaires, conflits,
reprise, journal et inventaire final habituels. Les ACL/flux NTFS ne sont pas
ajoutés. Le conteneur n’est pas conçu pour éditer un dossier vivant.

## Bornes et optimisation

Fichiers de 64 Kio maximum, 256 fichiers et 4 Mio maximum par groupe, 4096 entrées
et 64 Mio de données maximum par expérience. Le banc retient des groupes de
1 Mio, sans dictionnaire préentraîné. R4.0 conserve toute la restitution dans un
bytearray puis recopie les fichiers ; R4.1 conserve des vues en lecture seule
sur les groupes décodés. Cette économie mémoire ne supprime aucun SHA-256.
Le producteur conserve encore les groupes en mémoire : le passage en flux
borné doit être développé avant de viser les très grands dossiers.

Le protocole contient une liste complète de groupes, leurs tailles et leurs
empreintes, pas de recette exécutable. Les empreintes internes détectent les
erreurs ; l’authentification de l’émetteur vient du transport HTTPS existant.
L’identité `research-bundle` n’est pas une signature ni un manifeste authentifié
inter-transports : aucune bascule RDP/HTTPS/USB n’est revendiquée.

## Deux phases de reprise distinctes

Une coupure HTTPS reprend le fichier conteneur ; elle ne reprend pas des
fichiers logiques au fil du réseau. Après sa réception et validation complète,
la restitution peut reprendre ses propres fichiers. Ce découpage peut pénaliser
une reprise où peu de fichiers manquent ; il exige de l’espace pour le conteneur
et la destination. Il n’est pas activé dans le produit pour cette raison.

## Références et reproductibilité

```sh
python3 -m unittest discover -s tests -p test_smallfile_bundle.py -v
python3 -m research.benchmark_bundle_r4 --rounds 5
python3 -m research.benchmark_bundle_memory
python3 -m research.summarize_bundle_r4
```

Le banc principal mesure des copies TLS réelles en boucle locale Linux et
compte préparation, métadonnées, transport, reconstruction et vérification.
Les fixtures/certificats et le contrôle indépendant supplémentaire sont hors
chronométrage. La RSS est mesurée en processus isolés, la mémoire Python dans
un banc distinct. Les tableaux conservent les cas défavorables. Les méthodes
fichier par fichier utilisent un worker, avec deux références supplémentaires
à quatre workers. Le plafond est par connexion, pas un lien physique partagé.

`stdlib_real` contient des sources réellement installées ; les autres corpus
sont synthétiques. `mixed_heldout` utilise un mélange et une graine distincts,
sans ajustement après lecture des résultats finaux. Ni réseau distant, latence,
pertes, USB, Windows, canal natif RDP ou réactivité de session n’ont été mesurés.
Les références tar/ZIP sont réservées aux fixtures fabriquées par ce banc : leur
helper n’est pas un importateur de fichiers arbitraires à intégrer au produit.

Le checkpoint précédent R2.2/R3.1 est toujours intégré facultativement au
programme 0.4.1. Cette recherche ne le retire pas. L’installateur 0.4.1 reste
identique, bêta non signé et sans validation Windows/RDP réelle.

## Suite R4.2, 16 novembre 2026

Ce texte décrit le checkpoint R4.1 historique. Le bilan courant est dans
reports/bundle-r42-decision.md : manifeste comprimé facultatif, comparaison
complète aux archives et réconciliation avec le moteur Windows f95b002.
L'EXE distribué est désormais celui testé sur Windows Server 2022 et 2025,
SHA-256 01349c32f77356b0e42062eaa7910ca0f5d4adaf9a3d66e6e1ff1382e41ae835.
Lire DEMARRAGE_RAPIDE.md et les deux rapports windows-f95b002 ; le laboratoire
R4.2 n'est pas embarqué dans cet EXE. Bêta non signée, RDP réel non validé.

## Suite R4.3 : index et producteur borné

Lire reports/bundle-r43-decision.md et REPRISE_R43.md. Le lecteur de laboratoire
utilise un index avec égalité complète des entrées, sans retirer de hachage.
pack(..., spool=True) limite la RAM par un fichier privé temporaire. Le défaut
reste en mémoire et le produit/EXE n'est pas modifié. Tous les cas défavorables,
mesures mémoire et coûts CPU sont conservés. Les archives standard ne partagent
pas toutes les garanties du moteur ; aucune supériorité générale annoncée.
