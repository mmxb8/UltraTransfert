# Point de reprise R4.2

- Base publiée à recontrôler : main f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53.
- Archive récupérée en version 28 ; checkpoint courant reports/bundle-r42-checkpoint.json.
- Branche locale research/r42-manifest. Le patch pending-r42.patch dans l'archive
  ajoute R4.1/R4.2 et les guides sans toucher au moteur corrigé du dépôt.
- Avant application : récupérer le main actuel et lire les différences. Utiliser
  git apply --check sur le patch ; si main a changé, intégrer fichier par fichier
  ou appliquer en trois voies dans un checkout isolé. Ne jamais forcer main.
- L'identité du connecteur est maher8-git ; contrôle de droits mmxb8 refusé (403).
  Navigateur déconnecté. Aucun commit nouveau n'a été publié dans cette exécution.
- Quand l'accès mmxb8 est restauré : pousser le commit cohérent puis lancer
  windows-validation.yml si des sources embarquées changent. Les tests Windows
  existants ne concernent que l'EXE f95b002 fourni, pas le laboratoire.
- Reproduction : commandes du laboratoire dans research/README.md ; tests :
  python3 -m unittest discover -s tests -v (cryptography==50.0.2).
- Prochain objectif : profiler restitution/journal/fsync sur support contrôlé,
  puis concevoir groupes indépendants et reprise logique avant toute intégration.
- Ne pas activer UTSB2 dans l'interface sans négociation/authentification et
  mesures représentatives. Pas de canal RDP natif implémenté ou testé ici.
