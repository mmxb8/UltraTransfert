## 0.4.1 — intégration prédictive et préparation Windows/RDP

- Mode HTTPS prédictif distinct négocié explicitement, option graphique aux deux extrémités.
- Modules R2.2/R3.1 inclus dans le programme et son installateur ; décodeur propre à chaque flux.
- Contrôle RDP guidé, refus des simulations Linux/Wine, copie avec interruption/reprise et SHA-256.
- Workflow de validation Windows Server 2022/2025, rapports et scan Defender conditionnel.
- Script de signature par certificat approuvé et guide SignPath/Azure/Store. Aucun certificat ni essai Windows réalisé ici.

# Checkpoint recherche R3.1 (application 0.4.0 inchangée)

Lecteur expérimental : moins de copies mémoire, même grammaire et vérifications. Pic Python du microbanc UTCP1 réduit de 47 % ; gain HTTPS fixe modeste sur un cas, régressions conservées. 266 tests Linux, 1 332 copies de comparaison et stress TLS 1 Gio/514 fichiers avec reprise vérifiés. Les variations de recettes adaptatives empêchent d'attribuer leurs gains au lecteur seul. Voir RECHERCHE_LECTURE_R3.md et reports/reader-r3-summary.md. Aucune intégration au moteur ou à l'installateur.

---

# Checkpoint recherche R2.2 (application 0.4.0 inchangée)

Sélection limitée par le temps de transport brut estimé et réutilisation moins coûteuse. Trois campagnes, 1 005 copies HTTPS vérifiées et 1 940 mesures CPU ; 257 tests Linux réussis. Gain spécialisé conservé, régressions et limites documentées. Voir RECHERCHE_BUDGET_R2.md et reports/budget-r2-summary.md. Aucune intégration au moteur ou à l’installateur.

---

# Checkpoint de recherche prédictive R1 (application 0.4.0 inchangée)

Ajout du laboratoire réversible XOR/différence arithmétique, de sa reconstruction optimisée, de bancs CPU/HTTPS reproductibles et de 15 tests. 250 tests réussis et 305 copies HTTPS vérifiées. Sur un signal float32 synthétique distinct à 50 Mbit/s : 36,7 % de temps complet en moins face à Zstd3+shuffle4 ; régressions sur d’autres cas. Voir RECHERCHE_PREDICTIVE.md et reports/predictive-summary.md. Code de production et installateur inchangés.

---

# Journal

## 0.4.0 — 15 novembre 2026

- Véritable installateur Windows NSIS x64 : assistant en français, installation par utilisateur, runtime Python/Tcl/Tk et dépendances inclus, raccourci Démarrer, Bureau facultatif et désinstallation inscrite dans Windows.
- Installation sans terminal, Python préinstallé ou réseau ; contrôle local des fichiers SHA-256, ressources GUI et reprise avant confirmation.
- Licence MIT, sources complètes embarquées, notices des bibliothèques et construction documentée avec versions/empreintes verrouillées.
- Dons Bitcoin facultatifs : adresse exacte de Maher, copie manuelle et QR PNG/SVG décodé indépendamment ; aucune transaction automatique.
- Désinstallation par liste exacte sans suppression récursive des dossiers. Mise à niveau précédée du retrait de l'ancienne installation après confirmation ; pas de retour arrière automatique.
- Installateur réellement compilé sous Linux, non signé et non validé sur Windows. Aucun scan antivirus/SmartScreen revendiqué. Moteur/compression inchangés ; aucun gain de débit annoncé.

## 0.3.19 — 15 novembre 2026

