# Recherche R2 — coût de sélection et liens rapides

Recherche uniquement : application et installateur restent 0.4.0. Le laboratoire
porte sa propre révision R2.2 ; aucune nouvelle version du produit n'est forcée.
R1 reste reproductible et disponible, sans modification de son sélecteur.

## Hypothèse et essais successifs

La recherche de recettes doit coûter une petite fraction du transfert brut.
Le nouveau sélecteur limite son exploration à 3 % du temps brut estimé : limite
souple, vérifiée entre candidats ; un appel codec engagé peut la dépasser.
L'estimation encodeur + reconstruction est multipliée par 1,5, une marge
heuristique, pas une mesure du destinataire. Les recettes ne sont conservées
que si leur coût estimé avec le temps de sélection déjà passé bat le brut.

R2.0 : premier prototype avec échantillon de 12 Kio ; exploration encore inutile
sur données incompressibles. Pas de campagne finale sur cette révision.
R2.1 : arrêt après trois sondes incompressibles et exclusion des prédicteurs
si la meilleure recette n'a pas de permutation. Campagnes CPU et HTTPS dans
reports/budget-r2-*.json. Régression JSON à 1000 Mbit/s constatée.
R2.2 : échantillon de 48 Kio (au plus trois segments de 16 Kio) pour réduire
l'amplification du coût fixe des appels codec. Campagnes budget-r22-*.
Ce choix a été ajusté sur les huit jeux de R1 : ils ne constituent donc plus
une validation indépendante du réglage R2.

Réutilisation : recette réexaminée sur changement de contenu ; si elle cesse
d'être rentable elle revient au brut. Après passage au brut, pas de sonde sur
chaque bloc ; une recherche revient tous les 16 blocs par défaut. Une nouvelle
zone compressible peut donc attendre 15 blocs avant d'être détectée. Ce coût
est volontaire et doit être mesuré sur des mélanges multiblocs futurs.

## Critères fixés avant la validation indépendante R2.2

- Octets exacts pour chaque reconstruction et chaque copie, sans exception.
- Conserver un gain spécialisé d'au moins 10 % face à la meilleure référence
  HTTPS testée à 50 Mbit/s sur le signal R1.
- Viser au moins 10 % de temps complet en moins face à R1 sur le signal R1
  à 1000 Mbit/s ; garder tous les résultats des autres jeux.
- Sur les cinq nouveaux jeux, viser aucune régression médiane supérieure à
  5 % face à R1. Un échec empêche toute promotion de ce sélecteur comme
  remplacement général ; il n'est pas masqué par une moyenne globale.

La validation indépendante utilise un nouveau signal float32 bruité, des
pseudoaléas gzip d'une autre graine et les octets locaux d'OpenSSL, d'une fonte
DejaVu et du moteur de transfert. Ce sont des fichiers réels locaux, pas un
corpus externe téléchargé ni un échantillon représentatif des entreprises.
Aucun réglage supplémentaire ne sera fait à partir de cette validation dans R2.

## Reproduction

Depuis les sources, Linux, OpenSSL, Zstd et Blosc système :

```sh
python3 -m unittest discover -s tests -p test_budget_research.py -v
python3 -m research.benchmark_predictive --rounds 5 --mbps 50 1000 --methods raw predictive budget_R2 zstd1-shuffle1 zstd3-shuffle1 zstd3-shuffle4 blosc-zstd-bitshuffle-4 blosc-lz4-bitshuffle-4 --output reports/budget-r22-cpu.json
python3 -m research.benchmark_predictive_https --cpu-report reports/budget-r22-cpu.json --extra-methods budget_R2 --rounds 5 --mbps 50 1000 --output reports/budget-r22-https.json
python3 -m research.benchmark_budget_validation cpu --rounds 5 --mbps 50 1000 --methods raw predictive budget_R2 zstd1-shuffle1 zstd3-shuffle1 zstd3-shuffle4 lzma1 lzma6-delta4 blosc-zstd-bitshuffle-4 blosc-lz4-bitshuffle-4 --output reports/budget-validation-cpu.json
python3 -m research.benchmark_budget_validation https --cpu-report reports/budget-validation-cpu.json --extra-methods budget_R2 --rounds 5 --mbps 50 1000 --output reports/budget-validation-https.json
```

Pour reproduire R2.1 utiliser la méthode budget_R21 (copie historique de sa
classe), en remplacement de budget_R2 dans les arguments. Les noms historiques
budget_R2 dans reports/budget-r2-* désignent bien R2.1, avant l'ajustement.
Le code final budget_R2 désigne R2.2. LZMA n'était pas dans le deuxième banc CPU
d'ajustement mais figure dans le premier et dans la validation indépendante.

## Limites inchangées

UTCP1 n'est pas négocié en production : patches exclusivement dans le banc.
Un brut UTCP1 garde son framing et ses contrôles de blocs, et peut coûter plus
que le HTTPS brut normal. Aucun basculement transparent vers le brut HTTP
n'est implémenté. Il faudra une négociation explicite avant intégration.
CPU des deux extrémités sur le même Linux, caches chauds, débit applicatif
plafonné, pas de RTT/pertes imposés ; ni hôtes distincts, ni supports physiques,
ni Windows/RDP. Tailles et coûts de framing, préparation, restitution et
vérification sont comptés. Mémoire tracée Python : espaces natifs exclus.
Blosc1 n'est pas Blosc2/TurboPFor/SPDP ; bibliothèques spécialisées non disponibles
ici, donc aucune conclusion comparative sur celles-ci.
