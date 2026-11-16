# Checkpoint recherche R3.1 (application 0.4.0 inchangée)

Lecteur expérimental : moins de copies mémoire, même grammaire et vérifications. Pic Python du microbanc UTCP1 réduit de 47 % ; gain HTTPS fixe modeste sur un cas, régressions conservées. 266 tests Linux, 1 332 copies de comparaison et stress TLS 1 Gio/514 fichiers avec reprise vérifiés. Les variations de recettes adaptatives empêchent d'attribuer leurs gains au lecteur seul. Voir RECHERCHE_LECTURE_R3.md et reports/reader-r3-summary.md. Aucune intégration au moteur ou à l'installateur.

---

# Checkpoint recherche R2.2 (application 0.4.0 inchangée)

Sélection limitée par le temps de transport brut estimé et réutilisation moins coûteuse. Trois campagnes, 1 005 copies HTTPS vérifiées et 1 940 mesures CPU ; 257 tests Linux réussis. Gain spécialisé conservé, régressions et limites documentées. Voir RECHERCHE_BUDGET_R2.md et reports/budget-r2-summary.md. Aucune intégration au moteur ou à l’installateur.

---

# Recherche prédictive R1

Le nouveau bilan est dans reports/predictive-summary.md ; conception et reproduction dans RECHERCHE_PREDICTIVE.md. 250 tests réussis, 305 copies HTTPS réelles et 1 920 mesures CPU finales. Avantage spécialisé sur un signal synthétique, pas de supériorité générale. Aucune intégration au moteur ou à l’installateur 0.4.0.

---

# UltraTransfert 0.4.0 — installateur, code ouvert et dons

Date de livraison : 15 novembre 2026 (Montréal).

## Réalisé

- Installateur EXE NSIS réellement compilé sous Linux : assistant français,
  installation par utilisateur, runtime CPython 3.14.10 x64 et Tcl/Tk inclus,
  cryptography 50.0.2 et Zstandard 0.25.0 inclus, sans téléchargement à
  l'installation, raccourci Démarrer et Bureau facultatif.
- Contrôle du contenu installé par SHA-256, ressources GUI et copie/reprise
  avant confirmation. Aucun service réseau n'est démarré par ce contrôle.
- Licence MIT pour UltraTransfert ; sources complètes et licences tierces
  consultables hors ligne dans le dossier installé.
- Bouton de dons Bitcoin facultatifs. Adresse fournie par Maher conservée
  exactement : 3HaGinyFJQJXFAMgU8SBuDxdS5aG5BQUNU. QR PNG/SVG encodant
  bitcoin:3HaGinyFJQJXFAMgU8SBuDxdS5aG5BQUNU, décodé par zxing-cpp. Le QR
  de la capture a été relu et correspond ; aucune copie de la capture privée
  n'est incluse dans la distribution. Aucune transaction automatique.
- Dépendances et empreintes verrouillées, manifeste SHA-256 du contenu et
  liste fixe de désinstallation sans suppression récursive. Les fichiers
  étrangers restent sur place et peuvent empêcher une réinstallation.
- Script de validation Windows/Defender fourni pour un futur poste de test,
  mais non exécuté ici. Pas de retour arrière automatique à la mise à niveau.

## Validations effectuées

- Compilation Python et helper C++ Linux ; 235 tests réussis en 28,63 secondes après intégration de la version 0.3.19 (voir reports/tests-0.4.0.txt),
  dont contrôle de corruption, refus des ZIP traversants/liés, chemins de
  manifeste hors installation et cache de dépendances altéré.
- Interface réellement ouverte sous Xvfb/Linux, chargement du QR et copie de
  l'adresse contrôlés. Dialogue de don : 397 x 531 pixels sur écran 1280 x 1000.
  Fenêtre principale également manipulée à 760 x 400. Ce n'est pas un rendu Windows.
- Contrôle GUI et TLS local avec certificat préparé, rechargement de connexion,
  arrêt du service, interruption/reprise et SHA-256 vérifié. Voir gui-0.4.0-linux.json.
- Paquet Python construit avec assets et licence ; installation isolée contrôlée.
- EXE reconnu comme NSIS Unicode ; son manifeste PE requiert asInvoker,
  sans élévation administrateur. Signature Authenticode absente et annoncée.
- Contenu de l'EXE réextrait et comparé à son manifeste SHA-256. Vérification
  indépendante de l'adresse Bitcoin et du QR. Les dépendances CPython originales
  ne sont pas repackées avec UPX ni modifiées pour esquiver une détection.

## Limites

L'installateur est une bêta non signée. Aucune installation/mise à niveau/
désinstallation Windows réelle n'a été effectuée ; les contrôles d'installation
sont implémentés, sans preuve de leur exécution sur Windows. Une tentative
locale d'amorçage Wine n'a pas fourni d'environnement de test utilisable et
n'est pas comptée comme validation. Aucun scan antivirus, SmartScreen ou Smart
App Control réel n'est revendiqué. Zéro détection/blocage ne peut être garanti.
Il faut tester sur Windows propre, obtenir une signature reconnue et scanner
les octets finaux. Ne jamais demander aux utilisateurs de désactiver leurs protections.

La version 0.4.0 conserve aussi les modifications HTTPS de la 0.3.19 (réutilisation des connexions), intégrées après la première compilation. Leur historique, tests et mesures sont conservés ci-dessous. Aucun gain supplémentaire de vitesse ou de compression dû à l’installateur n’est revendiqué. RDP natif et reprise entre
protocoles restent à développer. Les limites de métadonnées restent documentées.
Aucun dépôt public ni compte de signature n'a été créé ; les sources sont
fournies sous licence open source et peuvent être publiées.

# Rapport — UltraTransfert 0.3.19

15 novembre 2026. Objectif : accélérer réellement les nombreux petits fichiers HTTPS sans nouveau réglage utilisateur, sans suppression des contrôles et sans changement du manifeste de reprise. Critères fixés : fidélité du contenu/inventaire, interruption/reprise, TLS/jeton/absence de redirection préservés ; gain de temps complet sur petits fichiers, coût CPU/mémoire documenté ; rejeter le framing supplémentaire sur gros flux s’il pénalise leur chemin.

## Modification retenue et essais rejetés

Pool TLS propre à chaque source/origine et contexte de confiance, connexions prêtées exclusivement à une réponse, huit inactives maximum. Chaque GET porte toujours son authentification. Le nombre de requêtes fichiers ne baisse pas : ce sont les négociations TLS répétées qui sont évitées. Fermeture à la fin de Transfer.run, après échec de préparation, via la source delta et à la destruction d’un pool inutilisé. Une réponse abandonnée, incomplète, en erreur de lecture ou nécessitant fermeture n’est pas réutilisée. Pas de retry implicite : après perte réseau, relancer avec les mêmes paramètres et l’état conservé. Le test de rupture d’une connexion inactive confirme l’erreur puis le rétablissement sur tentative suivante.

Serveur HTTP/1.1 avec Content-Length pour le brut. Réponses gzip/ultra de 64 Kio maximum : HTTP chunked avec tampon de 64 Kio et regroupement des écritures ; pas de tampon du fichier entier. Gros flux comprimés : chemin antérieur en fermeture de connexion, sans ce tampon supplémentaire. Les anciens serveurs HTTP/1.0 restent lisibles sans réutilisation. Les octets de codecs, sélecteur, trames UTCS1 et manifeste restent identiques. Aucune nouveauté algorithmique, amélioration de ratio ou reprise inter-transports livrée.

Premier essai rejeté : sans TCP_NODELAY côté serveur, 160 petits fichiers bruts avec un worker passaient de 0,413 à 7,236 s. Deuxième essai : TCP_NODELAY rétablit le bénéfice brut, mais les petites écritures du framing gzip dégradent certains transferts à quatre workers. Troisième essai : regroupement borné, gain sur petits fichiers, mais extension aux gros flux ultra défavorable (32 Mio aléatoires, un worker : 0,3202 → 0,4517 s, RSS médian 60 724 → 64 984 Kio). La variante conservée limite donc ce framing aux petites réponses comprimées. Résultats antérieurs conservés dans reports/https-reuse-first.json, https-reuse-0.3.19.json, https-reuse-final-0.3.19.json et https-reuse-buffered-0.3.19.json. Le RSS du tout premier banc est hérité du lanceur et inutilisable ; les suivants lisent VmHWM du processus exécuté.

## Comparaison finale complète

160 copies TLS réelles en boucle locale Linux, cinq répétitions par combinaison, ordre mélangé déterministe, processus isolés. Référence 0.3.18 complète dans history/v0.3.18/ultra ; même corpus et destination distincte à chaque essai. Small : 160 fichiers de 1 Kio synthétiques compressibles, un fichier caché vide et un dossier vide. Large : 32 Mio pseudo-aléatoires, caché vide et dossier vide. Temps incluant inventaire source, préparation/hachage serveur, TLS, manifestes, copie/fsync, décompression/reconstruction et contrôles finaux ; génération corpus/certificat, import et contrôle SHA indépendant supplémentaire exclus. Cache chaud, pas de plafond ni de latence ajoutée, aucun support physique/réseau distant. CPU mesuré pour client et serveur dans le même processus ; RSS haut du processus en Kio. Le framing HTTP/TLS est inclus dans le temps, mais aucun volume réseau complet n’est mesuré. Les médianes ne prouvent pas une supériorité universelle. Un signe négatif signifie une régression, conservée dans le tableau.

| Corpus | Workers | Mode | Avant s | Après s | Réduction du temps | CPU s avant → après | RSS Kio avant → après | Connexions TLS avant → après |
|---|---:|---|---:|---:|---:|---|---|---|
| small | 1 | none | 0.3979 | 0.1367 | +65.7 % | 0.376 → 0.141 | 22664 → 22624 | 164 → 1 |
| small | 1 | auto | 0.4340 | 0.1738 | +60.0 % | 0.404 → 0.181 | 23008 → 22872 | 164 → 1 |
| small | 1 | gzip | 0.4412 | 0.1537 | +65.2 % | 0.413 → 0.160 | 22936 → 22804 | 164 → 1 |
| small | 1 | ultra | 0.5561 | 0.2807 | +49.5 % | 0.430 → 0.290 | 23068 → 23008 | 164 → 1 |
| small | 4 | none | 0.3500 | 0.2374 | +32.2 % | 0.631 → 0.299 | 23928 → 23784 | 164 → 4 |
| small | 4 | auto | 0.4321 | 0.2602 | +39.8 % | 0.727 → 0.323 | 25020 → 24528 | 164 → 4 |
| small | 4 | gzip | 0.4254 | 0.2550 | +40.1 % | 0.715 → 0.317 | 24828 → 24344 | 164 → 4 |
| small | 4 | ultra | 0.5890 | 0.4744 | +19.5 % | 0.958 → 0.628 | 24784 → 24508 | 164 → 4 |
| large | 1 | none | 0.2028 | 0.2257 | -11.3 % | 0.240 → 0.249 | 31620 → 32792 | 5 → 1 |
| large | 1 | auto | 0.1878 | 0.2089 | -11.2 % | 0.218 → 0.241 | 31748 → 31768 | 5 → 1 |
| large | 1 | gzip | 0.8911 | 0.8323 | +6.6 % | 0.980 → 0.902 | 39220 → 39204 | 5 → 2 |
| large | 1 | ultra | 0.3340 | 0.2810 | +15.9 % | 0.402 → 0.350 | 60596 → 60604 | 5 → 2 |
| large | 4 | none | 0.1891 | 0.2398 | -26.8 % | 0.211 → 0.263 | 35036 → 35132 | 5 → 2 |
| large | 4 | auto | 0.1785 | 0.2134 | -19.6 % | 0.217 → 0.244 | 33192 → 33072 | 5 → 2 |
| large | 4 | gzip | 0.8984 | 0.9154 | -1.9 % | 0.979 → 1.031 | 40044 → 39928 | 5 → 2 |
| large | 4 | ultra | 0.3514 | 0.3075 | +12.5 % | 0.415 → 0.374 | 60880 → 60892 | 5 → 2 |

Les cinq mesures individuelles de chaque combinaison sont dans reports/https-reuse-bounded-0.3.19.json. Comparer les références et candidats de ce dernier banc uniquement : les variations entre bancs ne sont pas des gains de code. Les modes auto et ultra restent des stratégies existantes ; aucune nouvelle sélection ni compression n’a été développée. Gzip fixe et brut sont inclus pour rendre visibles les coûts de l’adaptation.

### Vérification complémentaire de 256 Mio

Vingt copies supplémentaires, cinq répétitions par version et nombre de workers, même procédure, HTTPS brut. Un worker : médiane 1,0417 → 0,9259 s (−11,1 %), CPU 1,265 → 1,174 s et RSS 38 024 → 32 996 Kio. Quatre workers : 0,9808 → 1,0257 s (+4,6 % plus lent), CPU 1,129 → 1,242 s et RSS 35 276 → 35 360 Kio. Le résultat dépend donc de la charge et du parallélisme : aucun gain général sur gros fichiers n’est établi. Les régressions de 32 Mio ci-dessus restent publiées, sans être effacées par ce banc complémentaire. Données complètes : reports/https-reuse-large256-0.3.19.json.

Une première tentative de ce complément conservait toutes les destinations temporaires : le contrôle d’espace de la référence a refusé la dix-neuvième copie, avant copie, faute de place. Aucun résultat statistique de cette tentative incomplète n’est revendiqué. Le banc libère désormais chaque destination après contrôle indépendant et conserve un checkpoint .partial tant qu’il n’a pas terminé ; le complément complet ci-dessus a réussi. Ce nettoyage touche seulement les données générées par le banc. Reproduction : ajouter --large-mib 256 --modes none --workloads large à la commande comparative. Le premier banc de 160 copies et ses résultats restent indépendants de ce complément.

## Validation de l’intégrité et robustesse

Compilation Python et helper C++ Linux réussie. **224 tests passent**, aucun ignoré : treize nouveaux tests de pool/framing/réseau couvrent connexion unique, petites réponses comprimées, abandon, isolation à quatre threads, HTTP/1.0, interruption/reprise, rupture inactive sans retry implicite, libération après verrou concurrent, borne du pool, tailles/framing et troncature. Les tests existants conservent corruption, conflits, source modifiée, manque d’espace simulé, authentification, certificats/nom d’hôte et refus des redirections. Contrôleurs GUI avec widgets doublés, pas de validation visuelle. Au premier passage, deux tests de préparation échouaient car le runtime avait cryptography 50.0.0 ; le complément attendu 50.0.2 a été installé dans test-deps isolé, puis la suite a passé sans modification des critères.

Trois intégrations réelles TLS loopback : brut avec fichier de 1 Gio et 259 fichiers au total ; gzip et ultra avec 64 Mio et 259 fichiers chacun. Cachés, Unicode/arabe/japonais, fichiers et dossiers vides, source conservée et inventaires/empreintes SHA-256 indépendants. Chaque parcours interrompt après 8 Mio puis reprend 8 Mio validés par contenu avant réussite. Les rapports mixed-raw/gzip/ultra-0.3.19.json donnent les empreintes et compteurs. Ces intégrations ne sont pas une comparaison de débit entre codecs. Elles sont relancées sur le code final avant sauvegarde.

Le wheel 0.3.19 est reconstruit après les changements finaux ; les nouveaux tests et le contrôle embarqué sans GUI sont exécutés depuis son installation isolée. Les sources réseau embarquées sont comparées octet pour octet au projet.

## Reproduire et point de reprise

- python3 build.py
- python3 -m unittest discover -s tests -v (complément cryptography 50.0.2 requis par les tests de partage/préparation)
- python3 -m research.benchmark_https_reuse --baseline history/v0.3.18 --candidate . --output reports/reproduction-reuse.json --rounds 5
- python3 -m research.verify_mixed_https --compression none --large-mib 1024 --output reports/reproduction-raw.json
- python3 -m research.verify_mixed_https --compression gzip --output reports/reproduction-gzip.json
- python3 -m research.verify_mixed_https --compression ultra --output reports/reproduction-ultra.json