- Réutilisation bornée des connexions HTTPS par origine, validation TLS et authentification de chaque requête conservées. Fermeture après transfert/erreur de préparation ; délégation delta et nettoyage des sources non utilisées.
- Réponses HTTP/1.1 : longueur explicite en brut, framing chunked et tampon borné pour les réponses gzip/ultra de 64 Kio maximum ; gros flux comprimés conservés en fermeture de connexion. Pas de tampon du fichier complet, aucun changement des codecs ni des manifestes.
- TCP_NODELAY côté serveur : suppression du retard des petites réponses persistantes observé au premier essai. Plusieurs écritures gzip regroupées dans un tampon de 64 Kio ; extension aux gros flux rejetée après régression mesurée.
- Réponses abandonnées, tronquées ou exigeant fermeture exclues du pool ; maximum huit connexions inactives, pas de retry silencieux ni de redirection. Reprise par contenu préservée.
- 224 tests Linux, treize tests depuis le wheel installé, 160 comparaisons finales + vingt complémentaires (256 Mio), intégrité HTTPS avec reprise jusqu’à 1 Gio. Gains petits fichiers vérifiés ; régressions sur certaines charges conservées dans le rapport.
- Voir RAPPORT.md pour les validations, mesures complètes et limites. Aucun EXE Windows construit ni essai Windows/RDP réel.

## 0.3.18 — 15 novembre 2026

- Fenêtre principale défilante : barre verticale, molette locale à la fenêtre et visibilité du contrôle lors de la navigation clavier ; réglages avancés accessibles en défilant.
- Hauteur minimale 400 au lieu de 700, taille initiale adaptée à l’écran ; textes explicatifs enveloppés à 600 pixels. Largeur minimale 720 conservée.
- 211 tests Linux, mesures de géométrie simulée, intégrité SHA-256 locale 1 Gio et HTTPS avec interruption/reprise. Aucun gain de débit/compression revendiqué.
- Aucun rendu visuel ni essai Windows/RDP réel ; sources sans EXE Windows construit. Moteur et codecs inchangés.

## 0.3.17 — 15 novembre 2026

- Interruption des inventaires destination et des recontrôles source, signal transmis aux sources locale/HTTPS/delta. Arrêt vérifié aussi pendant/après application des métadonnées de dossiers.
- Correction : une source sans fichiers ne peut plus être annoncée réussie après arrêt au début de l’inventaire final. Annulations typées normalisées, erreurs réelles conservées.
- 202 tests Linux, reprise intégralement vérifiée après arrêt final, comparaison de douze copies locales ; contrôles SHA-256 1 Gio et HTTPS mixte.
- Codecs, interface et préparation Windows inchangés ; aucun EXE Windows construit ni essai visuel/Windows/RDP réel.

## 0.3.16 — 15 novembre 2026

- Préparation répétée : complément cryptography 50.0.2 contrôlé et réutilisé sans pip/réseau s’il est déjà prêt. Les contrôles moteur/Tcl/copie/reprise restent systématiques.
- Version différente ou import impossible : installation toujours tentée en mode normal ; hors ligne ou après échec, copies/réception conservées. Rapport distingue réutilisation et tentative d’installation.
- 195 tests Linux, comparaison de douze préparations avec pip de référence forcé hors ligne, contrôles SHA-256 1 Gio et HTTPS interrompu/repris.
- Sources sans EXE Windows construit ; scripts Windows, visuel et RDP réels non validés. Moteur/codecs/GUI inchangés.

## 0.3.15 — 15 novembre 2026

- Interrompre fonctionne dès l’inventaire initial local : raccordement au signal d’annulation existant du moteur. Retour explicite et Reprendre avec les mêmes dossiers.
- Annulation typée distinguée des erreurs réelles ; aucun dossier destination créé si l’inventaire est annulé avant copie.
- 190 tests Linux, dont cinq nouveaux tests de préparation/copie/reprise et préservation de destination ; comparaison alternée sur 3 000 fichiers. Contrôles SHA-256 HTTPS mixte et 1 Gio.
- Moteur et codecs inchangés. Sources et wheel ; aucun EXE Windows compilé ni essai visuel/Windows/RDP réel.

## 0.3.14 — 15 novembre 2026

- Bouton Voir le bilan : résumé français de la tentative courante, défilant et en lecture seule ; compteurs copiés/identiques/repris, résultat et actions.
- Correction : un échec avant écriture du rapport ne peut plus faire afficher une ancienne réussite. Capture bornée en mémoire ; aucune lecture réseau/disque au clic, sans recopier les empreintes.
- 185 tests Linux, reprise réelle du contrôleur, inventaire/SHA-256 HTTPS 259 fichiers et 1 Gio local ; comparaison reproductible de préparation de rapports synthétiques.
- Moteur, codecs, appairage et construction Windows inchangés ; aucun EXE Windows construit et aucun essai visuel/Windows/RDP réel.

