# UltraTransfert — une copie qui garde son état entre local, réseau et RDP

Document de conception, 15 novembre 2026. Priorité donnée par Maher : uniquement le transfert de fichiers ; RDP est particulièrement important. Ce document remplace l'orientation générale agents/entreprise, archivée comme historique.

## L'expérience cible

L'utilisateur déclenche un transfert entre deux dossiers, deux postes ou un poste et une session distante. Le logiciel utilise le meilleur chemin permis et conserve le même état de transfert lorsqu'une connexion tombe ou qu'un autre chemin devient disponible.

Exemple cible : une copie de 100 Go commence au travers d'une session RDP. La session coupe après 20 Go. Une reconnexion permet de reprendre les blocs déjà confirmés. Si un chemin HTTPS ou réseau local autorisé devient accessible, il peut fournir les blocs manquants sans recréer tout le transfert. Chaque octet doit effectivement être disponible et vérifié à destination avant d'annoncer une copie achevée.

Ce comportement constitue une différenciation produit à démontrer ; aucune nouveauté scientifique, exclusivité ou supériorité universelle n'est revendiquée.

## Les cinq capacités prioritaires

1. **Un transport RDP natif.** Un canal virtuel dynamique dédié transporte les blocs et accusés de réception dans la connexion RDP établie. Ce chemin ne repose pas sur le copier-coller de fichiers. Il exige un composant côté client RDP et un composant dans la session distante, installés et autorisés.
2. **Une identité indépendante du chemin.** Les fichiers et blocs sont décrits par un manifeste de contenu stable. Des chemins Windows, URL, numéros de session ou identifiants de fichier locaux ne doivent pas, à eux seuls, définir l'identité transportable. Le manifeste et les autorisations doivent être authentifiés avant de rattacher un nouveau transport à une copie existante.
3. **Des trajets adaptatifs.** Local/USB, réseau monté SMB et HTTPS d'abord, canal RDP natif prioritaire, puis SFTP ou d'autres transports selon les usages validés. Un changement de trajet se fait dans les règles du déploiement ; il n'ouvre pas de port ou de destination externe à l'insu de l'administrateur.
4. **Des blocs et des lots efficaces.** Réutilisation de données vérifiées, découpage selon le contenu à comparer aux blocs fixes, compression sans perte selon des mesures de temps total. Regroupement des métadonnées et petits fichiers dans des échanges bornés pour réduire les allers-retours sur les liens à forte latence. Le format final reste constitué des fichiers d'origine.
5. **Une session distante utilisable.** Réguler la copie et la priorité du canal pour limiter la concurrence avec l'affichage et les interactions RDP. Mesurer le débit de copie et la dégradation de la réactivité ; aucune absence de ralentissement n'est garantie.

## RDP : ce qui existe et ce qu'il faut réellement construire

Microsoft fournit des API de canaux virtuels dynamiques. Côté session distante, `WTSVirtualChannelOpenEx` ouvre le canal avec `WTS_CHANNEL_OPTION_DYNAMIC`. Côté client RDC, un module implémente notamment `IWTSPlugin`, un listener et les callbacks de canal.

Les API et clients doivent être validés pour chaque produit ciblé. La première cible proposée est le client Windows RDC/MSTSC et un hôte Windows de test. Windows App, Azure Virtual Desktop, RemoteApp, FreeRDP ou d'autres clients ne sont pas présumés compatibles sans vérification spécifique.

L'application distante et le module client sont tous deux indispensables au mode natif. Un agent Python exécuté uniquement dans la session distante ne constitue pas un transfert natif complet. Aucun module natif RDP n'est compilé ni validé dans la version 0.3.0.

Un chemin via un lecteur redirigé `\\tsclient\...` peut fournir un premier mode utilisant le moteur de copie sur des chemins accessibles. Il faut le tester sur Windows et le présenter comme redirection de lecteur, séparément du futur canal natif. La configuration, les autorisations et les restrictions de redirection s'appliquent. Le produit ne contourne pas une politique interdisant l'export de fichiers.