Lancer ces commandes sous le verrou de projet, sans autre édition/compilation ou benchmark concurrent. Le benchmark est Linux (/proc/self/status), borné à ses combinaisons et termine tous ses enfants ; aucun processus détaché. Reprendre ensuite : tests réseau sur deux postes, débit/latence, coupures prolongées et essais Windows de premier lancement/portable. Conserver le seuil 64 Kio tant que des mesures plus larges ne justifient pas une autre stratégie ; ne pas réactiver le framing des gros flux sur la seule base des petits fichiers.

## Limites

Sources et wheel Python, **aucun EXE Windows construit**. Pas de Windows, Wine, DISPLAY/Xvfb ou hôte RDP accessible dans ce cycle. Installation Windows sans Python préinstallé, GUI, lecteurs tsclient et réactivité RDP non validés. Aucune mesure sur supports USB physiques ou réseau entre deux machines. Canal DVC natif et manifeste authentifié de reprise inter-transports restent à développer. ACL, ADS NTFS et attributs étendus non copiés. Connexions directes HTTPS ; proxy et gros déploiement multiutilisateur non validés. Une connexion inactive expirée peut produire une erreur ; la reprise explicite conserve les contrôles. Les gros flux comprimés ne bénéficient pas de la réutilisation pour leur propre corps. Aucun gain universel ni amélioration de compression sans perte revendiqués.

---

# Rapport — UltraTransfert 0.3.18

15 novembre 2026. Archive actuelle récupérée : 0.3.17, version persistante 20 ; même identité, remplacement avec garde effective. Cycle borné consacré à l’accessibilité du formulaire de copie sur écran peu haut, usage pertinent en session distante sans prétendre tester RDP.

## Code et parcours utilisateur

La fenêtre principale imposait 820 × 740 au lancement et une hauteur minimale de 700. Le formulaire est maintenant placé dans un Canvas avec barre verticale et Frame extensible en largeur. La taille initiale tient compte de l’écran, avec marges heuristiques de 80 pixels en largeur et 100 en hauteur ; plafond 820 × 740, minimum 720 × 400. Les textes principaux sont enveloppés à 600 pixels pour conserver une largeur prudente avec la barre.

Barre verticale ou molette pour atteindre les commandes, y compris les réglages avancés et boutons de résultat. La navigation clavier vers un contrôle hors champ ajuste le défilement. La molette n’est pas capturée dans les listes de sélection/texte disposant de leur propre comportement. Événements liés au seul toplevel principal et filtrés sur ses descendants du formulaire ; aucun bind_all et aucun dialogue secondaire capturé. Les champs de source, destination, boutons et contrôleurs restent les mêmes.

Ce changement concerne la fenêtre principale : les dialogues secondaires ne sont pas transformés. Une largeur inférieure à 720 ou hauteur inférieure à 400 reste hors cible. Marges, DPI, styles, coordonnées de focus et comportement du gestionnaire de fenêtres doivent être vérifiés visuellement. Aucun accès, transport, dépendance ou lancement automatique ajouté.

## Validations réelles et simulation

Compilation Python et helper C++ Linux réussies ; **211 tests Linux réussis, aucun ignoré**, dont neuf nouveaux avec widgets doublés : taille initiale, construction et barre, bindings limités au toplevel, région suivant le contenu, largeur suivant le viewport, directions Windows/Linux et petites valeurs de molette, sélection/texte/dialogue non capturés, focus au-dessus/au-dessous rendu visible selon coordonnées fournies, absence de saut pour un contrôle visible ou petit contenu, intégration d’App et minimum réduit. **Aucun rendu Tk réel** dans ces tests.

Mesure reproductible de géométrie avec le vrai gestionnaire de focus mais des positions synthétiques de widgets : formulaire de 1 200 pixels et commande à y=1 100, hauteur 30. Le déplacement place cette commande dans le viewport simulé pour les trois tailles ci-dessous. Ces positions ne sont pas celles d’un formulaire réellement rendu. Pas de temps de lancement, DPI, réactivité ou transfert RDP mesuré.

| Écran simulé | Taille demandée auparavant | Nouvelle taille calculée |
|---|---|---|
| 800 × 600 | 820 × 740, minimum hauteur 700 | 720 × 500, minimum hauteur 400 |
| 1024 × 768 | 820 × 740, minimum hauteur 700 | 820 × 668, minimum hauteur 400 |
| 1920 × 1080 | 820 × 740, minimum hauteur 700 | 820 × 740, minimum hauteur 400 |

Résultats, coordonnées et exclusions : reports/viewport-0.3.18.json. L’ergonomie visée doit encore être confirmée à l’écran. Aucun gain de performance/compression n’est déduit de ce modèle.

Contrôle HTTPS ultra réel en boucle locale Linux : 259 fichiers, un de 64 Mio et 256 petits, Unicode/cachés/vides, interruption puis reprise de 8 388 608 octets avec quatre workers, inventaire et SHA-256 indépendants, source conservée. 2,030 s, caches chauds, sans plafond réseau, élagage du sélecteur explicitement activé. Contrôle local 1 Gio : 3,151 s, bloc synthétique répété, fsync demandé et vérifications incluses, SHA-256 indépendant correct. Ces temps varient par rapport aux exécutions précédentes ; moteur inchangé, aucune causalité ou amélioration de débit revendiquée. Pas de support physique ou réseau entre deux postes.

Le wheel 0.3.18 a été construit et installé séparément ; les neuf nouveaux tests réussissent avec import depuis cette installation. Le contrôle embarqué local sans GUI réussit également, avec 65 536 octets repris. Rapports : reports/installed-wheel-0.3.18.json et son journal. Cela ne valide pas un EXE Windows ni le rendu Tk.

## Reproduire et limites

`python3 build.py` ; `python3 -m unittest discover -s tests -v` ; `python3 -m research.measure_viewport` ; `python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.18.json` ; `python3 verify_gib.py`. Cryptography 50.0.2 disponible en chemin isolé pour les tests du partage. Référence interface : history/v0.3.17/ultra/gui.py. Moteur, réseau, codecs, partage, préparation et construction Windows inchangés octet pour octet : reports/unchanged-core-0.3.18.json.

Linux sans DISPLAY/socket X11/Xvfb/Wine, sans Windows ni hôte RDP connecté. Aucun EXE Windows construit ou installé, aucune validation visuelle ou véritable session RDP. Archive source et wheel Python livrés ; installation sans Python utilisateur reste à construire/valider sous Windows. Tester réellement à 800 × 600 et plusieurs DPI : lancement, choix des dossiers, réglages avancés, copie, interruption/reprise, bilan et ouverture de destination, puis dialogues de partage. RDP natif et manifeste authentifié de reprise inter-transports restent à développer. ACL, flux NTFS alternatifs et attributs étendus non copiés. Compression expérimentale inchangée, facultative, désactivée par défaut.

---

# Rapport — UltraTransfert 0.3.17

15 novembre 2026. Archive actuelle récupérée : 0.3.16, version persistante 19. Identité conservée, remplacement avec garde effective. Cycle borné : interruption fiable pendant les inventaires et vérifications finales.

## Problème et correction

Les inventaires destination avant copie et en vérification finale ne recevaient pas le signal d’arrêt, et les recontrôles de source étaient également lancés sans lui. Pour un transfert sans fichiers, aucune boucle de hachage ne contrôlait ensuite l’arrêt : il pouvait être annoncé terminé malgré une demande d’arrêt au début de l’inventaire final. Ce défaut est reproduit avec la référence archivée.

Le moteur transmet désormais le signal aux deux inventaires destination et aux deux recontrôles de source. LocalSource le supportait déjà ; RemoteSource accepte maintenant cancel=None et contrôle le signal avant/après la requête de manifeste, DeltaSource le relaie. Les annulations typées OperationCancelled interceptées dans le moteur deviennent « Vérification interrompue ; reprise possible. », compatible avec le résultat graphique d’interruption. Les autres exceptions et erreurs déjà collectées sont conservées. Une différence de manifeste distant effectivement constatée reste une erreur, même si le signal est positionné après la requête.

L’arrêt est également contrôlé pendant la réapplication des métadonnées de dossiers et juste avant de quitter la partie vérifiée. Une interruption laisse le transfert incomplet même si les fichiers sont déjà présents ; reprendre avec les mêmes dossiers relance les vérifications par contenu et l’inventaire final avant réussite. Aucun contrôle SHA-256 ou d’inventaire n’est supprimé. Journal, identité et format du manifeste de reprise inchangés. Aucun nouveau transport ou permission.

Le mécanisme reste coopératif : un appel disque, une énumération/tri de grand dossier ou une requête HTTPS engagée peut retarder l’arrêt. La requête distante n’est pas interrompue au milieu ; ses délais réseau actuels s’appliquent. Ce changement n’apporte pas de reprise entre transports.

## Validations réelles

Compilation Python et helper C++ Linux réussies ; **202 tests Linux réussis, aucun ignoré**. Sept nouveaux tests : contrôleur graphique sans écran avec source vide arrêté à l’inventaire final, reprise et absence de faux succès ; arrêt à l’intérieur d’un inventaire final réel, reprise de 61 fichiers déjà publiés et tous leurs SHA-256 indépendants ; signal reçu lors des deux recontrôles source ; erreur de droits injectée restant une erreur ; garde distante avant/après requête et priorité du manifeste différent (requête doublée) ; relais delta ; arrêt après application des métadonnées du dernier dossier et reprise avec date contrôlée. Unicode, caché et dossier vide sont inclus. Les widgets et appels distants des nouveaux tests sont doublés, pas une validation visuelle ou réseau distante.

Contrôle HTTPS ultra réel en boucle locale Linux : 259 fichiers, dont un de 64 Mio et 256 petits, Unicode/cachés/vides. Interruption pendant copie et reprise de 8 388 608 octets avec quatre workers, inventaire/SHA-256 indépendants et source conservée : 1,273 s sur cette exécution, caches chauds, élagage du sélecteur explicitement activé. Contrôle local 1 Gio : 2,554 s, bloc synthétique répété, fsync demandé et contrôles inclus, SHA-256 indépendant. Pas une mesure de gain causal de débit ni de support physique.

Le wheel 0.3.17 a été construit puis installé séparément ; les sept nouveaux tests y réussissent avec import depuis cette installation. Contrôle embarqué local sans GUI également réussi avec 65 536 octets repris. Rapports : reports/installed-wheel-0.3.17.json et son journal. Ce contrôle Linux non figé ne valide pas Windows.

## Comparaison au point d’arrêt final

Douze copies locales réelles : trois répétitions alternées par variante et taille (0 ou 2 000 fichiers synthétiques minuscules Unicode, plus un dossier vide). Même demande d’arrêt au début de la phase d’inventaire final, caches chauds. Le temps après demande inclut retour du moteur, écriture du rapport/journal et libération du verrou. Préparation des données et contrôle indépendant des octets/inventaire exclus du chrono. Aucun rendu GUI, Windows, RDP ou réseau dans le banc.

| Fichiers | 0.3.16 après arrêt, médiane | 0.3.17 après arrêt, médiane | Réussites annoncées après arrêt, ancien → nouveau |
|---|---:|---:|---:|
| 0 | 0,247 ms | 0,137 ms | 3 → 0 |
| 2 000 | 66,388 ms | 1,941 ms | 0 → 0 |

Sur les 2 000 fichiers, l’ancien moteur poursuivait l’inventaire avant de remarquer l’arrêt au hachage. Le nouveau évite ce travail après demande. Tous les fichiers publiés et la source sont contrôlés indépendamment après les douze essais, verrous libérés. Min/max et résultats : reports/final-stop-0.3.17.json. Ces délais dépendent du banc ; aucune garantie d’arrêt immédiat ou de débit supérieur.

## Reproduire et limites

`python3 build.py` ; `python3 -m unittest discover -s tests -v` ; `python3 -m research.benchmark_final_stop` ; `python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.17.json` ; `python3 verify_gib.py`. Suite complète avec cryptography 50.0.2 pour les tests de partage. Référence archivée : history/v0.3.16/ultra/engine.py, network.py et delta.py. Codecs, GUI, partage, préparation source et construction Windows inchangés octet pour octet : reports/unchanged-parts-0.3.17.json. Aucune nouvelle expérience comparative de compression ou nouveauté algorithmique ; modes expérimentaux facultatifs et désactivés par défaut.

Linux sans DISPLAY/Xvfb/Wine, Windows ou hôte RDP connecté. Aucun EXE/installateur Windows construit ni validation visuelle. Archive source et wheel Python livrés ; installation Windows sans Python utilisateur reste à construire/valider sur Windows. Aucun support USB physique ou réseau entre deux postes testé. Canal RDP natif RDC/MSTSC et manifeste authentifié inter-transports restent à développer. ACL, flux NTFS alternatifs et attributs étendus non copiés.

---

# Rapport — UltraTransfert 0.3.16

15 novembre 2026. Archive actuelle récupérée : 0.3.15, version persistante 18. Même identité et remplacement avec la garde reçue. Cycle borné consacré à la préparation répétée des sources, partie portable de l’installation Windows.

## Modification concrète

La préparation vérifiait déjà les imports du complément HTTPS, mais appelait ensuite pip même si celui-ci était utilisable. Elle réutilise désormais cryptography **50.0.2** après contrôle de version et imports nécessaires (X.509, sérialisation, primitives/RSA). Aucun pip, ensurepip ou accès réseau n’est déclenché dans cette branche. Les contrôles de Python, environnement isolé, Tcl et copie/interruption/reprise restent exécutés ; un ancien rapport ready ne remplace pas ces contrôles.

Le rapport expose sharing_reused et sharing_install_attempted, tous deux initialisés à false. Un complément conforme déjà présent donne réutilisation, sans prétendre à une nouvelle installation réussie. En cas de version différente, absente ou inutilisable, la préparation normale tente toujours l’installation de la version attendue ; hors ligne, ou après échec réseau, elle conserve les copies/réception prêtes avec un statut partiel. Les paquets ne sont pas supprimés automatiquement. Le contrôle de version s’applique à l’annonce de préparation du complément ; il ne remplace ni ne modifie l’authentification ou la validation TLS des transferts.

Parcours source : extraire → Installer_Windows.bat → lancement. Une relance avec le complément déjà conforme n’a plus besoin de joindre un dépôt de paquets. La première installation et une réparation/version différente peuvent encore nécessiter Internet. Cette archive n’intègre pas de Python Windows autonome ; l’EXE nécessite toujours un véritable poste de construction Windows.

## Validations réelles

Compilation Python et helper C++ Linux réussies ; **195 tests Linux réussis, aucun ignoré**. Cinq nouveaux tests : complément utilisable réutilisé sans aucune commande de module pip, reprise moteur toujours contrôlée et rapport enregistré ; réutilisation hors ligne ; version incorrecte refusée hors ligne ; version incorrecte ou import cassé déclenchant une tentative d’installation avec maintien des copies lors d’échecs injectés. Venv et sous-processus Python/Tcl réels. Les fixtures de complément sont exposées par un fichier .pth vers cryptography 50.0.2 et les dépendances CFFI installées du banc : ce ne sont pas des téléchargements ou installations Windows. Versions incorrectes/imports cassés et échecs pip sont simulés explicitement, sans changer les paquets sources.

Contrôle HTTPS ultra réel en boucle locale Linux : 259 fichiers, dont un de 64 Mio et 256 petits, Unicode/cachés/vides. Arrêt puis reprise de 8 388 608 octets, quatre workers, inventaire et SHA-256 indépendants, source conservée ; 1,155 s sur cette exécution avec caches chauds, élagage du sélecteur activé explicitement. Contrôle local 1 Gio : 2,455 s, bloc synthétique répété, fsync demandé et vérifications incluses, SHA-256 indépendant. Ces contrôles ne mesurent aucun gain causal de débit.

Le wheel 0.3.16 a été construit puis installé séparément et importé depuis cette installation. Copie Unicode/vides et empreinte indépendante réussies ; contrôle embarqué local sans GUI réussi avec 65 536 octets repris. Rapport : reports/installed-wheel-0.3.16.json. prepare_installation.py a aussi été compilé explicitement avec py_compile ; le script source est livré dans le ZIP, pas dans le wheel.

## Mesure comparative de préparation répétée

