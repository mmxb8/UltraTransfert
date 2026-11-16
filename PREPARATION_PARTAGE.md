# Préparer la connexion — UltraTransfert 0.3.18

## Sans commande OpenSSL

1. Ouvrir **Émettre en HTTPS…**.
2. Indiquer l'adresse HTTPS du poste qui émettra les données : par exemple https://192.168.1.20:8443. Le nom/IP doit être celui de ce poste. localhost est réservé à un essai sur le même ordinateur.
3. Choisir un dossier personnel de configuration, hors des données à partager. Un sous-dossier neuf est créé automatiquement.
4. Garder server-key.pem et token.txt sur l'émetteur. Transmettre uniquement acces.utconnect par un canal de confiance ; comparer l'adresse et l'empreinte avec le destinataire.

La préparation ne démarre aucun serveur et n'ouvre aucun port, service ou règle de pare-feu. Le dialogue indique explicitement ce résultat. Après préparation, choisir le dossier puis **Partager ce dossier** dans ce dialogue, et **Arrêter le partage** à la fin. Le démarrage manuel reste également possible avec les fichiers obtenus, comme dans README.md, avec --bind IP_LOCALE si nécessaire. Exemple de terminal pour un essai local :

python3 -m ultra serve SOURCE --cert CONFIG/server-cert.pem --key CONFIG/server-key.pem --token-file CONFIG/token.txt

Le destinataire ouvre l'invitation dans Recevoir en HTTPS, compare l'adresse/empreinte et choisit sa destination. Arrêter ensuite le serveur à la fin du partage. Le logiciel ne transmet pas les fichiers de connexion à votre place.

## Installation du complément

Les copies locales et HTTPS existantes restent sans dépendance Python externe. La génération automatique utilise cryptography 50.0.2 en complément facultatif. Sur Windows source, Installer_Windows.bat prévoit de créer .venv-run et d'y installer requirements-sharing.txt, puis Lancer_UltraTransfert.bat utilise cet environnement en priorité. Ces scripts restent à tester sous Windows. Après une première installation de Python via WinGet, relancer Installer_Windows.bat pour terminer la préparation.

Sous Linux/macOS source : python3 -m pip install ".[sharing]" depuis le dossier du projet. Une absence du complément est signalée avant toute création de clé. Le futur portable Windows inclura ce complément et devra tester sa préparation embarquée avant livraison. Aucun EXE Windows n'est fourni ici.

Commande développeur équivalente au dialogue :
python3 -m ultra prepare https://ordinateur:8443 NOUVEAU_DOSSIER_PRIVE

## Garanties et limites

- Nouvelle clé RSA 3072 bits, signature SHA-256, SAN correspondant au seul nom/IP saisi, usage serveur TLS ; pas un certificat d'autorité. Validité jusqu'à sept jours après création, début antidaté de cinq minutes pour tolérer un petit décalage d'horloge. L'horloge des deux postes doit rester correcte.
- Nouveau jeton aléatoire cryptographique à chaque préparation. Aucune identité, clé ni jeton antérieur n'est réutilisé implicitement. Un dossier existant est refusé intégralement. Une erreur ordinaire supprime uniquement le dossier neuf de cette tentative ; un arrêt forcé peut laisser un dossier incomplet protégé à examiner.
- Sous POSIX, dossier 0700 et fichiers 0600. Sous Windows, le code prévoit whoami et icacls, avec chemins système explicites, pour retirer les droits hérités et autoriser le compte courant avant d'écrire un secret. En cas d'échec, aucune clé n'est écrite. Ces commandes ne concernent que le dossier neuf ; aucun droit de source/destination de transfert n'est élargi. Les appels Windows sont seulement testés par doublures sous Linux : l'effet réel des ACL, y compris sur différents supports et domaines, reste à vérifier.
- La clé privée est non chiffrée au repos pour être utilisée par le serveur ; la protection repose sur ce dossier privé. Ne pas choisir un emplacement public, synchronisé ou partagé. Le serveur refuse une source contenant le chemin de sa clé privée. Les ACL des données transférées ne sont toujours pas conservées.
- Seul le fichier invitation doit quitter le poste émetteur. Il contient un accès secret en clair au dossier servi ; pas de signature de l'invitation, de permissions individuelles ni de révocation automatique par destinataire. Conserver la comparaison d'empreinte hors bande. Le certificat n'est pas ajouté au magasin système.
- Le certificat peut expirer, mais cela ne constitue pas un mécanisme d'arrêt des transferts déjà établis. Arrêter le serveur puis changer le jeton pour révoquer l'ancien accès lors d'un redémarrage. Conserver l'ancien état de copie et suivre les contrôles de reprise ; la reprise inter-transports n'est pas livrée.
- Aucun changement de débit ou de compression revendiqué : la génération RSA est variable. Aucun Windows, visuel ou RDP réel testé dans cette livraison.

## Validation et reproduction

211 tests Linux passent, avec cryptography 50.0.2 : préparation hors réseau, propriétés du certificat DNS/IP, confidentialité, refus d'écrasement et adresses invalides, dépendance absente, manque d'espace simulé, erreurs de protection Windows simulées, dialogue avec widgets doublés, TLS réel en boucle locale avec interruption/reprise et refus d'une source contenant la clé.

python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_share_setup --rounds 6

La référence OpenSSL du banc est un automatisme de test représentant l'ancienne recette manuelle, sans mesurer le temps des actions humaines. Le produit n'utilise pas OpenSSL CLI pour la nouvelle préparation. Les détails de mesure sont dans RAPPORT.md.

Références primaires consultées le 15 novembre 2026 :
https://cryptography.io/en/latest/x509/tutorial/
https://cryptography.io/en/latest/x509/reference/
https://cryptography.io/en/latest/changelog/
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/icacls

Le dialogue propose maintenant Charger une connexion existante… pour réutiliser les fichiers conservés après fermeture, sans générer de nouvelles clés et sans ouvrir de service. Voir REPRENDRE_PARTAGE.md.

Pendant l’inventaire/hachage au démarrage du partage, Annuler la préparation demande un arrêt. Attendre la confirmation ; une opération disque engagée peut prendre du temps. Fermer ce dialogue attend aussi cette confirmation. La connexion conservée reste utilisable pour recommencer.

Préparation source 0.3.12 : Installer_sans_Internet.bat est prévu si Python/tkinter existe déjà. Le moteur est contrôlé sans pip obligatoire ; un complément de création de connexion indisponible est signalé sans bloquer copies/réception. Cette possibilité ne remplace pas la construction obligatoire et complète du futur portable Windows.