Les lectures DVC peuvent contenir des en-têtes de protocole et des fragments. Le module doit réassembler les messages, borner toutes les tailles, gérer les écritures partielles, la pression de flux et la fin de session. Les callbacks du client ne doivent pas bloquer. L'état durable doit appartenir au moteur de transfert plutôt qu'au seul handle de canal.

## Sécurité et intégrité propres au transfert

- Pairage explicite des deux extrémités et autorisations par dossier et sens de transfert.
- Manifeste authentifié, noms et chemins validés ; aucune traversée de répertoires.
- Empreinte de chaque bloc, accusés de réception pour les blocs validés, puis contrôle complet des fichiers et de l'inventaire final.
- Aucun mélange entre utilisateurs, sessions ou transferts ; pas de liaison d'un nouveau chemin sur la seule connaissance d'un identifiant public.
- Fichiers temporaires, publication sûre, conflits explicites et source conservée.
- Métadonnées prises en charge annoncées ; ACL et flux NTFS à implémenter avant toute revendication de copie Windows complète.

## Rôle éventuel de l'IA

L'IA peut proposer ou ajuster la taille des lots, les tampons, le parallélisme, la compression et l'ordre de copie à partir de mesures. Le moteur doit rester utilisable sans modèle et mesurer les gains face à un réglage déterministe. L'IA ne régénère jamais les octets manquants et ne modifie ni les contenus ni les permissions.

## Comment démontrer une avancée utile

Tester sur deux machines Windows réellement accessibles :

- Gros fichier de 10 Gio et dossiers mixtes de nombreux petits fichiers, avec Unicode, fichiers cachés et dossiers vides.
- Comparaison au transfert par lecteur RDP redirigé et à un outil de copie Windows de référence, avec les mêmes garanties de vérification clairement décrites.
- Liens à plusieurs débits et latences contrôlés, en séparant simulations et réseaux réels.
- Coupure de la session à mi-transfert, reconnexion et contrôle des blocs réutilisés ; arrêt du processus puis récupération de l'état.
- Reprise de RDP vers HTTPS ou LAN sur le même manifeste authentifié ; identité et droits vérifiés à chaque bascule.
- Concurrence avec une activité interactive dans la session, en mesurant latence et débit plutôt qu'en promettant un RDP toujours fluide.

Additionner RDP et une autre connexion utilisant le même lien physique ne garantit pas un débit doublé. Le premier transfert d'un fichier inédit reste borné par le disque, le réseau et le CPU. Les gains possibles viennent du travail évité, de moins d'allers-retours, d'un meilleur chemin et de reprises efficaces.

## Prochaines étapes concrètes

1. Valider le moteur Windows sur des lecteurs redirigés RDP et documenter ce mode de bout en bout.
2. Définir un manifeste de transfert indépendant des transports et tester les reprises inter-transports sur des environnements contrôlés.
3. Construire un échange minimal de messages via DVC avec un vrai composant RDC et un vrai processus distant ; compiler et tester sous Windows.
4. Brancher le moteur de fichiers sur le canal natif, puis traiter les lots de petits fichiers et la régulation du débit.
5. Mesurer les gains, conserver les améliorations démontrées et publier uniquement les exécutables réellement construits.

Aucune machine Windows ni session RDP n'est actuellement supposée disponible. L'absence de cet environnement doit être signalée, sans confondre les tests de framing ou de transport simulé avec un essai RDP réel.

## Documentation Microsoft consultée

- Ouverture DVC, session et priorité : https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsvirtualchannelopenex
- Interfaces client : https://learn.microsoft.com/en-us/windows/win32/termserv/dvc-client-apis
- Structure du plug-in RDC : https://learn.microsoft.com/en-us/windows/win32/termserv/writing-a-client-dvc-component
- Comportement des lectures serveur DVC : https://learn.microsoft.com/en-us/windows/win32/termserv/dvc-server-apis
- Redirection des ressources et restrictions : https://learn.microsoft.com/en-us/azure/virtual-desktop/redirection-remote-desktop-protocol
