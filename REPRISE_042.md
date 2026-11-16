# Reprise des optimisations 0.4.2

Base GitHub main : f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53.
Branche locale : optimize-framing-20261116.
La série R4.2/R4.3 de l’archive version 30 a été réappliquée dans ce checkout
isolé avant les changements 0.4.2. Le correctif d’identité Windows est intact.
Une autre exécution horaire pouvait produire un checkpoint ultérieur : lire
sa version actuelle avant toute mise à jour de l’archive ou publication globale.

304 tests Linux passent sans test ignoré après compilation du helper C++.
288 aller-retours de codecs et 180 copies TLS : rapports frame-cost-*.
Wheel 0.4.2 construit puis testé depuis une installation séparée.
Les changements embarqués doivent passer les runners Windows après publication.
Le dernier EXE Windows validé reste le 0.4.1 du commit f95b002.

Pour publier : utiliser mmxb8/UltraTransfert uniquement. Le connecteur actuellement
attaché a lecture seule sur ce dépôt ; la session navigateur est déconnectée.
Terminer la connexion sécurisée au compte mmxb8, examiner l’état actuel de main
et des recherches concurrentes, puis publier un commit cohérent sans force.
Suivre le workflow windows-validation.yml et corriger tout échec avant de
qualifier l’installateur 0.4.2 de testé. Ne pas utiliser l’ancienne origine.
Les gains de mémoire mesurés ne prouvent pas un gain de débit général.