Six répétitions alternées par variante, même venv existant, même complément déjà disponible par fixture .pth. Ancienne préparation 0.3.15 archivée et préparation actuelle ; contrôles moteur/Tcl/copie/reprise inclus. Venv initial et fixture commune exclus, caches chauds. Pip de référence réellement exécuté mais **install forcé --no-index** : aucun téléchargement, index ni latence réseau dans la mesure. Le pip du banc est importable via la fixture existante. Il s’agit d’une comparaison de la logique de préparation sous Linux, pas des scripts .bat, du premier lancement visuel ou de la première installation Windows.

| Préparation | Médiane | Minimum–maximum | Appels pip par essai |
|---|---:|---:|---:|
| 0.3.15 | 0,71167 s | 0,67099–0,86816 s | 2 |
| 0.3.16 | 0,14315 s | 0,13784–0,15743 s | 0 |

La réduction mesurée est le coût évité de deux appels pip quand le complément est déjà conforme. Aucun délai universel ni gain de transfert/compression revendiqué. Tous les résultats : reports/setup-reuse-0.3.16.json ; référence : history/v0.3.15/prepare_installation.py.

## Reproduire et limites

Avec le complément facultatif de test installé : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_setup_reuse`, `python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.16.json`, `python3 verify_gib.py`. Le banc et les nouveaux tests utilisent les chemins des modules cryptography/CFFI de l’interpréteur appelant pour la fixture locale ; ils ne téléchargent rien.

Moteur, GUI, réseau, partage, codecs et construction Windows inchangés, comparaison octet pour octet : reports/unchanged-core-0.3.16.json. Les mesures historiques de compression sont conservées, modes expérimentaux toujours facultatifs et désactivés par défaut. Aucun algorithme nouveau.

Linux sans DISPLAY/Xvfb/Wine, Windows ni hôte RDP connecté : aucune validation visuelle, aucun EXE/installateur Windows construit ou testé. Sources et wheel Python livrés. Premier lancement, raccourcis, mise à niveau et suppression sous Windows restent à vérifier réellement. Pas de support USB physique ni réseau entre deux postes. RDP natif RDC/MSTSC et manifeste authentifié inter-transports restent à développer. ACL, flux NTFS alternatifs et attributs étendus non copiés.

---

# Rapport — UltraTransfert 0.3.15

15 novembre 2026. Archive actuelle récupérée : 0.3.14, version persistante 17. Même identité, remplacement avec garde effective. Cycle borné : rendre Interrompre utilisable dès l’inventaire initial des copies locales.

## Correction et parcours

Le moteur possédait déjà un inventaire annulable, mais l’interface construisait LocalSource sans lui transmettre son signal d’arrêt. Un clic pendant l’inventaire laissait donc l’énumération complète se poursuivre. Le worker graphique transmet désormais ce signal. Une OperationCancelled pendant cette préparation produit « Inventaire interrompu » et propose Reprendre si l’utilisateur a demandé l’arrêt. Une erreur réelle, même simultanée à l’arrêt, reste une erreur ; une annulation inattendue n’est pas annoncée comme un arrêt utilisateur réussi.

Pendant l’inventaire local : Interrompre → attendre le résultat → Reprendre avec les mêmes dossiers. Si l’inventaire est annulé, le moteur de copie n’est pas lancé : aucune création de destination/état et aucune modification d’une destination préexistante. Une reprise après cette annulation refait l’inventaire complet nécessaire ; aucun bloc n’a encore été copié dans cette tentative. Les règles habituelles de reprise par contenu des tentatives ayant déjà copié restent identiques.

Ce raccordement concerne ordinateur, USB et chemins réseau ou lecteurs redirigés montés utilisables comme dossiers. Le mécanisme est coopératif : un appel système de lecture/lstat/resolve déjà engagé, l’énumération et le tri d’un grand dossier peuvent retarder la confirmation. Ce n’est pas une interruption forcée d’entrée/sortie. La préparation HTTPS n’est pas modifiée et conserve ses délais réseau. Aucun nouveau port, droit ou transport.

## Validations

Compilation Python et helper C++ Linux réussies ; **190 tests Linux réussis, aucun ignoré**. Cinq nouveaux tests : arrêt pendant un inventaire réel, arrêt avant l’inventaire, reprise réelle puis SHA-256 indépendant de tous les fichiers, Unicode/caché/dossier vide, destination existante intacte sans nouvel état. Les erreurs de permission et annulation inattendue sont injectées pour vérifier leur priorité : ce sont des simulations. Contrôleur et widgets doublés, pas de rendu visuel réel.

Contrôle HTTPS ultra réel en boucle locale : 259 fichiers, dont 64 Mio et 256 petits fichiers, Unicode/cachés/vides, arrêt puis reprise de 8 388 608 octets avec quatre workers. Inventaire et SHA-256 indépendants, source conservée ; 1,365 s sur cette exécution avec caches chauds, sans plafond réseau et élagage du sélecteur explicitement activé. Contrôle local 1 Gio : 2,575 s, bloc synthétique répété, fsync demandé, contrôles moteur et SHA-256 indépendant. Pas une comparaison de débit et pas un support physique.

Le wheel 0.3.15 a été construit et installé séparément ; les cinq nouveaux tests ont été réexécutés en important exclusivement cette installation. Le contrôle embarqué local sans GUI réussit aussi, avec 65 536 octets repris. Voir reports/installed-wheel-0.3.15.json et son journal. Ce contrôle n’est pas une validation Windows.

## Comparaison reproductible d’arrêt

Inventaire réel de 3 000 minuscules fichiers Unicode sous Linux, six répétitions alternées entre contrôleur 0.3.14 archivé et nouveau contrôleur. Même demande d’arrêt au vingtième point de contrôle, widgets doublés et caches chauds. Temps jusqu’au résultat traité par le contrôleur (aucune latence de rendu Tk incluse).

| Mesure médiane | 0.3.14 | 0.3.15 |
|---|---:|---:|
| Points de contrôle parcourus | 3 008 | 20 |
| Début de tentative → résultat | 192,420 ms | 3,454 ms |
| Demande d’arrêt → résultat | 189,686 ms | 0,682 ms |

La nouvelle préparation annulée n’a créé aucune destination dans les six répétitions ; les octets de toutes les sources ont été vérifiés après les douze essais. Le gain mesuré correspond à du travail d’inventaire évité après l’arrêt demandé. Ce n’est ni un gain de copie/compression, ni une garantie de délai d’arrêt sur un support lent. Toutes les durées et points de contrôle : reports/copy-inventory-stop-0.3.15.json.

## Reproduction et limites

`python3 build.py` ; `python3 -m unittest discover -s tests -v` ; `python3 -m research.benchmark_copy_inventory_stop` ; `python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.15.json` ; `python3 verify_gib.py`. Suite complète exécutée avec cryptography 50.0.2 en chemin isolé pour les tests de partage. Référence du contrôleur : history/v0.3.14/ultra/gui.py. Moteur, réseau, codecs, partage, préparation et construction Windows identiques à la référence : reports/unchanged-core-0.3.15.json. Les mesures de compression antérieures sont conservées ; aucune nouveauté algorithmique ou accélération générale revendiquée.

Environnement Linux sans DISPLAY/Xvfb/Wine, machine Windows ou hôte RDP connecté. Pas de validation visuelle ni EXE/installateur Windows construit. Scripts et futur portable Windows restent à tester réellement. La livraison est une archive source avec wheel Python ; l’utilisateur Windows a encore besoin de Python pour ces sources. Canal RDP natif et manifeste authentifié de reprise inter-transports restent à développer. Métadonnées : ACL, flux NTFS alternatifs et attributs étendus non copiés.

---

# Rapport — UltraTransfert 0.3.14

15 novembre 2026. État récupéré avant modification : archive 0.3.13, version persistante 16 ; même identité conservée, remplacement avec la garde réellement reçue. Cycle borné consacré au résultat utilisateur, sans changement de moteur ou de transport.

## Ce qui est plus simple et défaut corrigé

Le bouton **Voir le bilan** ouvre un résumé français, défilant et en lecture seule : destination effectivement utilisée, résultat de la tentative, compteurs copiés/identiques, données reprises pour les fichiers achevés, durée du moteur et action après erreur/interruption. Les détails d’erreur très longs sont abrégés en conservant le début et la fin, où figure l’action proposée. Les empreintes individuelles ne sont plus présentées en JSON dans cette fenêtre.

Auparavant, le clic relisait intégralement last-result.json depuis la destination dans le fil graphique. Un lecteur réseau lent pouvait bloquer ce clic ; après un échec avant l’écriture d’un nouveau rapport, un ancien JSON de réussite pouvait rester et être montré à la place du résultat courant. Désormais, le worker capture seulement les compteurs à son retour, sans parcourir/copier la table d’empreintes, avant l’événement terminal. L’interface réinitialise cette capture à chaque tentative. Si le moteur n’a pas rendu de résultat, le bilan explique qu’aucun rapport complet courant n’est disponible, avec l’erreur actuelle. Le clic ne fait aucun accès disque ou réseau.

Le bilan décrit le résultat à la fin de tentative : **ce n’est pas une nouvelle vérification des fichiers**. Il disparaît après fermeture de l’application. Le rapport technique complet et ses SHA-256 restent écrits par le moteur sans changement ; le bilan en indique l’emplacement habituel « si enregistré », sans supposer sa présence ni sa fraîcheur. Ouvrir ce fichier manuellement peut montrer un ancien résultat : seul le résultat courant est utilisé par l’interface.

## Validations réelles

Compilation Python et helper C++ Linux réussies. **185 tests réussis, aucun ignoré**, dont neuf nouveaux : rendu français/Unicode, validation prudente des compteurs, absence de faux succès après arrêt/erreur, erreur longue bornée avec action finale, absence d’accès fichier au clic sur chemin de forme tsclient, fenêtre désactivée pendant la copie, capture sans parcourir une table factice d’un million d’empreintes. Deux parcours utilisent le moteur réel avec widgets doublés : ancienne réussite suivie d’une modification d’inventaire source et d’un échec de préparation ; copie de 4 Mio interrompue puis reprise avec SHA-256 indépendant. Les autres tests conservent les contrôles de conflits, corruption, source modifiée, manque d’espace simulé, droits simulés et TLS/authentification. Le chemin tsclient est un texte dans ces tests : aucun essai RDP réel.

Contrôle HTTPS ultra réel en **boucle locale Linux** : 259 fichiers dont un de 64 Mio, 256 petits fichiers, caché et vide, noms Unicode et dossier vide. Interruption à 8 Mio, partiel non publié, reprise de 8 388 608 octets avec quatre workers, inventaire et SHA-256 indépendants, source conservée ; 1,222 s pour l’ensemble chronométré. Sélecteur avec élagage explicitement activé pour ce contrôle. Aucune comparaison de débit dans ce test d’intégrité.

Contrôle local indépendant de **1 Gio** réussi en 2,543 s, bloc pseudo-aléatoire répété, caches chauds, fsync demandé et vérifications moteur incluses. Empreinte finale indépendante identique à l’attendue. Ni support physique USB, ni débit universel, ni gain de performance moteur revendiqué.

Le wheel 0.3.14 a été construit, installé séparément puis importé depuis cette installation. Contrôle embarqué local sans GUI : réussite et 65 536 octets repris. Copie Unicode/vides et rendu du nouveau résumé également contrôlés depuis le paquet installé ; rapport reports/installed-wheel-0.3.14.json. Ce contrôle Linux non figé n’est pas une validation de portable Windows.

## Comparaison de préparation du bilan

Six répétitions par taille/variante, ordre alterné, métadonnées synthétiques Unicode, cache local chaud. Ancienne opération : lecture UTF-8 du JSON complet à afficher ; nouvelle : capture de compteurs et formatage du résumé courant, sans lecture fichier. Les textes affichés diffèrent volontairement. Tracemalloc actif ; génération/écriture de la fixture exclues. Pas de Tk, de temps d’ouverture visuel, de latence réseau ni de copie de fichiers mesurés.

| Empreintes dans le rapport | Ancien JSON médiane | Nouveau résumé médiane | Pic d’allocation médian ancien / nouveau |
|---|---:|---:|---:|
| 0 | 0,029 ms | 0,079 ms | 6 979 / 2 744 octets |
| 1 000 | 0,149 ms | 0,090 ms | 403 120 / 2 780 octets |
| 100 000 | 10,226 ms | 0,133 ms | 40 363 080 / 2 788 octets |

Le formatage est plus lent qu’une minuscule lecture locale à zéro fichier ; le coût reste inférieur au quart de milliseconde sur ce banc. Le bénéfice principal est l’absence structurelle d’une lecture réseau au clic et d’un résumé périmé. La table complète d’empreintes demeure dans le moteur pour l’intégrité ; les chiffres sont les allocations supplémentaires de préparation du bilan, pas la mémoire totale. Min/max et tous les essais : reports/report-view-0.3.14.json.

## Reproduction et limites

Commandes : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_report_view --rounds 6`, `python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.14.json`, `python3 verify_gib.py`. Les tests de création de connexions utilisent cryptography 50.0.2 en chemin isolé ; cette dépendance reste facultative pour le moteur.

Moteur, codecs, débit contrôlé, partage et construction Windows identiques octet pour octet à la référence : reports/unchanged-core-0.3.14.json. Historique utile : history/v0.3.13. Compression ultra et élagage restent expérimentaux, facultatifs et désactivés par défaut ; aucune nouvelle comparaison de compression ou nouveauté algorithmique.

Environnement Linux sans DISPLAY, Xvfb, Wine, Windows ou hôte RDP connecté. Aucune validation visuelle, aucun EXE/installateur Windows compilé, aucun test physique USB/réseau entre deux machines. Sources et wheel Python livrés ; ce n’est pas un portable Windows autonome. Le parcours installation → lancement visuel → copie → reprise → résultat devra être exécuté sous Windows. Canal RDP natif RDC/MSTSC et manifeste authentifié de reprise inter-transports restent à développer. ACL, flux NTFS alternatifs et attributs étendus restent non copiés.

---

# Rapport — UltraTransfert 0.3.13

15 novembre 2026. État récupéré avant modification : archive 0.3.12, version persistante 15. Même identité, garde de remplacement effectivement reçue. Cycle borné consacré au coût du sélecteur de compression expérimental, avec décision finale conservatrice : **optimisation facultative, désactivée par défaut**.

## Code livré et utilisation

Option serveur **--selection-pruning**, seulement avec --compression ultra. API correspondante : adaptive_frame(..., prune=True), AdaptiveEncoder(..., prune=True) et make_server(..., selection_pruning=True). Le parcours habituel n'ajoute aucun réglage et continue d'utiliser la sélection complète. Pas de nouveau codec, de dépendance ou d'IA obligatoire ; pas de changement de l'interface d'installation/copie.

Après encodage d'un candidat sur l'échantillon, l'encodage mesuré et la taille de transport estimée forment une borne inférieure. Si elle atteint déjà le score d'un candidat dont l'échantillon a été décodé/vérifié, la recherche peut écarter cette recette : son coût de reconstruction positif ne peut améliorer ce score. Le premier candidat est toujours évalué complètement, y compris aux valeurs extrêmes de débit qui produisent une estimation infinie. Le candidat retenu n'est jamais élagué.

Il s'agit d'une borne du modèle local de sélection, **pas d'une preuve de meilleur temps réseau réel**. L'échantillon peut ne pas représenter le fichier, les mesures CPU peuvent fluctuer et le destinataire peut avoir un autre processeur. Les recettes non retenues ne sont pas transmises. Aucune vérification des blocs reçus, SHA-256, taille maximale, terminal ou fichier final n'est retirée. Les diagnostics des candidats écartés portent pruned=true et estimate_is_lower_bound=true ; estimated_seconds représente alors une borne, pas un coût complet mesuré.

## Résultats CPU et décision

Six blocs synthétiques d'environ 2 Mio, sept répétitions en ordre mélangé, débits estimés 50/1000 Mbit/s, 588 essais avec ancien/nouveau sélecteur et références raw/zlib1/Zstd1/Zstd3/Zstd3+permutation4. Le coût médian de recherche baisse de **3,3 à 27,3 %** sur les douze situations. Exemple déjà gzip à 1000 Mbit/s estimés : **6,469 → 5,625 ms** de sélection. Mais le CPU complet encodage/reconstruction régresse d'environ **7,0 % sur le compteur uint32 à 50 Mbit/s**, et de 1,7 % sur le signal float32 à ce même débit. Les choix et chronométrages peuvent varier ; aucun gain global garanti.