## 0.3.13 — 15 novembre 2026

- Option expérimentale --selection-pruning : borne du modèle pour écarter des candidats qui ne peuvent améliorer le score estimé ; candidat retenu vérifié, contrôles du destinataire inchangés.
- Désactivée par défaut : coût de recherche réduit sur le banc CPU mais gain HTTPS non général, résultats défavorables conservés.
- 176 tests Linux, banc CPU 588 essais, banc final 240 copies HTTPS avec références Zstd1/3 fixes et ancien sélecteur ; reprise mixte 64 Mio et contrôle 1 Gio vérifiés.
- Interface d’installation/copie inchangée ; aucun EXE Windows construit et aucun essai visuel/Windows/RDP réel.

## 0.3.12 — 15 novembre 2026

- Préparation source hors ligne sans pip obligatoire ; contrôle moteur/Tcl/copie/reprise, complément de connexion facultatif et résultat partiel explicite.
- Installer_sans_Internet.bat prévu, arrêt avant WinGet si Python manque ; avis de préparation partielle dans l’interface et journaux reproductibles.
- Venv inconnu, verrou et rapport temporaire existants préservés ; nettoyage des échecs possédés.
- 170 tests Linux, douze préparations hors ligne et un ajout réel du complément en environnement isolé ; contrôles intégrité TLS mixte/1 Gio.
- Sources sans EXE Windows construit. Scripts/visuel/Windows/RDP réels non validés ; moteur et codecs inchangés.

## 0.3.11 — 15 novembre 2026

- Limite facultative de copie dans Réglages avancés et --limit-mb-s ; budget commun aux workers, attente interruptible, consigne enregistrée dans le rapport. Sans limite par défaut.
- Préfixes de reprise et empreintes source concernés ; vérification finale et trafic physique hors plafond. Helper natif simultané refusé.
- 159 tests Linux, 36 copies local/TLS comparées et vérifiées, contrôle 1 Gio et reprise TLS mixte. Aucun gain de débit/compression ou de réactivité RDP revendiqué.
- Sources et paquet Python, aucun EXE Windows construit ; visuel et Windows/RDP réels non validés.

## 0.3.10 — 15 novembre 2026

- Annuler la préparation du partage pendant inventaire/hachage ; fermeture du dialogue après confirmation, fermeture principale demandant l’annulation.
- Contrôles coopératifs avant/après bind et traitement de l’événement prêt tardif sans annonce trompeuse ; erreurs réelles distinctes.
- 152 tests Linux ; banc de six répétitions par variante, copie/reprise TLS après annulation, contrôles mixte 64 Mio et local 1 Gio.
- Compression inchangée ; aucun nouveau débit revendiqué. Windows/visuel/RDP réels non validés, aucun EXE livré.

## 0.3.9 — 15 novembre 2026

- Lancement protégé : message français et diagnostic personnel en cas d’exception Python ; secours natif Windows prévu sans dépendre de tkinter.
- Lanceur source préparé utilisant pythonw, cas archive incomplète/démarrage impossible expliqués ; scripts Windows non exécutés ici.
- 143 tests Linux, comparaison de dix échecs réels sans DISPLAY, journal absent/espace simulé, intégrité 1 Gio et HTTPS mixte interrompu/repris. Aucun gain de débit ou compression revendiqué.
- Sources et paquet Python, sans EXE Windows construit ; visuel, Windows et RDP réels non validés.

## 0.3.8 — 15 novembre 2026

- Ouvrir la destination après réussite vérifiée : dossier du transfert terminé, bouton désactivé après interruption/erreur, ouverture en arrière-plan et action manuelle si indisponible.
- Trames brutes : suppression du deuxième hachage/allocation identique ; comparaison des tailles complètes avant fallback, sans modifier le format ni les contrôles.
- 135 tests Linux ; compatibilité octet pour octet, retour au brut/corruption et contrôleur de résultat. Essai local 1 Gio et 180 copies HTTPS vérifiés.
- Mesures ancien/nouveau, brut et références fixes à 50/1000 Mbit/s en boucle locale ; gain CPU isolé net, gain total modeste sur contenu déjà gzip, brut toujours préférable sur ce cas. Compression ultra facultative et expérimentale.
- Sources et paquet Python ; aucun EXE Windows construit. Installation, visuel et RDP réels non validés ; canal natif et reprise inter-transports non livrés.

