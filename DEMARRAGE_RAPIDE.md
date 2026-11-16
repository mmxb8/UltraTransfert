# UltraTransfert — démarrage rapide

Cette livraison contient désormais un véritable installateur Windows x64 bêta non signé, compilé sous Linux et encore non validé sur Windows. Ouvrir dist/UltraTransfert-0.4.0-Setup-x64-beta.exe, puis utiliser le raccourci Démarrer. Aucun Python utilisateur ou accès Internet n’est requis pour cette installation. Ne désactiver aucune protection si Windows bloque le fichier.

Les étapes ci-dessous concernent uniquement les anciens lanceurs depuis les sources ; elles ne sont pas nécessaires avec l’installateur.

1. Extraire tout le ZIP.
2. Sous Windows, ouvrir Installer_Windows.bat, puis Lancer_UltraTransfert.bat. Python/tkinter est requis. Si déjà présent et sans réseau : ouvrir Installer_sans_Internet.bat. Un complément manquant ne bloque plus les copies ; les scripts restent à tester sous Windows.
3. Choisir le dossier à copier et un dossier destination vide.
4. Cliquer sur Copier / reprendre. Attendre « Copie terminée et vérifiée », puis Ouvrir la destination pour retrouver les fichiers.

Voir le bilan : affiche le résultat de cette tentative, sans relire le disque réseau. Ce n’est pas une nouvelle vérification. Le résumé disparaît à la fermeture ; le rapport technique reste dans la destination.

Petit écran : faites défiler la fenêtre principale avec la barre verticale ou la molette pour atteindre les commandes. Tab permet de passer au contrôle suivant et de l’amener dans la zone visible.

Pour arrêter, y compris pendant l’inventaire local : Interrompre, puis attendre le résultat. Un lecteur lent peut retarder cet arrêt. Pour continuer : Reprendre avec les mêmes dossiers. Ne pas supprimer le dossier .ultratransfert-state.

Relancer la préparation : si le complément HTTPS attendu est déjà présent et fonctionne, il est réutilisé sans téléchargement. Sinon, la préparation tente de l’ajouter ; son échec laisse les copies disponibles.

Pendant la vérification finale, Interrompre laisse la copie incomplète. Reprendre avec les mêmes dossiers effectue les contrôles avant d’annoncer la réussite, même si les fichiers sont déjà présents.

En cas d'erreur, suivre l'action indiquée. Aucun fichier différent n'est écrasé. Les flux NTFS alternatifs et les droits ACL ne sont pas copiés.

RDP : un lecteur redirigé autorisé peut être sélectionné comme dossier. Cette possibilité reste à tester sur Windows ; le canal RDP natif n'est pas livré.

Préparation du futur portable sans Python utilisateur : voir CONSTRUCTION_WINDOWS.md. Le fichier PORTABLE_UTILISATEUR.txt est destiné à ce futur paquet construit sur Windows ; l’archive source actuelle ne contient pas cet EXE.

Recevoir depuis un autre ordinateur : Recevoir en HTTPS → Ouvrir une invitation → comparer l’adresse/empreinte avec l’émetteur → choisir la destination → Copier / reprendre. Le fichier d’invitation est secret ; la préparation côté émetteur reste décrite dans INVITATIONS_HTTPS.md.

Préparer les fichiers côté émetteur : Émettre en HTTPS… → adresse du poste → dossier personnel hors des données à partager. Le logiciel crée certificat et accès secret sans démarrer de serveur. Choisir ensuite le dossier et Partager ce dossier ; utiliser Arrêter le partage à la fin. Voir PARTAGE_HTTPS.md.

Après fermeture de l’émetteur : Émettre en HTTPS… → Charger une connexion existante… → choisir le dossier privé conservé → choisir la source → Partager ce dossier. Le destinataire garde son invitation et sa destination, puis Copier / reprendre.

En cas d’échec d’ouverture de l’interface : suivre le message « lancement impossible ». Un diagnostic est tenté dans le dossier personnel (Windows : %LOCALAPPDATA%\UltraTransfert\diagnostics). Si aucun message n’apparaît, vérifier l’extraction complète et relancer la préparation. Ce mécanisme ne couvre pas un interpréteur ou un bootloader absent. Relire le journal avant de le transmettre ; les diagnostics peuvent être supprimés après fermeture de l’application.

Pendant l’inventaire/hachage au démarrage du partage, Annuler la préparation demande un arrêt. Attendre la confirmation ; une opération disque engagée peut prendre du temps. Fermer ce dialogue attend aussi cette confirmation. La connexion conservée reste utilisable pour recommencer.

Pour ralentir volontairement une copie : Réglages avancés → Vitesse maximale de copie → choisir une valeur. Sans limite reste le défaut. Pour changer pendant une copie : Interrompre, attendre, modifier puis Reprendre. Il s’agit de contenu logique ; les vérifications et pointes de trafic ne sont pas plafonnées. Aucune réactivité RDP n’est garantie.

Les petits fichiers HTTPS réutilisent automatiquement les connexions autorisées, avec ou sans compression. Aucun nouveau réglage. Après une coupure réseau : attendre le résultat, puis Reprendre avec les mêmes dossiers.