Les durées réseau de ce banc CPU sont uniquement des estimations séquentielles. Pas de disque/TLS/réseau/RDP dans ce banc. Tous les blocs reconstruits correspondent aux octets d'origine. Résultats, bornes CPU, recettes et compteurs : reports/selection-0.3.13.json.

## HTTPS réel en boucle locale

Banc final : **240 copies réussies**, trois jeux synthétiques d'environ 8 Mio, huit méthodes, cinq répétitions, ordre mélangé, plafonds applicatifs 50/1000 Mbit/s. Références fixes étendues aux niveaux Zstd 1 et 3, avec/sans permutation4, plus gzip1 et brut. Le sélecteur 0.3.12 est exécuté dans le même moteur/serveur courant. L'option est activée explicitement pour la seule méthode ultra du prototype ; les références fixes et historiques ne l'utilisent pas.

Total médian en secondes = inventaire/hachage/configuration TLS serveur + manifeste/TLS client + sélection/compression/métadonnées + transport + reconstruction/écriture/fsync et vérifications moteur. Aucun dictionnaire. Génération du certificat commun de fixture, création des données, arrêt serveur, installation/actions humaines et SHA-256 indépendant supplémentaire exclus. Cet ultime contrôle indépendant est bien exécuté pour chaque copie. Caches chauds Linux ; pas de RTT/pertes, support physique ou hôtes distincts.

| Données synthétiques | Plafond Mbit/s | Brut | Sélecteur 0.3.12 | Option élagage | Meilleure compression fixe testée |
|---|---:|---:|---:|---:|---:|
| Signal float32 | 50 | 1.3802 | 0.7534 | 0.7517 | 0.7433 (zstd3-shuffle4) |
| Signal float32 | 1000 | 0.1028 | 0.1125 | 0.1187 | 0.1070 (zstd1-shuffle4) |
| Journaux puis aléatoire | 50 | 1.3807 | 0.7651 | 0.7608 | 0.7497 (zstd3) |
| Journaux puis aléatoire | 1000 | 0.1034 | 0.1030 | 0.0967 | 0.0933 (zstd3) |
| Déjà gzip | 50 | 1.3844 | 1.4073 | 1.4078 | 1.4032 (zstd3) |
| Déjà gzip | 1000 | 0.1029 | 0.1328 | 0.1317 | 0.1244 (zstd1) |

À 1000 Mbit/s, les journaux mixtes passent de 0,1030 à 0,0967 s, mais le signal passe de 0,1125 à 0,1187 s (**+5,48 %**). Déjà gzip à 50 Mbit/s reste pratiquement identique et plus lent que le brut. Les bonnes recettes fixes restent meilleures que le prototype sur ces données ; les min/max de plusieurs groupes se chevauchent. **Pas de bénéfice général établi : l'élagage ne remplace donc pas le comportement par défaut**, même à l'intérieur du mode ultra facultatif. Ce choix conserve les fonctions existantes tout en permettant une expérience reproductible explicite.

Le premier essai, avant ajout de l'activation explicite, avait 180 copies et moins de références fixes ; il montrait aussi des régressions sur plusieurs médianes. Ses mesures sont conservées dans reports/https-compression-initial-0.3.13.json et selection-initial-0.3.13.json ; les tableaux ci-dessus viennent du banc final. Pas de suppression des résultats défavorables, pas de nouveauté algorithmique revendiquée. Les limites/compteurs de trames restent ceux de COMPRESSION_HTTPS.md.

## Validation et reproduction

**176 tests Linux réussis** (170 précédents + six nouveaux) : borne sous horloge contrôlée, candidat potentiellement meilleur encore décodé, corruption d'un candidat potentiellement retenu rejetée, cas vides/non alignés/débits extrêmes/négociation, absence d'activation par défaut et option refusée hors ultra. Les tests TLS adaptatifs existants activent maintenant l'option : reprise, delta, erreurs de trame, client sans Zstd et retour au brut restent contrôlés. Compilation Python et helper C++ Linux ; fixtures cryptography 50.0.2.

Contrôle mixte supplémentaire avec option explicitement activée : **64 Mio + 256 petits fichiers mixtes**, Unicode/cachés/vides, interruption/reprise de 8 388 608 octets, inventaire/SHA-256 indépendants et source conservée (259 fichiers), **1,4271 s**. Contrôle local de 1 Gio : **2,5394 s**, somme indépendante correcte, caches chauds/fsync demandé. Ce sont des contrôles de robustesse, pas une mesure de gain local entre versions. Moteur, limite de copie, préparation hors ligne et fonctions de décodage/framing inchangés : reports/unchanged-guarantees-0.3.13.json.

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_selection
python3 -m research.benchmark_https_compression --rounds 5 --mbps 50 1000 --selection-pruning --reference history/v0.3.12/ultra/compression.py --output reports/https-compression-0.3.13.json
python3 -m research.verify_mixed_https --selection-pruning --output reports/mixed-https-0.3.13.json
```

Activation avancée côté serveur : ajouter --selection-pruning à la commande serve déjà configurée avec certificat, clé, jeton, --compression ultra et --link-mbps. Le client garde --compression ultra ; TLS, nom d'hôte et authentification restent obligatoires. Les fichiers utilisateur n'ont aucun paramètre de recette à fournir.

Le wheel 0.3.13 construit puis installé séparément est importé depuis cette installation : aller-retour avec/sans option et contrôle copie/reprise réussis. Rapport reports/installed-wheel-0.3.13.json (frozen=false, gui_created=false). Cela ne valide pas un EXE Windows.

## Limites de plateforme

Pas de Windows/Wine, affichage/Xvfb ou hôte RDP accessible. Aucun EXE/installeur Windows construit, aucun parcours visuel/Windows ou RDP réel validé. La livraison reste source avec paquet Python. DVC natif RDC/MSTSC, lecteurs tsclient réels, réactivité de session et manifeste authentifié indépendant des transports restent à développer/valider. ACL, flux NTFS et attributs étendus non conservés. Vision entreprise archivée abandonnée.

---

# Rapport — UltraTransfert 0.3.12

15 novembre 2026. Archive actuelle récupérée avant modification : 0.3.11, version persistante 14. Remplacement avec la garde effectivement reçue, sous la même identité. Cycle borné consacré à la préparation source hors ligne et à la dégradation explicite si un complément manque.

## Plus simple à préparer

Installer_Windows.bat délègue maintenant à prepare_installation.py : environnement .venv-run isolé, contrôle moteur/Tcl/copie/interruption/reprise avant de déclarer le moteur prêt, puis complément de création des connexions facultatif. Le préparateur affiche trois étapes. Un échec pip/téléchargement ne bloque plus le lancement des copies ou de la réception HTTPS lorsque le contrôle du moteur a réussi.

**Installer_sans_Internet.bat** est prévu pour une préparation sans réseau : Python 3.10+ avec tkinter doit déjà être présent. Sinon il s'arrête avant WinGet. Aucun pip, ensurepip ou téléchargement n'est tenté dans ce mode. Le lanceur normal reste Lancer_UltraTransfert.bat. Une préparation normale peut ajouter le complément ensuite en relançant Installer_Windows.bat avec Internet, sans demander de commandes à l'utilisateur.

Un avis français dans l'interface indique le résultat partiel enregistré : copies et réception disponibles, nouvelle connexion demandant le complément ; une connexion privée conservée reste rechargeable. Cet avis est informatif et dépend du dernier rapport d'installation, pas une autorisation de transfert ni une détection permanente des paquets. Après une réparation manuelle, relancer la préparation pour l'actualiser.

## Mécanisme et garanties

Le venv est créé sans pip. Le contrôle vérifie Python >=3.10, sys.prefix dans l'environnement attendu, import tkinter/Tcl et une vraie copie synthétique de 2 Mio avec interruption/reprise/SHA-256. Cela ne crée pas de fenêtre Tk et ne valide pas le rendu. POSIX utilise les liens d'interpréteur habituels de venv ; le premier essai par copie d'interpréteur avait perdu l'accès à une bibliothèque Tcl de cet hôte, ce qui a été détecté et corrigé sans supprimer le contrôle. La branche Windows utilise le comportement prévu de venv, non testé sur Windows.

La préparation normale initialise pip si nécessaire puis installe requirements-sharing.txt avec roues binaires uniquement, timeout réseau et sans retry ; chaque sous-processus a une échéance. Les imports cryptographiques sont contrôlés ensuite. sharing_ready décrit ces imports, pas une garantie générale de création de certificats. Le futur portable conserve ses contrôles de génération/rechargement/TLS obligatoires et n'est pas construit ici.

Rapport reports/installation.json, journaux installation-core.log, installation-pip.log et installation-sharing.log selon les étapes. Aucun certificat/clé/jeton ni service n'est créé par ce préparateur. Rapport écrit via un fichier temporaire neuf puis remplacement ; partiel possédé nettoyé en cas d'échec, partiel préexistant conservé et signalé. Un verrou préexistant n'est jamais supprimé. Un environnement inconnu/incomplet est refusé sans effacement : conserver les fichiers et extraire une nouvelle copie propre du ZIP. Pas d'installation globale de paquets Python. Les diagnostics peuvent contenir chemins/erreurs de configuration et méritent relecture avant transmission.

## Validations réelles

**170 tests Linux réussis** (159 précédents + onze nouveaux). Venv réel sans pip et sans cryptography, contrôle moteur/reprise avec Tcl, réutilisation, téléchargement et ensurepip absents simulés sans perte de disponibilité du moteur, échec moteur bloquant, environnement inconnu préservé, manque d'espace simulé, verrou préexistant conservé, avis invalides/excessifs ignorés, rapport temporaire préexistant conservé, échec d'écriture nettoyé et codes CLI partiel/succès vs erreur moteur. Plusieurs contrôles sont regroupés par test. Compilation Python et helper C++ Linux ; fixtures cryptography 50.0.2 pour le reste de la suite. Pas de tests batch ou visuels Windows.

Banc réel, six couples neufs/réutilisés hors ligne, dans des chemins temporaires avec espaces/Unicode sous Linux : préparation neuve médiane **0,17366 s**, min–max 0,14977–0,23903 ; réutilisation médiane **0,15257 s**, min–max 0,14002–0,20390. Inclut création du venv si neuf, contrôle d'isolation/Tcl, copie/reprise de 2 Mio et SHA-256, vérification d'import optionnel et écriture du rapport. Source de fixture copiée avant chronométrage, caches chauds et bytecode favorisant la réutilisation ; neuf puis réutilisé par couple, pas d'ordre aléatoire. Ce n'est pas une mesure de WinGet, Windows, EXE, démarrage visuel ou débit de copie.

Une tentative réelle séparée d'ajout du complément en ligne a réussi : **15,72848 s**, bootstrap pip, installation de cryptography et dépendances, imports prêts. Ensuite, création et rechargement d'une connexion privée vérifiés dans cet environnement isolé, sans serveur. Une seule tentative : aucune comparaison de vitesse généralisable. Les douze préparations hors ligne ont toutes réussi avec core_ready=true et sharing_ready=false ; les secrets de la vérification en ligne étaient temporaires et ne sont pas livrés.

Régressions : HTTPS ultra loopback, 64 Mio + 256 petits fichiers mixtes, Unicode/cachés/vides (259 fichiers), interruption puis reprise de 8 388 608 octets, inventaire/empreintes indépendants et source conservée, **2,3674 s** pour ce contrôle. Copie locale **1 Gio en 4,2466 s** avec somme indépendante, caches chauds/fsync demandé. Aucun gain de débit revendiqué. Moteur, transport, limite de copie, compression et garanties inchangés (reports/unchanged-core-0.3.12.json).

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_installation --online-check
python3 -m research.verify_mixed_https --output reports/mixed-https-0.3.12.json
python3 verify_gib.py
```

prepare_installation.py --offline est destiné à l'extraction source courante ; il respecte .cycle.lock et ne doit pas être lancé pendant un autre cycle. Le banc travaille dans des copies temporaires distinctes. Mesures complètes : reports/installation-0.3.12.json. Sources modifiées précédentes : history/v0.3.11.

Le test de préparation hors ligne reçoit aussi réellement un fichier en HTTPS dans le venv sans pip/cryptography, depuis un serveur de fixture : validation TLS et SHA-256 indépendant réussis. Le serveur de fixture utilise le complément dans le processus parent ; le destinataire isolé n’en dispose pas.

Le wheel 0.3.12 a été construit, installé séparément et importé depuis cette installation : avis de préparation partielle et contrôle moteur copie/reprise réussis. Rapport reports/installed-wheel-0.3.12.json, frozen=false et gui_created=false, sans preuve Windows.

## Limites

Pas de Windows/Wine, affichage/Xvfb ni hôte RDP accessible. Scripts d'installation/WinGet/pythonw, Tcl/Tk Windows, premier lancement visuel, mise à niveau et désinstallation non validés sur Windows. Aucun EXE/installeur construit : archive source avec paquet Python. L'absence de Python ne peut pas être résolue hors ligne par cette archive ; le futur portable autonome reste à construire et tester sur Windows.

DVC natif RDC/MSTSC, lecteurs tsclient réels, mesure de réactivité RDP et manifeste authentifié de reprise inter-transports restent à développer/valider. Compression ultra expérimentale facultative, sans nouveau gain revendiqué ; ACL/flux NTFS/attributs étendus non conservés. Vision entreprise archivée abandonnée.

---

# Rapport — UltraTransfert 0.3.11

15 novembre 2026. État récupéré avant modification : archive 0.3.10, version persistante 13. Même identité et garde de remplacement effectivement reçue. Cycle borné consacré à une limite volontaire de vitesse de copie, utile à essayer sur les lecteurs RDP redirigés et partages réseau autorisés.

## Ce qui devient plus simple

Dans **Réglages avancés**, choisir **Vitesse maximale de copie (Mo/s)** : Sans limite (défaut), 1, 5, 10, 25 ou 50. Une limite commune couvre tous les fichiers en parallèle ; quatre workers ne multiplient pas la consigne par quatre. Le réglage est figé pendant la copie. Pour le modifier : Interrompre, attendre le résultat, changer la limite puis Reprendre avec les mêmes dossiers. La reprise peut conserver son état puisque les réglages ne changent pas le manifeste de source.

CLI : `python3 -m ultra copy SOURCE DESTINATION --limit-mb-s 5` ; même option pour pull. 1 Mo = 1 000 000 octets. Le rapport JSON enregistre max_bytes_per_second. La limite et le helper natif simultanés sont refusés avec une action claire, plutôt que de laisser le helper dépasser le réglage.

## Portée et garanties

Le moteur cadence le traitement des octets lus à la source pour copier, comparer les préfixes partiels et calculer une empreinte source d'un fichier déjà présent. Un échéancier monotone unique est partagé entre workers, avec attente interruptible hors verrou. Le nombre d'octets réellement lu est facturé, pas une taille de tampon fictive en fin de fichier. Aucune allocation ou file de tâches non bornée n'est ajoutée. Le code utilise le moteur Python et ne réclame pas d'IA.

**Ce n'est pas un plafond du trafic physique ni de toutes les E/S.** Les lectures anticipées, blocs de décompression, TLS/sockets et tampons peuvent produire des pointes. Inventaire, préparation du serveur, contrôle du protocole, indexation delta et relectures de vérification de la destination ne sont pas cadencés par cette option. Si la destination est un lecteur RDP, sa relecture finale peut donc encore solliciter la session. Le réglage ralentit volontairement le traitement de copie ; aucun meilleur débit ou gain de réactivité RDP n'est démontré ici.

Aucun contrôle supprimé : conflits sans écrasement, source conservée, préfixe comparé, SHA-256 des partiels et après publication, source/inventaire final et erreurs demeurent obligatoires. L'annulation pendant l'attente laisse les partiels validables ; la reprise peut utiliser une autre consigne. Formats, codecs et authentification HTTPS inchangés.

## Tests et mesures réels

**159 tests Linux réussis** (152 précédents + sept nouveaux). Nouveaux cas : échéancier global/temps virtuel sans attente sur EOF, attente sans verrou et annulation, valeurs invalides/helper natif refusés, interruption dans le cadencement puis reprise à une autre limite, empreinte d'un fichier déjà présent cadencée, consigne GUI capturée et CLI avec rapport/intégrité. Le test HTTPS ultra d'interruption/reprise préexistant utilise maintenant deux limites différentes. Widgets doublés, pas de validation visuelle.