## 0.3.7 — 15 novembre 2026

- Charger une connexion existante… dans Émettre : conserver certificat/clé/jeton/invitation après fermeture, rétablir l’adresse, choisir la source et partager explicitement sans recréer d’accès.
- Chargement borné et sans socket, validation TLS en mémoire des dates/nom/clé, cohérence du jeton, refus des liens et droits POSIX trop larges, détection des changements jusqu’avant écoute. Aucun fichier corrigé automatiquement.
- Clé chiffrée refusée sans demande interactive ; échec de rechargement sans retour implicite à une ancienne sélection.
- 127 tests Linux, reprise TLS réelle après rechargement dans un nouveau contrôleur, mesures nouvelle préparation vs connexion conservée. Contrôle du futur portable renforcé.
- Moteur/codecs inchangés ; sources sans EXE Windows construit. Visuel, Windows/ACL et RDP natif non validés.


## 0.3.6 — 15 novembre 2026

- Parcours Émettre en HTTPS : préparation hors ligne, dossier source explicite, démarrage/arrêt depuis la GUI et fermeture du dialogue après arrêt. Champs bloqués pendant le partage ; adresse modifiée exige une nouvelle préparation.
- Écoute graphique sur IPv4 précise ou localhost, invitation/certificat/jeton contrôlés avant ouverture ; pas de règle de pare-feu créée.
- Connexions suivies et fermées à l’arrêt ; négociation TLS déplacée dans les threads clients pour éviter un arrêt bloqué par une négociation inachevée. Capacités/attentes bornées. Certificat/clé chargés avant écoute pour éviter une écoute résiduelle en cas d’erreur TLS.
- 113 tests Linux, interruption réelle de 64 Mio avec reprise, client TLS inactif arrêté, contrôleur de dialogue avec copie TLS réelle. Contrôle du futur portable renforcé par une copie TLS et son arrêt.
- Banc cycle complet six répétitions ; moteur et codecs inchangés. Windows, EXE, visuel et RDP réels non validés ; aucun gain de vitesse revendiqué.


## 0.3.5 — 15 novembre 2026

- Dialogue français et commande prepare : création automatique du certificat DNS/IP, clé privée, jeton et invitation, sans serveur ni commande OpenSSL.
- Dossier neuf protégé avant secrets, refus d’écrasement et nettoyage d’erreur ; protection Windows prévue avec outils natifs, non exécutée sur Windows.
- Source contenant la clé privée du serveur refusée avant écoute.
- Complément sharing facultatif cryptography 50.0.2, scripts source Windows avec environnement .venv-run ; futur portable soumis à un contrôle de génération embarquée. Scripts/EXE Windows encore non validés.
- 104 tests Linux, banc de préparation + transfert TLS complet, 1 Gio vérifié ; moteur et codecs inchangés, aucun gain de compression ou débit revendiqué.


## 0.3.4 — 15 novembre 2026

- Réception HTTPS avec un seul fichier d’invitation secret : confirmation explicite de l’adresse et de l’empreinte, confiance TLS chargée en mémoire ; configuration manuelle conservée.
- Commande invite pour exporter à partir de certificat/jeton existants sans ouvrir de service et sans écraser de fichier. Génération automatique de certificats non livrée.
- Invitations bornées et validées, aucun secret dans les messages normaux ; certificat, nom d’hôte et jeton toujours obligatoires. Redirections authentifiées refusées.
- Client HTTP réutilisant son opener ; 91 tests Linux, banc HTTPS synthétique de six répétitions avec trois configurations, et essai de 1 Gio vérifié.
- Sources/scripts livrés ; Windows, visuel et RDP réel restent non validés. Compression et moteur de copie inchangés.


