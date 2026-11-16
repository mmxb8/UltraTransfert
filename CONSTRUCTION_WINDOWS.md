# Construction Windows portable — 0.3.19

État : implémentation de la chaîne et tests de ses parties portables sous Linux. Aucune machine Windows accessible ; aucun EXE Windows produit, testé ou fourni dans l'archive source. Pas de validation visuelle.

## Sur le poste de construction

Windows x64 et Python x64 3.10+ avec tkinter sont requis pour construire, ainsi qu'un accès aux paquets de construction. Ouvrir Construire_EXE_Windows.bat. Le script prépare .venv-build puis exécute build_windows.py. Aucun droit administrateur n'est demandé. Le générateur refuse un hôte non-Windows et respecte .cycle.lock ; ne pas retirer un verrou actif.

PyInstaller 6.22.3 est figé dans requirements-windows-build.txt. Les dépendances installées sont enregistrées avec pip freeze. Le dossier autonome est généré dans un répertoire temporaire, compressé, extrait ailleurs et lancé avec son EXE pour contrôle. Le PATH d'essai ne contient que System32 ; PYTHONPATH/PYTHONHOME sont retirés. Le contrôle doit confirmer sys.frozen, win32 et la version courante, créer Tk/App, puis réussir une copie locale avec interruption/reprise. Le rapport reste un test embarqué limité : il ne couvre pas toutes les dépendances TLS, les serveurs HTTPS, le rendu à divers DPI, les antivirus ou RDP.

La publication conserve le ZIP testé et refuse d'écraser une archive de même version. Une construction qui échoue laisse ses journaux et n'annonce aucun nouveau portable validé. Un ancien ZIP éventuel reste distinct et ne prouve pas la réussite du dernier essai. Les fichiers pending préexistants ne sont pas supprimés automatiquement.

## Vérifications manuelles indispensables avant distribution

Sur une VM Windows x64 distincte, sans Python et sans accès réseau : extraire le ZIP dans un chemin personnel avec espaces et accents, lancer UltraTransfert.exe, copier un dossier, interrompre, attendre, reprendre et contrôler le résultat. Après une réussite, tester Ouvrir la destination dans Explorer ; confirmer son indisponibilité après interruption/erreur. Tester aussi lancement depuis un raccourci, affichage avec mise à l'échelle, fermeture pendant copie et erreurs de droits/espace. Préserver les journaux.

Tester la nouvelle version dans un dossier séparé, avec reprise d'un transfert créé par l'ancienne version. Si le manifeste n'est plus compatible, conserver l'ancienne application et ne pas effacer l'état. Supprimer seulement le dossier d'application après fermeture : source, destination et état de transfert doivent rester. Vérifier le comportement des protections Windows et la signature/distribution avant de revendiquer un installateur fiable ; ne pas contourner une protection.

HTTPS demande des essais TLS réels sur deux postes. RDP demande un hôte réel et des lecteurs redirigés autorisés ; ce contrôle local n'exerce aucun RDP. Le canal DVC natif et la reprise inter-transports restent à construire.

## Reproduire les contrôles disponibles sous Linux

python3 build.py
python3 -m unittest discover -s tests -v
python3 -c "from ultra.smoke import write_report; raise SystemExit(write_report('smoke-linux.json', require_gui=False))"

Le rapport Linux indique frozen=false et gui_created=false : il est volontairement refusé comme preuve Windows. Les tests d'archivage utilisent des fichiers factices, pas des EXE fabriqués ou présentés comme fonctionnels.

## Choix technique et références

Le format dossier est choisi pour examiner les dépendances et faciliter le diagnostic. Aucun gain de démarrage n'est mesuré ici. PyInstaller décrit les modes onedir/windowed et l'inclusion de l'interpréteur ; sa sortie dépend du système sur lequel il est exécuté.

Documentation primaire consultée le 15 novembre 2026 :
https://pyinstaller.org/en/stable/usage.html
https://pyinstaller.org/en/stable/operating-mode.html

La construction inclut maintenant cryptography 50.0.2. Le contrôle embarqué du futur EXE doit aussi préparer une connexion privée et confirmer sharing_prepared=true ; cela exercera la génération cryptographique et la protection native du dossier sur Windows. Ce parcours n’a pas encore été exécuté sur Windows. Installer_Windows.bat prépare séparément un environnement .venv-run pour l’archive source, sans installation globale de cette dépendance.

Le contrôle du futur EXE doit maintenant aussi confirmer sharing_session_checked=true après un partage TLS réel en boucle locale, copie et arrêt. Les tests de schéma de validation et du code sous Linux ne constituent pas une construction Windows exécutée.

Le contrôle du futur EXE doit aussi confirmer sharing_restore_checked=true après validation locale de la connexion sauvegardée. Cette branche est testée sous Linux avec frozen simulé, sans constituer une compilation/exécution Windows.

En cas d’échec d’ouverture de l’interface : suivre le message « lancement impossible ». Un diagnostic est tenté dans le dossier personnel (Windows : %LOCALAPPDATA%\UltraTransfert\diagnostics). Si aucun message n’apparaît, vérifier l’extraction complète et relancer la préparation. Ce mécanisme ne couvre pas un interpréteur ou un bootloader absent. Relire le journal avant de le transmettre ; les diagnostics peuvent être supprimés après fermeture de l’application.

Préparation source 0.3.12 : Installer_sans_Internet.bat est prévu si Python/tkinter existe déjà. Le moteur est contrôlé sans pip obligatoire ; un complément de création de connexion indisponible est signalé sans bloquer copies/réception. Cette possibilité ne remplace pas la construction obligatoire et complète du futur portable Windows.