Banc : **36 copies réussies**, trois répétitions par variante, ordre mélangé, source synthétique de 8 Mio répartis dans quatre fichiers, fichier/dossier vides et noms Unicode. Un ou quatre workers, sans limite, 4 ou 16 Mo/s, local ou TLS loopback sans compression, Linux et caches chauds. Médianes :

| Parcours | Parallélisme | Sans limite (s) | 4 Mo/s (s ; Mo/s mesurés) | 16 Mo/s (s ; Mo/s mesurés) |
|---|---:|---:|---:|---:|
| local | 1 | 0.0327 | 2.1565 ; 3.890 | 0.5729 ; 14.643 |
| local | 4 | 0.0212 | 2.1110 ; 3.974 | 0.5364 ; 15.640 |
| https | 1 | 0.0658 | 2.2054 ; 3.804 | 0.6155 ; 13.630 |
| https | 4 | 0.0557 | 2.1396 ; 3.921 | 0.5587 ; 15.013 |

Le temps inclut inventaire local ou manifeste/TLS client, préparation destination, copie/cadencement/écriture/fsync et vérifications moteur. La préparation commune du serveur HTTPS est mesurée séparément dans le rapport ; génération du certificat de fixture et SHA-256 supplémentaire indépendant exclus. Tous les résultats ont une empreinte indépendante correcte. Les moyennes globales restent sous la consigne, mais cette expérience ne mesure pas un plafond instantané sur le réseau. Aucun disque/USB physique, RTT/perte, Windows ou RDP réel. Ce n'est pas une comparaison de codecs ou un gain de compression.

Régressions supplémentaires, sans limite : copie locale de **1 Gio en 3,6071 s**, SHA-256 indépendant correct ; HTTPS ultra **64 Mio + 256 petits fichiers mixtes**, cachés/Unicode/vides (259 fichiers), interruption/reprise de **8 388 608 octets**, inventaire/empreintes indépendants et source conservée, **2,5670 s**. Caches chauds et fsync demandé, contrôles de robustesse sans revendication de gain de débit entre versions. La suite garde corruption, conflits, manque d'espace simulé, liens/collisions et erreurs réseau/TLS/droits.

Résultats : reports/pacing-0.3.11.json, tests-0.3.11.txt, mixed-https-0.3.11.json et one-gib-0.3.11.json. Les sources modifiées précédentes sont conservées dans history/v0.3.10.

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_pacing
python3 -m research.verify_mixed_https --output reports/mixed-https-0.3.11.json
python3 verify_gib.py
```

Le wheel 0.3.11 a été construit puis installé dans un dossier isolé. Import confirmé depuis cette installation ; copie limitée, somme indépendante et contrôle embarqué copie/reprise réussis. Rapport reports/installed-wheel-0.3.11.json, frozen=false et gui_created=false : ce n’est pas une validation Windows.

## Limites de plateforme

Environnement Linux sans Windows/Wine, affichage/Xvfb ou hôte RDP accessible. Aucun EXE/installeur Windows construit ; sources et paquet Python uniquement. Le rendu du nouveau réglage, l'installation, les raccourcis, la mise à niveau/désinstallation et le comportement réel sur tsclient restent à valider. Le mode lecteur redirigé n'est pas un canal RDP natif. DVC RDC/MSTSC, régulation mesurée de réactivité RDP et manifeste authentifié indépendant des transports restent à développer. ACL, flux NTFS et attributs étendus non conservés. Compression ultra facultative et désactivée par défaut, sans nouveauté revendiquée ; vision entreprise archivée abandonnée.

---

# Rapport — UltraTransfert 0.3.10

15 novembre 2026. Dernier état récupéré avant édition : UltraTransfert 0.3.9, version persistante 12. Identité conservée, remplacement avec garde de version reçue. Cycle borné consacré à l'annulation de la préparation d'un partage HTTPS.

## Parcours simplifié

Après **Partager ce dossier**, le bouton devient **Annuler la préparation** pendant l'inventaire et le hachage. Le clic demande un arrêt coopératif et affiche l'attente en cours ; on peut ensuite recommencer avec la même connexion et la même source. Fermer ce dialogue demande l'annulation puis attend sa confirmation avant destruction. Fermer la fenêtre principale demande l'annulation et invite à attendre le résultat puis à fermer de nouveau.

La création initiale des clés/certificats et le rechargement de connexion ne sont pas rendus annulables par ce changement. L'annulation concerne la préparation de la source au démarrage du partage, pas tous les inventaires de copies locales.

## Code et sécurité

Un signal d'annulation facultatif traverse ShareSession, LocalSource/inventory et make_server. Contrôles entre entrées, blocs de hachage, validation d'inventaire et ouverture du serveur ; le hachage delta est couvert aussi. Une exception d'annulation distincte reste compatible avec TransferError. Les erreurs de droits/configuration ne sont pas transformées arbitrairement en annulation.

Aucun inventaire/hachage/contrôle TLS n'est sauté lors d'une préparation achevée. Si l'annulation arrive juste après création de la socket, elle est fermée ; si elle arrive après l'événement interne prêt, le contrôleur arrête l'écoute et les connexions avant résultat, sans afficher PARTAGE OUVERT. Une écoute peut donc exister brièvement lors de cette course : pas de promesse d'absence absolue de socket après l'instant du clic. Une lecture, résolution de chemin, énumération/tri ou opération système déjà engagée peut retarder la prise en compte ; aucune borne universelle sur un support bloqué.

La résolution du chemin affiché précède l'ouverture du service, pour ne pas laisser une erreur de résolution survenir après démarrage. Aucun effacement de source, de configuration ou de journal de reprise. Pas de nouvelle permission, de pare-feu ouvert ou de transport ajouté.

## Validation réelle et mesures

**152 tests Linux réussis** (143 précédents + neuf nouveaux). Nouveaux cas : pré-annulation sans scan/socket, annulation pendant inventaire/hachage, fermeture de dialogue attendant confirmation, redémarrage puis copie TLS vérifiée, delta annulé, annulation juste après bind fermant la socket, événement prêt tardif, erreur réelle non masquée et fermeture principale demandant annulation. Widgets doublés : pas de rendu graphique validé. Compilation Python et helper C++ Linux ; fixtures cryptography 50.0.2.

Banc de six répétitions par variante, ordre alterné : source synthétique de 64 Mio, lectures et SHA-256 réels, caches chauds Linux. Demande d'annulation simulée exactement après lecture de 8 Mio. Ancien make_server archivé avec inventaire courant commun : il n'accepte pas d'annulation, lit les 64 Mio, crée l'écoute loopback immédiatement fermée sans servir. Nouveau : arrêt après 8 Mio, aucune écoute construite dans ce scénario. **56 Mio de lectures/hachage évités par essai**. Préparation médiane 65,17 → 10,75 ms ; délai médian après demande **58,56 → 3,44 ms**. Génération du certificat de fixture exclue. Ce sont des travaux évités sur une annulation, pas un meilleur débit de copie, un essai de disque lent ou une mesure RDP. Toutes les répétitions, min/max recalculables et empreinte source : reports/prepare-cancel-0.3.10.json.

Régressions supplémentaires : HTTPS ultra loopback, fichier de 64 Mio + 256 petits fichiers mixtes, Unicode/cachés/vides, interruption/reprise de 8 388 608 octets, inventaire/empreintes indépendants de 259 fichiers et source conservée : réussite en 2,3119 s pour cet essai de robustesse. Copie locale de 1 Gio vérifiée indépendamment en 3,5486 s, caches chauds et fsync demandé ; aucune comparaison de débit entre versions. La suite garde corruption, conflits, liens/collisions, modifications source, erreurs TLS/authentification et manque d'espace simulé.

Codecs, format de blocs, delta et SHA-256 final inchangés (reports/unchanged-codecs-0.3.10.json). Compression ultra expérimentale facultative, inactive par défaut ; pas de nouvelle expérience de compression ou nouveauté algorithmique revendiquée.

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_prepare_cancel
python3 -m research.verify_mixed_https --output reports/mixed-https-0.3.10.json
python3 verify_gib.py
```

Le contrôle mixte accepte maintenant --output (défaut reports/mixed-https.json) pour ne plus écraser un rapport versionné historique. Tests, rapports et sources modifiées précédentes dans history/v0.3.9 sont inclus.

Le wheel 0.3.10 construit puis installé dans un dossier isolé est importé depuis cette installation : pré-annulation et contrôle copie/reprise vérifiés. Rapport reports/installed-wheel-0.3.10.json (frozen=false, gui_created=false), sans valeur de preuve Windows.

## Limites

Pas de Windows/Wine, bureau graphique/Xvfb ni hôte RDP accessible. Sources et paquet Python, sans EXE/installeur Windows construit. Installation, pythonw, MessageBox, visuel, raccourcis, mise à niveau/désinstallation et RDP réels restent à valider. Lecteurs redirigés distincts du canal DVC natif RDC/MSTSC, toujours à développer, comme le manifeste authentifié indépendant des transports. La reprise actuelle reste liée à l'origine et aux métadonnées source. ACL, flux NTFS et attributs étendus non conservés. Aucune relance de la vision générale entreprise archivée.

---

# Rapport — UltraTransfert 0.3.9

15 novembre 2026. État actuel récupéré avant édition : archive 0.3.8, version persistante 11. Remplacement sous la même identité avec la garde effectivement reçue. Cycle borné consacré au premier lancement et aux erreurs compréhensibles.

## Ce qui devient plus simple

Le lanceur utilisé par le futur portable et par les scripts source Windows traite désormais les exceptions Python de lancement : message français, actions d'extraction/préparation, diagnostic personnel et code de sortie non nul. Sous Windows, le message utilise MessageBoxW sans dépendre de tkinter ; cette branche est simulée dans les tests, pas exécutée sur Windows. Le lanceur source préfère pythonw dans l'environnement préparé : pas de console permanente requise pour utiliser l'interface. Les cas archive incomplète et échec immédiat du démarrage proposent une action dans le script. Les scripts batch sont développés mais non exécutés ici.

Le diagnostic est créé sans écraser de fichier existant, dans %LOCALAPPDATA%\UltraTransfert\diagnostics sous Windows ou XDG_STATE_HOME/UltraTransfert/diagnostics sous Linux (sinon ~/.local/state). Fichier privé 0600 sur POSIX ; permissions Windows héritées du dossier personnel, non validées sur hôte réel. Trace limitée aux 65 536 derniers caractères et en-tête version/plateforme ; pas de capture des variables locales ou du contenu des fichiers copiés. Les messages et chemins peuvent contenir des informations personnelles : relire le diagnostic avant de le transmettre. En cas d'erreur d'écriture, le fichier partiel créé est retiré et le message donne une action espace/droits. Aucun journal précédent n'est effacé.

Le traitement commence une fois le code Python du lanceur chargé. Il ne répare pas un EXE/_internal absent, un interpréteur incapable de démarrer ou le bootloader PyInstaller. Ce n'est pas une capture générale des erreurs des transferts, déjà gérées par leur contrôleur.

## Validation réelle

**143 tests Linux réussis**, huit nouveaux : journal Unicode borné et distinct, confidentialité POSIX, échec d'écriture simulé sans partiel, emplacement impossible, codes de sortie, message natif Windows simulé sans tkinter, absence d'affichage/journal avec action de secours, maintien de la route --smoke-test, lancement réellement impossible sans DISPLAY avec diagnostic et sortie 1. Plusieurs assertions sont regroupées dans un même test. Compilation Python et helper C++ Linux réussie ; fixtures cryptography 50.0.2.

Banc reproductible : cinq démarrages par variante, ordre alterné, sous-processus Linux sans DISPLAY. Ancien et nouveau lanceurs importent le même paquet courant et rencontrent TclError. Ancien : 0/5 diagnostics ; nouveau : 5/5 diagnostics et messages avec action ; tous sortent avec code 1. Médiane ancien **0,1331 s**, nouveau **0,1488 s**, min–max 0,1078–0,1589 et 0,1025–0,1689 s. Surcoût médian descriptif d'environ 16 ms pour ce cas d'échec ; intervalles superposés, aucun gain de vitesse revendiqué. Ce n'est pas un démarrage visuel réussi, ni un EXE Windows. Le premier banc, qui chargeait involontairement le paquet historique partiel, a été corrigé puis entièrement réexécuté ; seules les mesures du banc corrigé sont conservées.

Régression de transfert : essai local **1 Gio en 2,5127 s**, SHA-256 indépendant correct, caches chauds/fsync demandé. HTTPS ultra réel en boucle locale : **64 Mio + 256 petits fichiers mixtes**, Unicode/cachés/vides, interruption puis reprise de **8 388 608 octets**, 259 fichiers/inventaire/empreintes indépendants et source conservée ; 1,3949 s pour ce contrôle de robustesse. Pas de comparaison de débit entre versions. La suite conserve corruption, conflits, espace insuffisant simulé, liens, source modifiée et refus d'authentification/TLS.

Moteur, client/serveur HTTPS, compression, décodage, delta et contrôleur GUI identiques aux sources récupérées : reports/unchanged-core-0.3.9.json. Aucune nouvelle mesure ni gain de compression revendiqué ; le mode ultra demeure expérimental facultatif, désactivé par défaut.

