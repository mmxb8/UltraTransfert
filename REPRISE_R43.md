# Reprise R4.3

1. Récupérer le main actuel de mmxb8/UltraTransfert et lire la version actuelle
   de l'archive principale. Ne jamais pousser sur l'ancienne origine par défaut.
2. Base publiée de ce cycle : f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53.
   Base locale R4.2 : 6f1643e1a30299d4daa56b4309c15f32e3028d17.
   L'archive source a été récupérée en version 29 ; voir checkpoint R4.3.
3. pending-r43.mbox conserve la série complète non publiée depuis main.
   Dans un checkout isolé au bon parent, git am --3way permet de l'appliquer.
   Si main a changé, examiner les conflits et différences ; ne jamais forcer.
   Le patch R4.2 précédent reste historique : ne pas appliquer les deux séries.
4. Le connecteur reste maher8-git, contrôle de droits mmxb8 refusé 403.
   Aucun push ni nouveau workflow Windows n'a eu lieu. Dès accès restauré,
   publier le commit cohérent sur mmxb8 ; relancer windows-validation.yml si
   des sources embarquées sont modifiées.
5. Installer/engine/test Windows, actifs Bitcoin et EXE inchangés.
   Le SHA de l'EXE est 01349c32f77356b0e42062eaa7910ca0f5d4adaf9a3d66e6e1ff1382e41ae835.
6. Prochaine capacité : index de groupes indépendants et cache borné côté
   réception, avec maintien de l'identité de snapshot et des contrôles sur les
   blocs rechargés. Mesurer décodage répété et reprise logique avant intégration.
   Ne pas réduire le coût en supprimant SHA-256, fsync, journal ou contrôles.
7. RDP natif, redirection réelle et réactivité de session demandent des hôtes
   Windows connectés ; aucun résultat simulé ne vaut cette validation.
