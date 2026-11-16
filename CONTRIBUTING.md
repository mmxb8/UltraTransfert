# Contribuer

Le code UltraTransfert est ouvert sous licence MIT, voir LICENSE. Cette archive
contient ses sources et son historique ; aucun dépôt public n'a été créé par
cette livraison. Une copie peut être publiée sur une forge avec cette licence.

Contrôles de base : `python build.py`, puis
`python -m unittest discover -s tests -v`. Installer les dépendances de partage
si les tests HTTPS sont souhaités. Ne jamais désactiver SHA-256, la reprise
vérifiée ou la gestion des conflits pour améliorer un chiffre de débit.

Voir CONSTRUCTION_INSTALLATEUR.md pour reconstruire l'EXE. Toute contribution
doit distinguer mesures synthétiques, boucle locale et supports réels ; ne pas
présenter une compilation croisée ou Wine comme une validation Windows/RDP.