Reproduire :

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_startup --rounds 5
python3 -m research.verify_mixed_https
python3 verify_gib.py
```

Les deux derniers outils historiques écrivent par défaut mixed-https-0.3.8.json et one-gib.json ; les sorties de ce cycle ont été conservées sous les noms 0.3.9 et le rapport historique mixed-https-0.3.8 restauré. Mesures : reports/startup-0.3.9.json, mixed-https-0.3.9.json et one-gib-0.3.9.json. Sources précédentes modifiées : history/v0.3.8.

Le paquet Python 0.3.9 a été construit, installé dans un dossier isolé et importé depuis cette installation : diagnostic Unicode et contrôle embarqué copie/reprise réussis. Rapport installed-wheel-0.3.9.json, frozen=false et gui_created=false ; cela ne valide pas Windows.

## Limites

Aucun Windows/Wine, affichage graphique/Xvfb ou hôte RDP disponible. Pas d'EXE/installeur produit ni validé, de validation visuelle, de test réel MessageBoxW/pythonw/batch/raccourcis/mise à niveau/désinstallation. La livraison reste source avec paquet Python. Le portable sans Python utilisateur reste soumis à la construction et aux contrôles Windows prévus. Les diagnostics n'ajoutent aucun service ni partage et ne changent pas les politiques ou permissions RDP.

Canal natif RDC/MSTSC DVC, lecteurs tsclient réels, mesure de réactivité RDP et reprise inter-transports authentifiée restent à développer/valider. La reprise actuelle dépend encore de l'URL et des métadonnées source. ACL, flux NTFS et attributs étendus non conservés. Vision générale entreprise archivée abandonnée.

---

# Rapport — UltraTransfert 0.3.8

15 novembre 2026. Archive actuelle récupérée avant édition : 0.3.7, version persistante 10. Remplacement avec la garde effectivement reçue, sous la même identité. Cycle borné : optimisation du coût des blocs bruts expérimentaux et accès plus simple au résultat dans l'interface.

## Ce qui est plus simple

Après « Copie terminée et vérifiée », **Ouvrir la destination** retrouve les fichiers dans le gestionnaire de fichiers. Il utilise la destination du transfert terminé, même si le champ est changé ensuite. Le bouton reste désactivé durant une nouvelle copie, après interruption ou erreur. L'ouverture se fait dans un thread séparé pour ne pas bloquer la fenêtre sur un lecteur réseau lent. Si le dossier ou le gestionnaire est indisponible, un message indique le chemin à ouvrir manuellement ; le résultat d'intégrité n'est pas transformé en échec de copie. Aucun dossier n'est ouvert automatiquement.

Installation inchangée : cette archive contient les sources, les lanceurs et le paquet Python, **aucun EXE Windows construit**. Guide court : DEMARRAGE_RAPIDE.md. Le parcours conserve source → destination → Copier / reprendre, puis interruption/reprise avec les mêmes dossiers. La compression ultra reste réservée au mode expérimental explicite en terminal ; aucun réglage de codec n'est ajouté à l'interface.

## Code et garanties

Lorsqu'une recette envoyait du brut, le code construisait une seconde trame brute identique pour comparer les tailles, avec nouveau SHA-256 et allocation du bloc entier. Le code construit désormais une seule trame. Pour une recette comprimée, il compare la taille complète (préfixe et payload) à celle du brut avant d'allouer une éventuelle trame de remplacement ; les deux préfixes partagent le même SHA-256 du bloc source. L'égalité des tailles conserve la recette comme avant.

Format UTCL1/UTCS1, choix des codecs/largeurs, sondes, fréquence de sélection, négociation et réglages par défaut conservés. Le format émis est testé octet pour octet contre 0.3.7 pour tous les codecs/largeurs disponibles et plusieurs tailles non alignées. Le récepteur continue de décompresser dans ses bornes et de vérifier chaque bloc et le terminal ; les relectures SHA-256 et inventaires du moteur sont inchangés. Aucune nouvelle méthode de compression n'est revendiquée.

## Validations réelles

**135 tests Linux réussis**, dont huit nouveaux cas : quatre pour compatibilité/retour au brut/corruption/source conservée, quatre pour ouverture du bon résultat, erreur avec action manuelle, indisponibilité pendant copie/sans succès et gestionnaire lent sans bloquer le contrôleur. Les tests interruption → reprise et conflit existants vérifient aussi le nouvel état du bouton. Widgets doublés et ouverture du gestionnaire simulée : aucune validation visuelle ou Windows prétendue.

Compilation Python et helper C++ Linux réussie ; cryptography 50.0.2 pour les fixtures. La suite conserve les tests de corruption, troncature, source modifiée, refus d'écrasement, liens/collisions, droits, manque d'espace simulé, nombreux petits fichiers, Unicode/cachés/vides, plages/delta et réseau HTTPS avec interruption/reprise. Un essai local supplémentaire de **1 Gio** réussit en **2,5219 s**, avec SHA-256 indépendant, caches chauds et fsync demandé : contrôle d'intégrité, aucune accélération locale revendiquée.

Un contrôle d’intégrité supplémentaire copie réellement en HTTPS ultra un fichier de **64 Mio + 256 petits fichiers mixtes**, caché/Unicode/vides (259 fichiers). Une interruption à 8 Mio laisse le gros fichier non publié ; la reprise avec quatre workers réutilise **8 388 608 octets**. Inventaire/SHA-256 indépendants et source conservée confirmés. Durée globale de cet essai de robustesse : 1,6761 s, sans comparaison de vitesse. Les compteurs de flux complets excluent les flux interrompus, comme avant ; ils ne mesurent pas le trafic total. Reproduire : `python3 -m research.verify_mixed_https` ; reports/mixed-https-0.3.8.json.

Le wheel 0.3.8 construit puis installé dans un dossier isolé a passé le contrôle embarqué Linux sans affichage et un retour au brut vérifié ; import confirmé depuis le paquet installé. Ce contrôle déclare explicitement frozen=false et gui_created=false et ne vaut pas preuve Windows (reports/installed-wheel-0.3.8.json).

Le moteur local, le serveur HTTPS, le décodeur de flux, le delta, le rechargement/contrôleur de partage et la chaîne de construction Windows sont identiques à l'archive récupérée (reports/unchanged-core-0.3.8.json). Les sources précédentes modifiées sont conservées dans history/v0.3.7.

## Mesures CPU et HTTPS

Quinze répétitions par variante, ordre mélangé, sur deux blocs synthétiques de 4 Mio, état brut déjà sélectionné imposé. Encodage + reconstruction/SHA-256 médian : aléatoire **10,519 → 6,073 ms** (-42,3 %) ; déjà gzip **9,977 → 6,627 ms** (-33,6 %). Cela isole le chemin affecté, sans recherche initiale, réseau ni disque : **ce n'est pas le gain du transfert complet**. Détails et bornes dans reports/raw-reuse-0.3.8.json.

Banc HTTPS : **180 copies réussies**, cinq répétitions par combinaison, ordre mélangé, trois fichiers synthétiques d'environ 8 Mio, six méthodes et deux plafonds applicatifs par connexion (50 et 1000 Mbit/s). TLS réel en boucle locale Linux, morceaux de 16 Kio, caches chauds. Total en secondes = inventaire/hachage et configuration serveur + manifeste/TLS client + sélection/compression/métadonnées + transport + reconstruction/écriture/fsync/vérifications moteur. Aucun dictionnaire. Génération du certificat commun de fixture, création des données, installation, actions humaines, arrêt serveur et SHA-256 indépendant supplémentaire exclus (certificat commun non chronométré). Chaque résultat a ce contrôle indépendant supplémentaire.

| Données synthétiques | Plafond Mbit/s | Brut | Adaptatif 0.3.7 | Adaptatif 0.3.8 | Meilleure compression fixe testée |
|---|---:|---:|---:|---:|---:|
| Signal float32 | 50 | 1.3837 | 0.7641 | 0.7629 | 0.7501 (zstd3-shuffle4) |
| Signal float32 | 1000 | 0.1098 | 0.1267 | 0.1173 | 0.1171 (zstd3-shuffle4) |
| Journaux puis aléatoire | 50 | 1.3831 | 0.7688 | 0.7663 | 0.7521 (zstd3) |
| Journaux puis aléatoire | 1000 | 0.1057 | 0.1094 | 0.1031 | 0.0996 (zstd3) |
| Déjà gzip | 50 | 1.3827 | 1.4167 | 1.4095 | 1.4103 (zstd3) |
| Déjà gzip | 1000 | 0.1042 | 0.1428 | 0.1370 | 0.1280 (zstd3) |

À 50 Mbit/s sur le fichier déjà gzip, 1,4167 → 1,4095 s (-0,51 %) ; le brut reste meilleur à 1,3827 s. À 1000 Mbit/s, 0,1428 → 0,1370 s (-4,07 %) mais le brut est à 0,1042 s. Les références fixes de compression sont gzip 1, Zstd 3 et Zstd 3 + permutation 4, mêmes trames vérifiées pour Zstd. Ce ne sont pas toutes les références du marché. Les bonnes recettes fixes restent généralement préférables lorsqu'elles sont connues ; plusieurs intervalles se chevauchent. La réduction CPU est nette sur le chemin isolé, le petit gain global à 50 Mbit/s ne prouve pas une amélioration générale. La recherche sur les contenus déjà comprimés demeure coûteuse. Le sélecteur dépend du chronométrage et peut choisir des recettes différentes selon la charge.

Résultats bruts, recettes/compteurs et min–max : reports/https-compression-0.3.8.json. Reproduire :

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_raw_reuse --rounds 15
python3 -m research.benchmark_https_compression --rounds 5 --mbps 50 1000 --reference history/v0.3.7/ultra/compression.py --output reports/https-compression-0.3.8.json
python3 verify_gib.py
```

## Limites et prochaine étape

Pas de Windows/Wine, affichage graphique/Xvfb ou hôte RDP accessible dans cet environnement. Installation/EXE/portable, raccourcis, mise à niveau/désinstallation et rendu de l'interface restent à valider réellement sous Windows. Les appels d'ouverture Windows/macOS/Linux ne sont pas des essais réels de leurs gestionnaires graphiques. La livraison ne contient aucun paquet Windows présenté comme validé.

Compression expérimentale facultative, sans IA obligatoire, inactive par défaut. Réseau réel entre deux postes, latence/pertes, supports USB/disques physiques et caches froids non mesurés. Canal RDP DVC/MSTSC natif, lecteurs \\tsclient\ réels, régulation de réactivité RDP et manifeste authentifié indépendant des transports restent à développer/valider. La reprise actuelle dépend encore de l'URL et des métadonnées source. ACL, flux NTFS alternatifs et attributs étendus non copiés. La vision générale entreprise archivée reste abandonnée.

---

# Rapport — UltraTransfert 0.3.7

15 novembre 2026. État récupéré avant modification : archive 0.3.6, version persistante 9. La sauvegarde conserve l'identité et la garde de version effectivement reçue. Cycle borné consacré à la reprise d'un partage après fermeture de l'application, sans modification du moteur de fichiers ou des codecs.

## Progrès utilisateur

Nouveau bouton **Charger une connexion existante…** dans Émettre en HTTPS. L'émetteur sélectionne son dossier privé conservé ; l'adresse est restaurée et les fichiers sont vérifiés. Il choisit ensuite explicitement la source et clique Partager. Le destinataire peut conserver la même invitation et reprendre la même destination lorsque URL, source et inventaire restent identiques. Il n'est plus nécessaire de recréer une clé, un certificat, un jeton ou une invitation à chaque réouverture.

Le chargement ne crée pas de socket et ne démarre pas de partage. Il ne réécrit ni ne supprime les fichiers de connexion. Annuler le sélecteur conserve la sélection ; un rechargement invalide efface la sélection prête et ne réactive pas implicitement une ancienne connexion. Le dossier source n'est pas restauré ou partagé automatiquement : il reste à choisir consciemment.

## Validation et garde-fous

Les quatre fichiers attendus sont lus avec limites de taille, refus des liens/jonctions et contrôle de leurs signatures avant/après lecture. Les droits trop larges du dossier et des fichiers secrets sont refusés sous POSIX, sans correction automatique. Le jeton et le certificat sont recoupés avec l'invitation ; les secrets ne sont pas affichés.

Une négociation TLS en mémoire (MemoryBIO, 32 échanges maximum et 512 Kio échangés au maximum) vérifie certificat, dates, nom d'hôte et clé privée sans socket. Ce n'est pas un essai réseau. Une clé PEM chiffrée est refusée avant déchiffrement ; les callbacks de chargement de clé interdisent aussi les demandes interactives de mot de passe. Le rechargement ne dépend pas de cryptography ; ce complément demeure requis seulement pour générer de nouvelles clés.

Le démarrage du partage revalide cette configuration et contrôle encore ses signatures juste avant écoute, après l'inventaire/hachage de la source. Une modification ordinaire pendant le démarrage provoque un refus sans ouverture de service. Les contrôles ne constituent pas un instantané contre un acteur hostile capable de restaurer les métadonnées : ne pas modifier la configuration pendant ces opérations.

## Tests réels

**127 tests Linux réussis** (113 existants + 14 nouveaux), avec cryptography 50.0.2 pour les fixtures. Compilation Python et helper C++ Linux réussie. Tests nouveaux : chargement sans socket/import cryptography et sans réécriture, mauvais jeton/clé/nom, certificats expirés et futurs, clé chiffrée sans prompt/déchiffrement, fichiers manquants/excessifs, liens, permissions POSIX, modification pendant contrôle et avant écoute, annulation/erreur de chargement GUI.

Un test copie réellement en HTTPS 8 Mio avec Unicode/vides, interrompt le destinataire, arrête le serveur, crée un nouveau contrôleur, recharge la connexion conservée, redémarre et reprend avec l'invitation initiale. Des octets partiels sont réutilisés et le SHA-256 final indépendant correspond. La GUI de ce test utilise des widgets doublés : pas une validation visuelle. La suite préexistante couvre aussi 64 Mio interrompus par arrêt serveur, corruption, conflits, source modifiée, nombreux petits fichiers et manque d'espace simulé.

Le contrôle du futur portable exige maintenant sharing_restore_checked=true après restauration locale, en plus du partage TLS/copie/arrêt déjà prévus. Sa branche est testée sous Linux avec frozen simulé, pas dans un EXE Windows. Un essai local de 1 Gio réussit en 3,7347 s avec empreinte indépendante ; cache chaud et fsync demandé, pas mesure physique disque/USB.

## Mesures de réouverture

Six répétitions par variante, ordre alterné équilibré. Même serveur/client courant et même source synthétique de 8 Mio + 128 fichiers de 2 Kio + caché/vides (131 fichiers). TLS réel en boucle locale Linux, caches chauds, aucun plafond réseau, compression auto habituelle sans gzip sur les données aléatoires utilisées.

| Parcours | Connexion prête, médiane | Serveur prêt, médiane | Total médian | Total min–max |
|---|---:|---:|---:|---:|
| Nouvelle génération | 0,14166 s | 0,17488 s | 0,75213 s | 0,63922–0,85726 s |
| Connexion conservée | 0,00436 s | 0,03204 s | 0,60410 s | 0,58658–0,64698 s |

Le rechargement évite le travail de génération RSA et les écritures déjà effectués : l'amélioration porte sur la préparation lors d'une réouverture, pas sur la vitesse du moteur ou la compression. Le profil conservé avait coûté 0,19351 s à créer auparavant ; ce coût est mesuré séparément et volontairement exclu de la colonne de réouverture. Il ne faut pas présenter ces résultats comme un gain de premier usage gratuit ou une promesse matérielle.

Le total inclut création ou rechargement des accès, contrôles locaux TLS, inventaire/hachage/configuration serveur et revalidation avant écoute, import/TLS client, transport, copie/fsync/reconstruction/vérifications moteur et arrêt. Préparation des données, installation/import initial des dépendances, actions humaines/rendu GUI et SHA-256 supplémentaire indépendant exclus. Toutes les empreintes indépendantes ont réussi. Aucune mesure Windows, RDP, Internet, USB ou réseau entre deux machines.

