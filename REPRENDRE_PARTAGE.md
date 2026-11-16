# Reprendre après fermeture — UltraTransfert 0.3.18

## Émetteur

1. Ouvrir **Émettre en HTTPS…**, puis **Charger une connexion existante…**.
2. Choisir le dossier privé créé précédemment, contenant server-cert.pem, server-key.pem, token.txt et acces.utconnect. Conserver les quatre fichiers ensemble sur l'émetteur ; la clé privée ne doit pas être envoyée au destinataire.
3. Le logiciel vérifie la connexion localement et rétablit son adresse. Aucun service n'est ouvert pendant ce chargement.
4. Choisir explicitement le même dossier source, puis **Partager ce dossier**. Attendre « PARTAGE OUVERT ».

Le dossier de données n'est pas mémorisé ni partagé implicitement. Le rechargement ne démarre jamais un partage. Les détenteurs de l'invitation ont accès au dossier qui sera explicitement choisi au prochain démarrage : réutiliser ces accès pour une autre source est donc une décision de partage à prendre consciemment.

## Destinataire

Conserver l'invitation initiale et la destination avec .ultratransfert-state. Réouvrir l'invitation si l'application a été fermée, comparer l'adresse/empreinte avec l'émetteur, puis **Copier / reprendre** avec les mêmes chemins. Le moteur relit et valide les données partielles avant réutilisation ; fichier SHA-256 et inventaire final restent obligatoires.

La reprise est démontrée ici sur HTTPS avec la même URL, la même source inchangée et les mêmes fichiers de connexion, après arrêt du serveur et création d'un nouveau contrôleur. Une source, un inventaire ou une origine différente peut être refusé. Ce n'est pas une reprise inter-transports, ni un essai RDP.

## En cas de refus

Sélectionner le dossier complet et ses fichiers d'origine, pas seulement l'invitation. Une clé/certificat non concordant, une invitation/token différente, des fichiers manquants, excessifs, liés ou changés pendant la validation sont refusés. Une erreur de chargement efface la sélection prête dans le dialogue et ne réactive pas une ancienne connexion. Annuler le sélecteur conserve la sélection courante.

Si le certificat est expiré ou pas encore valide, vérifier l'horloge des deux postes. Le certificat généré est valable sept jours. Au besoin, créer une nouvelle connexion dans un nouveau dossier personnel, sans supprimer les données ou l'ancien état de copie. La confiance de la nouvelle invitation doit être confirmée à nouveau. Les clés chiffrées par mot de passe ne sont pas prises en charge par ce parcours et ne déclenchent pas de demande interactive.

Les fichiers de connexion ne sont pas réécrits, supprimés ou corrigés lors du chargement. Sous POSIX, le dossier et les fichiers secrets doivent être privés (0700/0600 normalement) ; les droits trop larges sont refusés sans chmod automatique. Sous Windows, les ACL du dossier chargé ne sont pas réévaluées par ce lecteur : conserver les fichiers dans le dossier personnel protégé d'origine. L'efficacité native des protections et le parcours Windows restent à valider sur Windows. Ne pas déplacer ces secrets sur un support public ou partagé.

Le contrôle de certificat utilise une négociation TLS bornée en mémoire avec MemoryBIO (32 échanges, 512 Kio maximum), sans socket ni ouverture de port. Ce n'est pas un transfert réseau. Il vérifie certificat, dates, nom d'hôte et clé par le moteur TLS de Python/OpenSSL. Le jeton est comparé à celui de l'invitation. Les fichiers sont contrôlés avant/après et à nouveau avant l'ouverture du partage. Ne pas modifier la configuration pendant le chargement, le démarrage ou le partage ; les contrôles ne constituent pas un instantané contre un acteur hostile capable de restaurer les métadonnées.

Le rechargement utilise uniquement la bibliothèque standard Python ; le complément cryptography reste nécessaire pour créer de nouvelles clés, pas pour recharger des fichiers valides. Aucune importation dans le magasin de certificats système, extension de permissions ou découverte réseau n'est ajoutée. L'ouverture reste sur localhost ou une IPv4 précise dans la GUI et demande l'action Partager.

## Validation et reproduction

211 tests Linux passent : chargement sans socket et sans import cryptography, fichiers conservés, mauvais jeton/clé/nom et certificats expirés/futurs refusés, clé chiffrée refusée sans prompt, limites de taille, liens et permissions POSIX, changement pendant validation/démarrage, annulation et erreur GUI, puis reprise d'une copie TLS réelle après rechargement dans un nouveau dialogue (widgets doublés). Le rendu visuel, Windows/ACL/EXE et RDP réel restent non validés.

python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_share_restore --rounds 6

Le banc compare une nouvelle génération à la réutilisation d'une connexion déjà créée, puis effectue le même cycle serveur/TLS/copie/vérification/arrêt. Le coût de création antérieur du profil sauvegardé est indiqué séparément. Ce n'est pas une accélération du moteur de transfert ni une nouvelle compression. Voir RAPPORT.md et reports/share-restore-0.3.7.json.

Référence primaire consultée le 15 novembre 2026 : https://docs.python.org/3/library/ssl.html (MemoryBIO, SSLObject.do_handshake et SSLContext.wrap_bio).
