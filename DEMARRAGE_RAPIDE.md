# Installer et copier — UltraTransfert 0.4.1 bêta

1. Ouvrir **UltraTransfert-0.4.1-Setup-x64-beta.exe** puis suivre l’assistant.
2. Ouvrir **UltraTransfert** depuis le menu Démarrer.
3. Choisir le dossier source et une destination vide.
4. Cliquer **Copier / reprendre**. Attendre **Copie terminée et vérifiée**.

Aucun Python à installer, aucune commande à saisir. Les réglages automatiques
conviennent pour commencer.

Pour interrompre, cliquer **Interrompre** et attendre la confirmation.
Pour reprendre, conserver les mêmes dossiers puis cliquer **Copier / reprendre**.
Conserver le dossier de reprise caché dans la destination. Un fichier différent
déjà présent n’est jamais écrasé.

Pour deux ordinateurs : **Émettre en HTTPS…** prépare la connexion, puis
**Partager ce dossier** démarre le partage choisi. Transmettre l’invitation
secrète au destinataire ; celui-ci utilise **Recevoir en HTTPS**. Comparer
l’adresse et l’empreinte avec l’émetteur. Cliquer **Arrêter le partage** à la fin.

L’installateur fourni provient du commit f95b002, exécution :
https://github.com/mmxb8/UltraTransfert/actions/runs/43844226030
SHA-256 : 01349c32f77356b0e42062eaa7910ca0f5d4adaf9a3d66e6e1ff1382e41ae835

Installation, copie/reprise, TLS prédictif, réinstallation et désinstallation
testées sur Windows Server 2022 et 2025. Defender a scanné ces octets et les
fichiers installés sans détection dans ces deux rapports du 16 novembre 2026.
Ces observations ne garantissent pas l’absence d’alertes sur un autre poste.

**Bêta non signée.** Windows 10/11, SmartScreen après téléchargement et RDP réel
restent à tester. Ne pas désactiver les protections si Windows bloque le fichier.

Pour RDP : seuls les lecteurs redirigés autorisés peuvent être choisis comme
dossiers ; le canal virtuel natif et la reprise entre transports ne sont pas
livrés. Les ACL, flux NTFS et attributs étendus ne sont pas copiés.

La recherche R4.3 est séparée de cet installateur ; aucune option supplémentaire
n’est à choisir pour l’utiliser.