Reproduire : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_share_restore --rounds 6`, `python3 verify_gib.py`. Résultats bruts dans reports/share-restore-0.3.7.json ; journal de 1 Gio dans reports/one-gib-0.3.7.log. Les tests doivent disposer du complément sharing pour créer les fixtures ; un chargement valide lui-même n'en a pas besoin.

## Limites et suite

L'environnement ne fournit pas de Windows, RDP ou affichage graphique accessible. Les scripts d'installation, ACL natives, EXE/portable et rendu visuel ne sont pas validés ; l'archive livrée reste source avec paquet Python. Sous Windows, le lecteur ne réévalue pas les DACL d'un dossier chargé : conserver les fichiers dans le dossier personnel protégé d'origine et valider ce parcours sur Windows. Les configurations chiffrées par mot de passe ne sont pas prises en charge et un certificat expiré demande une nouvelle préparation (ou correction d'horloge si appropriée).

L'ouverture initiale de la source reste non annulable pendant inventaire/hachage ; le parcours graphique reste limité à localhost ou une IPv4 précise. Recharger la même connexion réactive les mêmes accès au dossier explicitement choisi : aucun scellement de l'invitation à une source unique ni révocation individuelle n'est ajouté. La reprise dépend encore de l'URL et des métadonnées source ; ce n'est pas le manifeste indépendant des transports demandé à terme.

Canal DVC natif et reprise inter-transports restent à développer ; lecteurs RDP redirigés non validés. Compression ultra expérimentale facultative et inchangée, aucune nouvelle expérience de compression. Guide court : REPRENDRE_PARTAGE.md.

---

# Rapport — UltraTransfert 0.3.6

15 novembre 2026. Dernière archive récupérée avant édition : 0.3.5, version persistante 8. La garde de remplacement utilise la version renvoyée, pas une constante du projet. Cycle borné consacré au partage HTTPS depuis l'interface et à un arrêt fiable des connexions, sans changement du moteur de copie ou des codecs.

## Résultat utilisable

Le bouton **Émettre en HTTPS…** ouvre maintenant un parcours complet : créer la connexion privée hors ligne, choisir un dossier, **Partager ce dossier**, puis **Arrêter le partage**. L'ouverture n'a lieu que sur ce clic explicite. Dossier et adresse sont affichés et bloqués pendant le partage. Fermer le dialogue actif demande l'arrêt avant fermeture ; la fenêtre principale attend aussi l'arrêt avant fermeture. Une adresse changée exige une nouvelle préparation et un échec de nouvelle préparation ne réactive pas implicitement l'ancienne.

La portée graphique initiale est une IPv4 précise de ce poste ou localhost, sans écoute générale ni ouverture de pare-feu. Invitation, certificat et jeton sont recoupés avant écoute ; le certificat/nom et le jeton restent vérifiés au transfert. Le serveur refuse toujours une source contenant sa clé privée. Le mode CLI existant reste disponible.

## Arrêt et robustesse du serveur

Le serveur suit les connexions et ferme leurs sockets à l'arrêt, puis ferme l'écoute. La négociation TLS se déroule dans les threads clients, avec limite de 64 connexions, attente TLS de 5 s et attentes d'E/S de 120 s. Un client ne terminant pas sa négociation ne bloque plus l'acceptation ni l'arrêt. La clé et le certificat sont chargés avant création de l'écoute, pour éviter une ouverture résiduelle en cas d'erreur de certificat.

Les octets déjà reçus restent sur le destinataire et une copie déjà complète ne peut pas être rappelée. Des lectures locales engagées dans les threads peuvent finir après fermeture de leurs sockets. Arrêter puis redémarrer avec la même préparation réactive le même accès ; changer le jeton pour révoquer durablement l'ancien accès. La reprise nécessite même origine/source et validation des partiels ; ce n'est pas la reprise inter-transports.

## Validations réelles

**113 tests Linux réussis** (104 précédents + 9 nouveaux), avec cryptography 50.0.2. Compilation Python et helper C++ Linux réussie. Nouveaux tests : construction sans socket, portée IPv4 précise, TLS/copie/arrêt/redémarrage, double démarrage refusé, écoute fermée après arrêt, client sans négociation TLS arrêté en moins de 2 s dans ce test, erreur de clé avant ouverture de socket, invitation incohérente et écoute générale refusées, adresse GUI modifiée refusée avant démarrage.

Un transfert réel de 64 Mio est interrompu par arrêt du serveur après début de réception : fichier incomplet non publié, état conservé, redémarrage puis reprise avec octets réutilisés et SHA-256 final correct. Le test de contrôleur graphique (widgets doublés) démarre une vraie écoute TLS, affiche la source, réalise une copie et ferme le dialogue en attendant l'arrêt effectif. La suite existante conserve corruption, conflits, source modifiée, nombreux petits fichiers, Unicode/cachés/vides et manque d'espace simulé.

Le contrôle du futur portable exige maintenant également sharing_session_checked=true : préparation cryptographique, partage TLS local, copie et arrêt. Le code de ce chemin a été testé sous Linux avec un indicateur frozen simulé ; aucun EXE Windows n'a été exécuté. Ce test ne constitue pas une validation graphique ou Windows.

Essai local supplémentaire de 1 Gio : 4,7166 s, SHA-256 indépendant correct. Cache chaud et fsync demandé ; débit logique, pas mesure physique disque/USB. Une seule exécution, pas de comparaison de vitesse entre versions. Moteur, delta, codecs, préparation de certificat et parsing d'invitation restent identiques à l'archive récupérée (reports/unchanged-core-0.3.6.json).

## Mesures du cycle complet

Six répétitions par variante, ordre alterné équilibré. Référence : orchestration directe du serveur courant ; variante : ShareSession utilisé par le dialogue. Même client et même serveur courant : **ce n'est pas une comparaison ancien/nouveau serveur**. Dossier synthétique : 16 Mio, 128 fichiers de 2 Kio, caché/vides (131 fichiers), TLS en boucle locale Linux et caches chauds, aucun plafond réseau. Compression auto habituelle, données aléatoires ne sélectionnant pas gzip.

| Parcours | Prêt, médiane | Arrêt, médiane | Total médian | Total min–max |
|---|---:|---:|---:|---:|
| Orchestration directe | 0,03995 s | 0,09087 s | 0,68065 s | 0,63350–0,80707 s |
| Contrôleur du dialogue | 0,03821 s | 0,09047 s | 0,66320 s | 0,62229–0,98002 s |

Les écarts et plages ne démontrent aucun gain stable de vitesse. Le bénéfice livré est l'absence de terminal pour le parcours d'émission/réception et l'arrêt explicite du partage. Les mesures ne couvrent pas le temps des gestes humains ni le rendu graphique.

Le total inclut export d'invitation, inventaire/hachage/configuration serveur, client/import/TLS/transport/copie/fsync/reconstruction/vérifications moteur et arrêt. Préparation unique du certificat/clé mesurée séparément : 0,09073 s, à ajouter pour un premier usage comparable. Préparation des données, installation/import initial des dépendances et contrôle SHA-256 supplémentaire indépendant exclus. Toutes les vérifications indépendantes ont réussi. Aucun test de latence/perte réseau, machine distante, charge continue, USB ou RDP réel.

Reproduire : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_share_session --rounds 6`, `python3 verify_gib.py`. Données brutes dans reports/share-session-0.3.6.json, journaux correspondants et reports/one-gib-0.3.6.log.

## Limites et prochaines étapes

L'environnement ne fournit aucun hôte Windows/RDP ni affichage graphique accessible (DISPLAY/Xvfb absents ; inventaire des paquets indisponible sans droits supplémentaires). Les parcours graphiques sont testés par contrôleur avec widgets doublés : rendu/layout non validés. Les scripts d'installation, ACL natives, build/EXE/portable Windows restent à essayer réellement ; l'archive livrée reste source avec paquet Python, sans EXE Windows construit.

Le démarrage initial inventorie/hache la source sans annulation graphique de cette phase ; il faut attendre son résultat. IPv6 et DNS arbitraire ne sont pas proposés par le nouveau parcours graphique. Les limites de connexions/attentes peuvent produire une erreur sur des liens très lents ou surchargés ; la reprise reste soumise aux contrôles de contenu. Aucun contournement du pare-feu ou des politiques RDP.

Canal DVC natif, manifeste authentifié indépendant des transports et reprise entre chemins restent à développer. Les lecteurs RDP redirigés restent distincts et non validés sur Windows. Compression ultra expérimentale facultative et inchangée ; aucune nouvelle mesure de compression. Guide court : PARTAGE_HTTPS.md.

Limite de confort : le dialogue ne recharge pas encore une préparation sauvegardée après fermeture. Pour réutiliser exactement ses fichiers, le mode manuel reste disponible ; dans un même dialogue laissé ouvert après Arrêter, Partager ce dossier peut redémarrer avec la préparation courante.

---

# Rapport — UltraTransfert 0.3.5

15 novembre 2026. Reprise de l'archive 0.3.4, version persistante 7 effectivement récupérée avant modification ; garde de version conservée pour sauvegarde. Cycle borné consacré à la préparation automatique des connexions, avec moteur de copie et codecs inchangés.

## Progrès concret

Nouveau bouton **Préparer une invitation d'émission…** : adresse du poste, choix d'un emplacement personnel, puis création d'un sous-dossier neuf avec certificat, clé, jeton aléatoire et invitation. Le dialogue évite toute commande OpenSSL ; il reste réactif pendant la génération, affiche le résultat sans secret et attend la fin avant fermeture. La commande `prepare` fournit la même fonctionnalité aux utilisateurs avancés.

La préparation n'ouvre aucun réseau ni service. Le lancement graphique du serveur reste à développer ; son lancement explicite existant est documenté. La réception par invitation et sa comparaison d'empreinte restent inchangées. Une source contenant la clé privée du serveur est désormais refusée avant écoute.

Cryptography 50.0.2 est un complément facultatif de préparation ; les transferts existants restent utilisables sans lui. Installer_Windows.bat prévoit sa préparation dans .venv-run et le lanceur donne priorité à cet environnement. Le constructeur du futur portable inclut la dépendance et exige sharing_prepared=true lors du contrôle embarqué, pour exercer aussi la protection du dossier sur un vrai Windows avant livraison. Aucun de ces scripts Windows n'a été exécuté sur Windows ici.

## Protection de la configuration

Dossier neuf seulement, aucune réutilisation ou écrasement implicite. Permissions POSIX 0700/0600 vérifiées. Sous Windows, le code prévoit whoami et icacls avec chemins système, retrait des autorisations héritées et accès au compte courant avant écriture de secrets. Un échec annule la préparation. Les tests Linux simulent ces appels : **pas une validation d'ACL Windows**. Seul le dossier neuf est concerné ; les droits de transfert ne sont pas élargis.

Certificat RSA 3072/SHA-256, SAN DNS ou IP précis, usage serveur, auto-signé et non CA, valide sept jours avec début antidaté de cinq minutes. Nouvelle clé et jeton à chaque préparation ; pas d'installation dans le magasin de certificats du système. La clé est stockée non chiffrée dans ce dossier privé. L'invitation contient toujours un accès secret en clair et demande une transmission de confiance et une comparaison d'empreinte hors bande ; ce n'est pas une signature ni un appairage complet automatique.

## Validation réelle

**104 tests Linux réussis**, avec cryptography 50.0.2 (13 nouveaux, 91 existants). Compilation Python et helper C++ Linux réussie. Les tests couvrent génération sans socket, caractéristiques/validité du certificat, secrets distincts, dossier existant préservé, adresses refusées avant création, dépendance absente, échec d'écriture/manque d'espace simulé, protection Windows simulée avant secrets, contrôleur graphique avec widgets doublés et préparation CLI sans secret dans la sortie.

Le certificat IP généré est utilisé avec un serveur TLS réel en boucle locale : copie Unicode/cachés/vides, interruption/reprise et SHA-256 final contrôlés, mauvais nom d'hôte refusé. Le garde-fou de dossier contenant la clé privée est testé avant toute ouverture de socket. Le nouveau chemin de contrôle embarqué est également exécuté sous Linux avec un indicateur frozen simulé : cela valide du code, pas un EXE Windows. La suite existante conserve corruption, conflits, modifications de source, reprise locale/HTTPS, nombreux petits fichiers et manque d'espace simulé.

Essai local supplémentaire : 1 Gio copié et vérifié indépendamment en 3,0149 s, cache chaud, fsync demandé. Ce n'est pas un débit physique de disque/USB ni une promesse matérielle. Empreinte et résultat conservés dans reports/one-gib-0.3.5.log.

## Mesures de préparation et transfert

Six répétitions par variante, ordre alterné équilibré. Référence : ancienne recette OpenSSL automatisée par le banc, sans mesurer les actions humaines. Variante : nouveau générateur Python/cryptography. Clés RSA 3072 et certificat de sept jours dans les deux cas ; même moteur courant et même chemin HTTPS. Dossier synthétique : 8 Mio, 128 fichiers de 2 Kio, caché et vides (131 fichiers, 8 650 758 octets). Linux, caches chauds, boucle locale TLS, aucun plafond réseau, aucune compression.

| Variante | Préparation médiane | Total médian | Total min–max |
|---|---:|---:|---:|
| Recette OpenSSL | 0,12757 s | 0,61434 s | 0,52590–0,95005 s |
| Préparation automatique | 0,13360 s | 0,57155 s | 0,51555–0,84091 s |

La génération RSA varie fortement. Ces résultats ne démontrent pas un gain stable de vitesse ; l'amélioration livrée est la suppression des commandes et fichiers à fabriquer manuellement. Aucun gain de débit ou de compression revendiqué.

La préparation comprend génération clé/certificat/jeton, écritures/fsync et invitation. Le total ajoute inventaire/hachage/configuration du serveur, export pour le port éphémère du banc, import client/TLS, transport brut, écriture/reconstruction et vérifications moteur. Génération des données, installation/import initial des dépendances, actions humaines et vérification SHA supplémentaire indépendante exclus. Ce n'est pas une mesure de première installation. Les contrôles indépendants ont tous réussi. Résultats bruts dans reports/share-setup-0.3.5.json ; version cryptography 50.0.2 et plateforme consignés.

Reproduire après installation du complément sharing : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_share_setup --rounds 6`, `python3 verify_gib.py`. OpenSSL CLI est nécessaire au banc de référence seulement, pas au nouveau générateur du produit. La correspondance des fichiers moteur/codecs inchangés est dans reports/unchanged-core-0.3.5.json.

## Limites et suite

Linux sans serveur graphique ni hôte Windows/RDP connecté. Aucun rendu visuel, ACL Windows réelle, installation source Windows ou EXE/portable Windows validé. L'archive reste source avec scripts et paquet Python. La création du complément et les commandes Windows doivent être essayées sur un vrai hôte, puis la préparation/lancement et la mise à niveau/suppression du portable sur un second poste sans Python.

Le certificat peut expirer ; cela n'arrête pas un transfert déjà établi. Pas d'expiration de jeton, de révocation individuelle, de serveur démarré implicitement ou de nouveau transport. Le parcours graphique complet d'émission et d'arrêt, le canal DVC natif, le manifeste authentifié et la reprise inter-transports restent à développer. Compression ultra toujours facultative et inchangée ; aucune nouvelle expérience de compression. Guide utilisateur : PREPARATION_PARTAGE.md.

---

# Rapport — UltraTransfert 0.3.4

15 novembre 2026. Archive récupérée avant modification : 0.3.3, version persistante 6. Le remplacement utilise la garde effectivement reçue. Cycle borné consacré à la réception HTTPS simplifiée, sans nouveau codec ni modification du moteur de fichiers.

## Ce qui est plus simple

Le destinataire peut ouvrir une invitation .utconnect au lieu de sélectionner trois paramètres techniques séparés. Il compare explicitement l'adresse et l'empreinte du certificat avec l'émetteur, puis choisit sa destination et lance la copie. L'invitation reste seulement en mémoire après import. Le mode manuel reste disponible ; importer une invitation efface l'ancienne référence delta pour éviter un choix implicite.

L'émetteur peut exporter l'invitation avec `python3 -m ultra invite URL SORTIE --cert CERTIFICAT_PUBLIC --token-file JETON`, sans clé privée, sans connexion et sans ouverture de service. Le fichier n'est pas écrasé. Certificat et jeton doivent encore être préparés manuellement ; le parcours graphique Émettre et l'automatisation de cette préparation restent à construire.

Le format borne la taille, exige une origine HTTPS, un certificat unique, un jeton imprimable borné et des champs cohérents. La comparaison d'empreinte interne n'est pas une signature : confiance hors bande obligatoire. Le certificat, sa validité, le nom d'hôte et le jeton restent vérifiés au transfert. Les redirections authentifiées sont désormais refusées. Le client réutilise son opener HTTP plutôt que de le reconstruire à chaque requête.

## Validations réelles

91 tests Linux réussis : 83 existants et 8 nouveaux. Les nouveaux couvrent création sans réseau et sans écrasement, confidentialité des messages/représentation, format invalide ou excessif, mauvaise empreinte et clé privée refusées, transfert HTTPS réel avec interruption/reprise, refus des mauvais certificat/nom/jeton, redirection non suivie, acceptation/refus de l'invitation dans le contrôleur avec widgets doublés et export CLI sans secret dans la sortie.

Le test de contrôleur déclenche une véritable copie HTTPS après confirmation simulée ; le refus d'import ne contacte pas le réseau. Le test de reprise contrôle le SHA-256 final et les octets réutilisés. La suite préexistante conserve les contrôles de corruption, conflits, source modifiée, nombreux petits fichiers, Unicode/vides et manque d'espace simulé. Compilation Python et C++ Linux réussie. Un fichier synthétique de 1 Gio est copié et vérifié avec empreinte indépendante en 2,6332 s, caches chauds : pas un débit de support physique.

## Mesures HTTPS de contrôle

Six répétitions par configuration, six permutations d'ordre équilibrées, processus clients distincts et même serveur TLS en boucle locale. Dossier synthétique : 128 fichiers de 2 Kio, un fichier de 16 Mio, caché et vides, soit 131 fichiers / 17 039 365 octets. Aucun plafond réseau et aucune compression. Caches chauds, pas une session Windows/RDP ni un réseau entre deux machines.

| Client | Durée médiane | Minimum–maximum |
|---|---:|---:|
| 0.3.3 manuel | 0,29699 s | 0,28147–0,33884 s |
| 0.3.4 manuel | 0,26408 s | 0,25946–0,28893 s |
| 0.3.4 invitation | 0,27444 s | 0,26427–0,28803 s |

Sur ce banc seulement, le nouveau manuel est environ 11,1 % plus court que l'ancien. Le parcours invitation est environ 7,6 % plus court que l'ancien manuel, mais 3,9 % plus long que le nouveau manuel. Ce compromis inclut l'import/validation du certificat de l'invitation ; l'écart ne doit pas être attribué exclusivement à cette étape sans profilage. Aucun gain universel ni nouvelle compression n'est revendiqué.

Les temps comprennent import d'invitation le cas échéant, TLS, manifeste, transport, copie/fsync et contrôles du moteur. Le contrôle SHA-256 supplémentaire indépendant est effectué après chronométrage. Préparation commune du serveur : 0,02897 s ; export unique de l'invitation : 0,00125 s, séparés du tableau. Génération des données et du certificat exclues : ce n'est pas une mesure complète de premier appairage. Le moteur engine.py, delta.py et les codecs compression.py/blockstream.py restent identiques à l'archive récupérée.

Reproduire : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 -m research.benchmark_invitations --reference DOSSIER_0_3_3 --rounds 6`, `python3 verify_gib.py`. Résultats bruts dans reports/invitation-https-0.3.4.json et journaux correspondants. Le rapport de 1 Gio est conservé dans one-gib-0.3.4.log.

