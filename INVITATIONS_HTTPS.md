# Invitation HTTPS — 0.3.18

## Parcours destinataire

1. Recevoir le fichier .utconnect par un canal de confiance ; ne pas le publier.
2. Ouvrir Recevoir en HTTPS, puis Ouvrir une invitation.
3. Comparer l'adresse et l'empreinte SHA-256 complète avec l'émetteur, par un autre canal de confiance. Confirmer seulement si elles correspondent.
4. Choisir la destination et Copier / reprendre. Attendre la confirmation de vérification finale.

Interrompre puis attendre l'arrêt ; reprendre avec la même invitation et la même destination. Après fermeture de l'application, réouvrir et confirmer l'invitation. Le moteur valide les partiels par leur contenu ; aucun contrôle SHA-256 n'est retiré. Le mode manuel reste disponible, ainsi que l'ancienne copie delta dans ses champs avancés. Importer une nouvelle invitation efface le choix de référence delta pour éviter une réutilisation implicite.

## Préparation par l'émetteur

Le parcours **Émettre en HTTPS…** génère désormais certificat, clé, jeton et invitation sans démarrer de service. Voir PREPARATION_PARTAGE.md. Le partage peut maintenant être démarré et arrêté explicitement dans le même dialogue ; voir PARTAGE_HTTPS.md. Pour exporter manuellement avec des fichiers déjà prêts selon le README :

python3 -m ultra invite https://ordinateur:8443 acces.utconnect --cert server-cert.pem --token-file token.txt

Sous Windows source, remplacer python3 par py -3. La commande crée le fichier secret sans écrasement et affiche seulement l'adresse et l'empreinte publique. Elle n'ouvre aucun service et ne prend pas de clé privée. Le fichier doit contenir un unique certificat public PEM ; les chaînes PEM multiples ne sont pas prises en charge par ce format initial. L'ancien mode manuel reste utilisable pour les configurations correspondantes.

Démarrer explicitement le serveur avec le dossier choisi, sa clé privée, le certificat correspondant et le même jeton. Le nom/IP de l'URL doit être dans les SAN du certificat. Aucun port, découverte réseau, ouverture de pare-feu ou relais n'est ajouté par cette fonctionnalité. Le serveur reste lié à 127.0.0.1 par défaut ; une écoute réseau exige l'action explicite décrite dans le README.

## Confiance et durée d'accès

Le JSON est borné à 32 Kio, avec schéma/version exacts, champs dupliqués/inconnus refusés, URL HTTPS d'origine uniquement, jeton ASCII imprimable borné et empreinte du certificat vérifiée. La lecture/importation ne contacte aucun serveur. L'empreinte interne prouve une cohérence, pas l'identité de l'émetteur : ce fichier n'est pas signé et requiert un transport de confiance plus la comparaison hors bande proposée par l'interface.

Le certificat est chargé en mémoire dans un contexte TLS vérifiant le certificat et son nom, sans mode insecure ni modification du magasin de confiance système. Le jeton reste hors URL. Toute redirection HTTP est refusée avant le renvoi d'une requête authentifiée vers une autre adresse. Le serveur authentifie le destinataire par possession du jeton ; aucune authentification mutuelle par certificats clients n'est ajoutée.

L'invitation donne le même accès en lecture au dossier entier servi que le jeton existant : aucune permission plus fine par invitation, expiration, usage unique ou révocation individuelle n'est implémenté. Arrêter le serveur interrompt le partage actif, mais relancer avec le même jeton rend à nouveau l'invitation utilisable. Pour révoquer un accès compromis, arrêter le partage puis changer le jeton avant un redémarrage. Le fichier secret n'est pas chiffré : créé en mode 0600 sous POSIX ; les ACL héritées du dossier Windows restent à vérifier. Ne pas le mettre sur un partage public. Les objets et messages d'interface ne montrent pas le jeton ; supprimer une invitation n'efface pas nécessairement toutes ses copies.

L'URL est normalisée avec un port explicite. Une reprise créée en mode manuel avec une URL textuellement différente (par exemple sans :443) peut être refusée : garder la même origine textuelle ou reprendre avec l'ancienne configuration. Ce mécanisme ne fournit pas la reprise inter-transports.

## Validation

211 tests Linux au total. Les tests des invitations couvrent : invitation sans réseau avant acceptation, acceptation/refus de confiance avec widgets doublés, copie HTTPS et interruption/reprise réelles en boucle locale, certificat/nom/jeton invalides refusés, limites de taille, corruption de l'empreinte, JSON invalide et redirections bloquées. Le rendu graphique et Windows/RDP n'ont pas été testés.

Banc reproductible :
python3 -m research.benchmark_invitations --reference DOSSIER_0_3_3 --rounds 6

Il compare l'ancien client manuel, le nouveau manuel et l'import d'invitation, avec six permutations d'ordre équilibrées sur des données synthétiques. Les durées incluent import d'invitation le cas échéant, connexion TLS, manifeste, transport brut, copie/fsync et vérifications moteur. Préparation partagée du serveur et export sont mesurés séparément. Génération du certificat et préparation des données exclues ; ce n'est pas un essai complet de première installation ni une mesure RDP. Les empreintes finales sont contrôlées indépendamment après chronométrage. Voir RAPPORT.md et reports/invitation-https-0.3.4.json.

Référence primaire consultée le 15 novembre 2026 : https://docs.python.org/3/library/ssl.html (cadata, CERT_REQUIRED, check_hostname).