## 0.3.3 — 15 novembre 2026

- Chaîne de construction Windows x64 portable : dossier autonome PyInstaller, dépendance principale figée, verrou de projet, essai du ZIP extrait et publication sans écrasement. Code développé sous Linux ; aucune construction Windows réalisée.
- Contrôle embarqué lancé depuis l’exécutable : création Tk, copie Unicode/cachés/vides, interruption/reprise et SHA-256 ; échec explicite sans publication.
- Instructions de lancement, raccourci, mise à niveau et suppression du futur portable ; sources encore livrées sans EXE Windows.
- 83 tests Linux réussis ; mesures locales, essai indépendant 1 Gio et rapports du contrôle embarqué. Moteur/GUI/codecs inchangés, aucun gain de vitesse annoncé.


## 0.3.2 — 15 novembre 2026

- Parcours français en trois étapes ; réglages avancés repliés, choix automatiques conservés.
- Champs, sélecteurs et onglets bloqués pendant la copie, puis restaurés avec le même mode.
- Interruption demandée et erreur moteur distinguées : les conflits ne sont plus masqués par le signal d’abandon interne. Bouton Reprendre et message d’attente explicites.
- Inventaire et vérification finale affichés sans estimation de pourcentage ; actions proposées après erreur.
- Six tests de contrôleur supplémentaires, moteur réel et widgets doublés : 75 tests réussis. Pas de validation visuelle, Windows ou RDP réel dans cet environnement.
- Moteur et codecs inchangés ; mesures de contrôle conservées, aucun gain de vitesse revendiqué.


## 0.3.1 — 15 novembre 2026

- Compression HTTPS expérimentale et facultative `ultra` : recettes codec/permutation, blocs bornés et SHA-256, négociation des codecs, réutilisation des recettes et terminal contrôlé.
- Reprise, plages et delta testés avec ce transport ; aucun changement du réglage par défaut.
- 69 tests et banc réel HTTPS plafonné à 50 Mbit/s, trois répétitions par cas ; résultats dans COMPRESSION_HTTPS.md.
- Gains face au brut sur données synthétiques compressibles, mais pas de gain démontré face à la meilleure recette fixe testée ; régression sur données déjà gzip. Aucun codec inédit revendiqué.

## 0.3.0 — 15 novembre 2026

- Mode HTTPS delta facultatif : empreintes par blocs de 4 Mio, récupération bornée des plages et réutilisation depuis une ancienne copie, y compris renommée.
- Validation SHA-256 de chaque bloc réutilisé/téléchargé, plus contrôles complets du moteur.
- Statistiques de reconstruction dans le rapport et sélection de référence dans l’interface.
- 44 tests réussis et démonstration HTTPS de 1 Gio avec compteurs côté serveur.
- Volume fichier téléchargé réduit de 99,61 % dans le cas testé ; durée totale plus élevée sur boucle locale rapide (voir rapport). Aucune accélération générale revendiquée.
- Vision « dossier vivant » documentée ; les fonctionnalités de lecteur virtuel et de multi-source restent à développer.

## 0.2.0 — 15 novembre 2026

- Réutilisation du chemin direct en mode un seul worker : suppression du passage par les futures pour les copies et vérifications séquentielles ; tous les contrôles SHA-256 sont conservés.
- Vérification interrompable et contrôle préalable de l'espace libre.
- Libération du verrou même si l'enregistrement du rapport échoue.
- Compression HTTPS automatique selon le contenu de l'échantillon.
- Interface : réception HTTPS, choix du parallélisme, étapes de vérification et consultation du rapport.
- Scripts de démarrage, préparation de Python et construction EXE sur Windows ; paquet Python installable.
- 33 tests, comparaison alternée de sept répétitions et essai indépendant de 1 Gio.
- Une première variante utilisant des tampons réutilisables a été retirée : les mesures initiales ne montraient pas d'amélioration stable. Le helper C++ reste facultatif pour la même raison.

## 0.1.1

Base retrouvée au début de cette session : moteur Python, helper C++, HTTPS, interface locale et 28 tests. Copie des sources dans `history/v0.1.1` pour permettre une comparaison reproductible.