## Limites

Le fichier d'invitation contient le jeton en clair ; toute personne qui le possède a le même accès au dossier servi. Aucune expiration, permission individuelle ou révocation distincte ajoutée ; arrêter le serveur ferme le partage actif, changer le jeton révoque l'ancien accès lors d'un redémarrage. Le fichier est en mode 0600 sous POSIX ; les ACL Windows héritées restent à tester. Aucun certificat n'est ajouté au système. L'URL est normalisée avec port explicite, ce qui peut rendre incompatible un ancien état de reprise utilisant une écriture différente de l'origine : conserver l'ancienne configuration pour le reprendre. Ce n'est pas la reprise inter-transports.

Aucun hôte Windows/Wine ni serveur graphique ou session RDP connecté. Les parcours sont testés avec contrôleur et widgets doublés : pas de validation visuelle. Le paquet reste une archive source sans EXE Windows construit. Installation/portable Windows, génération automatique des certificats, émission graphique, canal DVC natif et manifeste authentifié inter-transports restent à développer ou valider. La compression ultra reste facultative ; aucune nouvelle mesure de compression dans ce cycle. Voir INVITATIONS_HTTPS.md pour le fonctionnement et les limites de confiance.

---

# Rapport — UltraTransfert 0.3.3

15 novembre 2026. État récupéré : archive 0.3.2, version persistante 5 ; garde de version conservée pour le remplacement. Cycle borné consacré à la construction d'un portable Windows et à ses contrôles préalables, sans changement du moteur, de la GUI ni des codecs.

## Travail réalisé

- Nouvelle chaîne build_windows.py, appelée depuis Construire_EXE_Windows.bat : environnement isolé, PyInstaller 6.22.3, construction onedir/windowed, dépendances incluses et ZIP autonome visé.
- Verrou de projet, sortie temporaire, ZIP extrait dans un chemin Unicode/espaces puis lancement avec un environnement sans Python dans PATH. Le ZIP n'est publié qu'après réussite du contrôle embarqué. Une archive existante de même version n'est jamais écrasée.
- Contrôle embarqué via launch_gui.py --smoke-test RAPPORT : création Tk/App, copie locale avec noms Unicode, cachés et éléments vides, interruption, reprise validée et SHA-256 indépendant. Un rapport Linux ou non figé est refusé comme preuve Windows. Le mode normal continue à ouvrir l'interface.
- Instructions courtes du futur portable : extraction/lancement, raccourci facultatif, mise à niveau dans un autre dossier, suppression limitée à l'application. Aucun service, règle de pare-feu, élévation ou démarrage automatique ajouté.

## Validations réellement effectuées

83 tests réussis sous Linux (75 précédents + 8 nouveaux). Compilation Python du moteur, de la recherche, de launch_gui.py et build_windows.py ; compilation C++ Linux réussie. Nouveaux tests : copie embarquée et reprise réelle, rapports réussite/échec, archivage/extraction de dépendances avec Unicode, refus d'exécutable absent, de liens et de preuves Windows incomplètes, refus de construction sur Linux. Les tests d'archivage utilisent des fichiers factices, pas de vrais exécutables Windows.

Le contrôle embarqué sans GUI exécuté trois fois sous Linux reprend 65 536 octets à chaque fois ; médiane 0,01178 s pour préparation, interruption, reprise et vérifications d'un fichier synthétique de 2 Mio et des éléments annexes. Ce n'est ni un temps de lancement Windows, ni une mesure de débit matériel. Le véritable point d'entrée avec --smoke-test a aussi été exécuté sans DISPLAY : sortie 1 et rapport failed, confirmant qu'une création Tk impossible ne peut être déclarée réussie.

La suite existante couvre de nombreux petits fichiers, Unicode/vides, corruption, conflits, manque d'espace simulé, interruption/reprise et réseau HTTPS réel en boucle locale. Aucune nouvelle expérience de compression n'a été réalisée.

## Mesures comparatives de contrôle

Trois répétitions, ordre alterné entre processus, contre l'archive 0.3.2 récupérée. Données synthétiques, caches chauds, inventaire/copie/fsync/vérifications inclus ; sans interface graphique. Les fichiers engine.py, network.py, compression.py, blockstream.py, delta.py et gui.py sont identiques à la référence (rapport unchanged-runtime-0.3.3.json).

| Charge | 0.3.2 médiane | 0.3.3 médiane | Variation du temps |
|---|---:|---:|---:|
| 800 petits fichiers | 0,22636 s | 0,21153 s | −6,55 % |
| 320 Mio | 0,58812 s | 0,59392 s | +0,99 % |

Ces variations ne démontrent aucun gain de code : le moteur est inchangé. Essai indépendant de 1 Gio réussi en 2,9293 s, empreinte SHA-256 conservée dans one-gib-0.3.3.log. Débit logique en cache chaud, pas du débit USB/disque physique et pas une promesse sur un autre poste.

Reproduire : commandes dans CONSTRUCTION_WINDOWS.md ; comparaison avec `python3 compare_versions.py --reference DOSSIER_0_3_2 --rounds 3 --output reports/comparison-0.3.3.json` puis `python3 verify_gib.py`. La mesure du contrôle Linux correspond à trois appels `ultra.smoke.check(require_gui=False)` ; chaque durée et chaque résultat figurent dans reports/embedded-smoke-linux-0.3.3.json.

## Limites et prochaine priorité

L'environnement est Linux sans serveur graphique, sans Windows/Wine et sans hôte RDP connecté. La chaîne Windows n'a pas été exécutée, le contrôle Tk réel n'a pas pu réussir, aucun EXE ni ZIP portable Windows n'a été produit. L'archive livrée reste un paquet de sources et de scripts ; le guide du portable est une préparation de livraison future. Les dépendances transitives sont enregistrées au build mais pas toutes figées, et la reproductibilité binaire n'est pas établie.

Il faut construire sur Windows x64, tester le portable sur un second poste sans Python (premier lancement visuel, raccourci, copie, arrêt/reprise, erreurs, mise à niveau et suppression), puis tester HTTPS et lecteurs RDP redirigés sur de vrais postes. Le canal DVC natif, l'appairage simplifié et le manifeste authentifié inter-transports restent à développer. La compression ultra reste expérimentale et facultative ; aucune nouveauté algorithmique ou accélération générale démontrée.

---

# Rapport — UltraTransfert 0.3.2

15 novembre 2026. Cycle borné consacré à la clarté de la copie et de sa reprise. Dernière archive récupérée avant modification : 0.3.1, version persistante 4. Le remplacement doit utiliser la version effectivement récupérée, pas ce numéro documentaire.

## Résultat utilisable

Réglages avancés repliés ; source/destination et mode bloqués pendant le transfert ; arrêt demandé explicite ; reprise dans le même mode ; erreurs accompagnées d'une action possible. Correction d'un défaut : une erreur multiworker positionnait le signal d'abandon interne, et l'interface pouvait alors supprimer sa boîte d'erreur en croyant à une interruption utilisateur. Les erreurs réelles restent visibles même si une interruption est aussi demandée.

La barre indique les octets copiés. L'inventaire et la vérification finale utilisent une animation, sans pourcentage fictif ni annonce prématurée de réussite. Les contrôles d'intégrité du moteur restent identiques.

## Validations réelles et limites

- Compilation Python et helper C++ Linux ; 75 tests réussis (69 existants + 6 nouveaux).
- Test du contrôleur sans écran : copie réelle de 8 Mio, arrêt après 1 Mio, reprise partielle confirmée dans le rapport, SHA-256 indépendant, noms Unicode, fichier/dossier vides. Test réel de conflit multiworker : l'erreur est affichée et la destination n'est pas écrasée.
- Contrôles des champs bloqués/restaurés, de la priorité des erreurs sur un arrêt et des messages de manque d'espace/TLS. Les autres tests couvrent HTTPS boucle locale, corruption, manque d'espace simulé, reprise, nombreux petits fichiers et inventaire.
- Aucun serveur graphique, Windows, session RDP ou support USB physique disponible. Les widgets des nouveaux tests sont doublés : ce n'est pas une validation visuelle. EXE, installation/désinstallation, appairage simplifié et canal DVC natif restent à développer/valider ; aucun paquet Windows validé n'est revendiqué.

## Mesures de contrôle

Comparaison alternée en processus séparés contre l'archive 0.3.1, trois répétitions, données synthétiques et caches chauds ; inventaire, copie et vérifications inclus. Moteur et codecs strictement inchangés ; ces mesures sans interface servent de contrôle, pas de preuve de gain ergonomique ou de régression causale.

| Charge | 0.3.1 médiane | 0.3.2 médiane | Variation du temps |
|---|---:|---:|---:|
| 800 petits fichiers | 0,3121 s | 0,3083 s | −1,23 % |
| 320 Mio | 0,9683 s | 1,0516 s | +8,61 % |

Aucun gain de vitesse revendiqué. Variations du banc avec code moteur identique ; ne pas généraliser à un disque physique ni conclure à partir de trois répétitions. Un essai supplémentaire de 1 Gio réussit en 3,596 s avec SHA-256 indépendant ; c'est du débit logique en cache chaud, pas une mesure matérielle.

Reproduire : `python3 build.py`, `python3 -m unittest discover -s tests -v`, `python3 compare_versions.py --reference DOSSIER_0_3_1 --rounds 3 --output reports/comparison-0.3.2.json`, `python3 verify_gib.py`. Rapports bruts et test de parcours dans reports/ et tests/test_ui_workflow.py. Le dernier script remplace son rapport one-gib.json ; le journal one-gib-0.3.2.log conserve cette exécution.

Prochaine priorité : construire et examiner un portable autonome sur un vrai environnement Windows, puis réduire le nombre de champs HTTPS via un appairage authentifié. Compression expérimentale facultative conservée, sans nouvelle mesure compression ni revendication algorithmique dans ce cycle.

---

# Rapport — UltraTransfert 0.3.1

69 tests passent. La compression HTTPS adaptative est maintenant disponible explicitement avec `--compression ultra`. Mesures, utilisation et limites : `COMPRESSION_HTTPS.md`. Le mode habituel reste la valeur par défaut ; le canal RDP natif n’est pas inclus.

---

# Rapport — UltraTransfert 0.3.0

15 novembre 2026. Nouvelle fonctionnalité : reconstruction HTTPS par blocs, facultative.

- 44 tests réussis, dont 11 nouveaux tests delta : référence renommée, corruption locale et distante, reprise, plages compressées, lecture à position arbitraire, chevauchement de dossiers et manifeste invalide.
- Source compilée en Python et helper C++ Linux. Windows reste à tester ; l'extension graphique delta n'a pas encore été vérifiée visuellement.
- Démonstration réelle sur boucle locale HTTPS, sans compression : fichier synthétique de 1 073 741 824 octets, composé de blocs pseudo-aléatoires distincts ; un octet diffère dans un bloc de la référence, renommée.

| Mesure | Copie complète | Reconstruction delta |
|---|---:|---:|
| Octets fichier servis par le serveur | 1,073,741,824 | 4,194,304 |
| Durée client, inventaire et indexation inclus | 2.926 s | 3.677 s |
| SHA-256 final vérifié indépendamment | Oui | Oui |

Le delta a demandé **99,609375 % de contenu fichier en moins**. Le temps total reste plus long sur cette boucle locale rapide : l'indexation et les lectures locales coûtent davantage que les octets réseau évités. Une seule exécution par mode, caches chauds : aucune conclusion statistique sur la vitesse. Le compteur serveur exclut le manifeste, les en-têtes et TLS. Les résultats bruts sont dans `reports/delta-one-gib.json`.

Le résultat complet est écrit physiquement et vérifié ; aucune copie par référence ni fichier virtuel n'est utilisée. Le gain prouvé porte sur le volume réseau du cas testé. Pour accélérer le temps d'accès utilisateur, la prochaine piste est le dossier vivant décrit dans `VISION.md` ; ce concept n'est pas encore implémenté.

---

# Rapport de validation — UltraTransfert 0.2.0

15 novembre 2026. Environnement : Linux-6.18.57-x86_64-with-glibc2.41, Python 3.12.14.

## Résultats vérifiés

- Compilation des modules Python et du helper C++ Linux réussie (g++ -O3, avertissements traités comme erreurs).
- 33 tests réussis, aucun ignoré : copies binaires, Unicode, dossiers vides, conflits, corruptions, modifications de source, reprise locale/HTTPS, certificats et jetons invalides, compression adaptative, manque d’espace et libération de verrou.
- Un cycle complet compilation → tests → mesures → recommandations terminé avec trois répétitions par configuration.
- Interface Linux ouverte et utilisée pour copier deux fichiers dont un nom Unicode, avec fichier et dossier vides ; résultat et SHA-256 contrôlés indépendamment.
- Paquet Python universel construit ; installation locale vérifiée.

## Comparaison du code avant/après

Sept répétitions par charge et par version, ordre alterné aléatoire, mêmes données synthétiques, processus distincts, réglages automatiques. Temps de copie et vérifications inclus ; caches chauds.

| Charge | Avant, médiane | Après, médiane | Variation |
|---|---:|---:|---:|
| small_800_files | 0.3390 s | 0.2081 s | +38.6 % de gain |
| large_320MiB | 0.5818 s | 0.6009 s | -3.3 % de gain |

Le gain est établi sur les petits fichiers grâce au traitement direct lorsque le parallélisme vaut 1. Sur les gros fichiers, la médiane de cette comparaison est 3,3 % plus lente ; aucune amélioration de cette charge n’est revendiquée. Les chemins multiworkers de copie restent ceux de la base avec les corrections fonctionnelles décrites dans le journal.
Les variations et temps bruts sont conservés dans `reports/comparison.json`. Les recommandations du cycle comparent des réglages de la même version ; elles ne remplacent pas cette comparaison entre versions.

## Test de 1 Gio

- Taille : 1,073,741,824 octets.
- Durée mesurée, copie et contrôles : 2.262 s.
- Débit logique : 474.8 Mo/s.
- SHA-256 indépendant : `93e202379b54a7bd392df85680a6a8b89d2d5270b9ebd2e99d7da86699f4b620`.
- Données synthétiques : répétition d’un bloc pseudo-aléatoire. Cache chaud, fsync demandé. Ce n’est ni une mesure de débit physique disque/USB, ni un transfert Internet, ni une garantie pour un autre ordinateur.

## Ce qui reste à valider

- Exécution et création d’un EXE sur Windows ; aucune machine Windows n’était connectée.
- Mesures sur vraies clés USB, SSD, disques mécaniques et réseau entre deux machines. Le HTTPS a été testé uniquement sur boucle locale.
- Métadonnées Windows avancées (ACL, flux alternatifs), chemins longs Windows et comportement FAT32 sur vrai support.
- Le mode compression adaptative utilise un échantillon pour réduire le volume ; son effet sur la durée totale demande des mesures de CPU et de réseau.
- Appairage plus simple, découverte réseau et connexion Internet sans configuration manuelle ne sont pas implémentés.

Les données, noms et dossiers pris en charge sont contrôlés ; les limitations de fidélité sont détaillées dans `README.md`.

## Reprendre le développement

1. Récupérer et extraire cette archive ; préserver son identité lors de la sauvegarde suivante.
2. Consulter `CHANGELOG.md`, ce rapport et les résultats bruts.
3. Exécuter `python3 cycle.py --cycles 1 --rounds 3` ; ne pas lancer de second cycle tant que le verrou est détenu.
4. Pour une modification de performance, comparer à un instantané de référence avec `compare_versions.py` et conserver tous les contrôles d’intégrité.
5. Mettre à jour les sources, rapports et paquet après validation. Le script de cycle produit des recommandations ; les changements de code sont effectués par le développement planifié.
