# Émettre et recevoir — UltraTransfert 0.3.18

## Émettre

Ouvrir **Émettre en HTTPS…**. Saisir l'adresse IPv4 réelle de ce poste et le port, puis **Créer les fichiers de connexion…**. Choisir un dossier personnel de configuration, hors des données à partager. Cette étape seule ne démarre aucun serveur.

Choisir le **Dossier à partager en lecture seule**, puis **Partager ce dossier**. Le bouton constitue l'action explicite d'ouverture. Attendre « PARTAGE OUVERT » : l'adresse et le dossier affichés indiquent la portée. Les champs sont bloqués pendant le partage. Le serveur n'expose que l'inventaire de ce dossier ; une source contenant le chemin de sa clé privée est refusée.

Transmettre uniquement **acces.utconnect** par un canal de confiance. La clé privée et token.txt restent sur l'émetteur. Confirmer avec le destinataire l'adresse et l'empreinte SHA-256 du certificat par un autre canal. Toute personne possédant le jeton de l'invitation a accès au dossier servi : ne pas publier ce fichier.

## Recevoir

Ouvrir **Recevoir en HTTPS**, puis **Ouvrir une invitation…**. Comparer l'adresse/empreinte avec l'émetteur avant de confirmer. Choisir une destination vide ou celle de la reprise, puis **Copier / reprendre**. Attendre « Copie terminée et vérifiée ». Le contrôle SHA-256 et l'inventaire final restent systématiques ; les données incomplètes ne sont pas annoncées réussies.

## Arrêter et reprendre

Sur l'émetteur, utiliser **Arrêter le partage**. L'écoute et les connexions suivies sont fermées avant confirmation. Fermer le dialogue actif demande aussi l'arrêt et attend le résultat. Fermer la fenêtre principale demande l'arrêt du partage ; attendre son résultat puis fermer de nouveau, comme pour une copie en cours.

Un transfert interrompu peut conserver des partiels côté destinataire. Après redémarrage avec la même préparation, la même URL et la même source inchangée, le destinataire utilise Copier / reprendre avec les mêmes chemins. Le contenu des partiels est relu et validé. Les données déjà reçues ne sont pas rappelées par l'arrêt. Redémarrer avec le même jeton réactive l'invitation ; changer le jeton pour révoquer cet accès lors d'un redémarrage. Ce n'est pas de la reprise inter-transports.

## Portée et limites du parcours initial

- Le parcours graphique accepte localhost (ce poste seulement) ou une IPv4 précise appartenant au poste émetteur. Pas d'écoute générale 0.0.0.0, d'IPv6 graphique, de DNS arbitraire, de découverte ou de traversée NAT automatique. Une adresse non locale ou un port déjà pris produit une erreur ; le logiciel ne remplace pas le service existant et n'élargit pas l'écoute.
- Le pare-feu et le réseau doivent déjà permettre la connexion. Aucun service Windows, démarrage automatique, élévation ni règle de pare-feu n'est ajouté.
- L'import de l'invitation vérifie le certificat/nom d'hôte par TLS et l'émetteur vérifie le jeton ; la confiance initiale repose encore sur la transmission de confiance et la comparaison hors bande. Pas de permissions individuelles, signature de l'invitation, authentification par certificat client ou révocation individuelle.
- L'inventaire/hachage initial de la source n'est pas encore annulable depuis le dialogue. La fermeture attend le résultat de ce démarrage avant de pouvoir arrêter. Pour les grosses sources, cette phase peut durer longtemps.
- Le serveur suit au plus 64 connexions, négocie TLS dans les threads clients (attente bornée à 5 s) et borne les attentes d'E/S à 120 s. Un client ne terminant pas sa négociation ne bloque pas l'acceptation ni l'arrêt de l'écoute. Une opération dépassant ces limites peut échouer ; la reprise reste à valider par contenu. Aucune mesure de charge hostile, réseau lent réel ou tenue continue n'est revendiquée.
- L'arrêt ferme les sockets, mais les traitements locaux déjà engagés dans des threads peuvent encore finir une lecture avant de constater la fermeture. Aucun transfert déjà complet ne peut être annulé rétroactivement.
- Compression réseau automatique habituelle ; le mode ultra expérimental et le delta avancé restent disponibles en ligne de commande. Aucun codec nouveau ni gain universel annoncé.
- Les ACL, flux NTFS alternatifs et attributs étendus des données ne sont pas copiés. Windows, ACL natives de configuration, installation/EXE, rendu graphique et RDP réel restent à valider. Les essais de GUI sont des tests de contrôleur sans écran.

## Tests et mesures reproductibles

211 tests Linux réussis : départ/arrêt/redémarrage, portée d'écoute précise, invitation cohérente avec certificat/jeton, arrêt d'un client sans négociation TLS, interruption réelle d'un transfert de 64 Mio et reprise vérifiée, démarrage/fermeture du dialogue avec widgets doublés. La suite préexistante conserve corruption, conflits, Unicode/vides, source modifiée et manque d'espace simulé.

python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_share_session --rounds 6

Le banc compare l'orchestration directe au contrôleur avec le même serveur courant, en boucle locale TLS, sans affichage. Il inclut préparation de serveur, copie/vérification et arrêt ; ce n'est pas une comparaison de performances ancien/nouveau serveur ni un essai Windows/RDP. Voir RAPPORT.md et reports/share-session-0.3.6.json.

Références primaires consultées le 15 novembre 2026 :
https://docs.python.org/3/library/socketserver.html
https://docs.python.org/3/library/ssl.html

Après fermeture de l’application, utiliser Charger une connexion existante… pour recharger le dossier privé conservé, puis sélectionner la source et Partager. Le destinataire conserve son invitation et sa destination de reprise si les paramètres restent identiques. Voir REPRENDRE_PARTAGE.md.

Pendant l’inventaire/hachage au démarrage du partage, Annuler la préparation demande un arrêt. Attendre la confirmation ; une opération disque engagée peut prendre du temps. Fermer ce dialogue attend aussi cette confirmation. La connexion conservée reste utilisable pour recommencer.
