Mise à jour R2.2 : voir RECHERCHE_BUDGET_R2.md et reports/budget-r2-summary.md. Recherche seulement ; moteur/format publié et installateur 0.4.0 inchangés.

# Recherche de compression prédictive — checkpoint R1

Objectif demandé par Maher : obtenir un avantage de transfert sans perte démontré
face à des références solides, puis élargir et optimiser ce qui fonctionne.
Cette recherche reste limitée au transfert de fichiers local, réseau et RDP.

Ce checkpoint ajoute un laboratoire, pas un nouveau codec de production.
Le moteur `ultra/`, la négociation réseau et l’installateur 0.4.0 ne sont pas
modifiés. Les trames de recherche UTCP1 sont volontairement refusées par le
décodeur publié. Un banc HTTPS injecte explicitement son propre encodeur et
décodeur, uniquement pendant les mesures. Aucun utilisateur ne doit mélanger
ces trames avec un client 0.4.0 habituel.

## Hypothèses explorées

- Prédiction XOR à décalage fixe, suivie d’une permutation d’octets et de Zstd.
- Différence arithmétique du bloc entier à décalage fixe, suivie de la même
  compression. Les emprunts entre mots font partie du format et sont inversés
  exactement ; ce n’est pas le delta modulaire indépendant de chaque mot.
- Reconstruction de cette différence par division modulaire, comparée à
  l’accumulation par doublement de décalage. Les tailles non alignées gardent
  leur fin inchangée, et la longueur est bornée à 4 Mio.
- Arrêt rapide de la recherche sur données presque incompressibles ; choix
  d’une recette sur échantillons, réutilisation, détection de changement de
  contenu et retour au brut si la trame complète grossit.
- Deuxième itération : suppression du hachage/framing répété pendant la
  comparaison des recettes ; recherche en deux étapes et exclusion heuristique
  des prédicteurs pour certains contenus. Cette exclusion peut manquer une
  bonne recette : ce n’est pas une preuve d’optimalité.

Le décodage accepte une grammaire fixe et bornée. Il n’exécute pas de code généré,
n’utilise pas de modèle génératif et ne supprime aucun bit. Chaque bloc porte
un SHA-256 ; le flux et le moteur gardent aussi leurs vérifications habituelles.

## Critères fixés avant le banc HTTPS

Un premier succès spécialisé exige une réduction médiane d’au moins 10 % de
la durée complète à 50 Mbit/s sur le nouveau signal de validation, face à la
meilleure référence retenue par le banc CPU, et une restitution exacte à chaque
essai. La référence est avantagée par la connaissance du jeu et du débit.
Les coûts de préparation de la source et de reconstruction doivent compter.

Un gain de taille seul, un temps réseau estimé ou un gain face au brut seulement
ne remplissent pas ce critère. Les cas défavorables doivent rester visibles.
Aucune promotion générale ne découle de huit jeux sur une seule machine :
elle demandera des corpus externes représentatifs, d’autres processeurs,
des destinataires distincts et des transferts Windows/RDP réels.

## Reproduire

Depuis la racine des sources, sous Linux avec Python et OpenSSL :

```sh
python3 -m unittest discover -s tests -p test_predictive_research.py -v
python3 -m research.benchmark_predictive --rounds 5 --mbps 10 50 1000
python3 -m research.benchmark_predictive_https --rounds 5 --mbps 50 1000
```

Zstandard et Blosc système sont utilisés seulement s’ils sont disponibles.
Les références incluent brut, ancien UltraTransfert, Zstd 1/3 avec et sans
permutation, LZMA 1/6 avec et sans filtre delta, et Blosc1 Zstd/LZ4 avec
shuffle/bitshuffle. LZMA est celui de la bibliothèque Python dans un conteneur
XZ : ce n’est pas une exécution de 7-Zip. Blosc1 n’est pas Blosc2 ni TurboPFor.
Tous les octets de métadonnées sont comptés. Aucun dictionnaire préentraîné.

Les jeux comprennent des octets réels de la bibliothèque standard Python et
d’un exécutable ELF, plus des données synthétiques : signal float32 distinct
de l’exploration initiale, horodatages uint64, journaux JSON, base SQLite,
pseudoaléatoire déjà gzip et mélange JSON/pseudoaléatoire.

Les rapports conservent les empreintes des jeux, versions, recettes, temps
individuels, médianes et bornes. Le pic tracé par Python exclut les espaces
de travail natifs des codecs ; il ne représente pas la mémoire RSS totale.
Le temps CPU du banc HTTPS englobe les deux extrémités sur la même machine.
Les mesures loopback utilisent des caches chauds et un débit applicatif
plafonné ; elles n’émulent ni latence/pertes ni protocole RDP.

## Antériorité et limites de nouveauté

XOR, delta, permutation, bitshuffle et sélection de filtres existent déjà.
Cette combinaison et son implémentation ne sont pas présentées comme une
invention. Références primaires consultées :

- https://blosc.org/c-blosc2/c-blosc2.html
- https://blosc.org/c-blosc2/reference/utility_variables.html
- https://github.com/Blosc/c-blosc/blob/main/blosc/blosc.h
- https://github.com/powturbo/TurboPFor-Integer-Compression

Le bilan chiffré final de ce checkpoint est dans
`reports/predictive-summary.md`. Les échecs et les prochaines étapes y sont
conservés pour poursuivre la recherche sans recommencer l’exploration.
