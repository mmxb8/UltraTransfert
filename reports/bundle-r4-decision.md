# Décision R4.1 et point de reprise

- Objectif : regroupement borné pour accélérer les dossiers de petits fichiers,
  sans annoncer de nouveauté algorithmique. Recherche uniquement, application
  et EXE conservés en 0.4.1 ; moteur utilisateur non modifié.
- Deux cycles : R4.0 conteneur complet + banc exploratoire ; R4.1 index en vues
  mémoire + campagne finale indépendante du test intégral, puis comparaison
  standard tar/ZIP. Les révisions de lecture sont conservées pour reproduire
  le microbanc mémoire. Ne pas utiliser le banc initial pour démontrer un gain.
- Gain mémoire conservé : vues immuables de groupes, toutes les empreintes
  inchangées. Pic Python -37,3 %, RSS -30,1 % sur le microbanc de 32 Mio.
- Piste non promue : auto groupe gagne notamment 56,3 % sur JSON à 50 Mbit/s
  face au meilleur direct mesuré, mais perd 74,6 % face à ZIP dans la campagne
  standard distincte. Sur le mélange à 50 Mbit/s, le direct 4 workers bat le
  groupe mono-worker (plafond applicatif par connexion, non agrégé).
- L’auto évite seulement les expansions de payload, pas la compression d’un
  groupe déjà incompressible. Le manifeste JSON est transmis non comprimé.
  Le pipeline écrit un conteneur supplémentaire et attend sa réception avant
  restitution. Les rapports contiennent la durée de restitution séparée.
- Les références standard n’ont pas le journal ni la publication temporaire
  par fichier du moteur. Elles vérifient octets/inventaire dans un dossier neuf.
  Aucune égalité des garanties de reprise/publication n’est revendiquée.
- Prochain objectif : profiler préparation, manifeste, fsync/journal, restitution
  et vérifications ; comparer un manifeste borné comprimé aux mêmes références,
  puis indexer des groupes indépendants avec reprise logique. Préserver chaque
  contrôle d’intégrité et mesurer coût complet avant intégration.
- Ne pas charger le conteneur de recherche dans le protocole utilisateur sans
  négociation et manifeste authentifié. Le canal virtuel RDP reste absent.
- L’installateur existant est conservé octet pour octet ; Windows/RDP réels et
  signature toujours indisponibles, aucune tentative de connexion GitHub dans
  cette exécution. Les fichiers d’authentification et assets Bitcoin sont inchangés.
