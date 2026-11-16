# UltraTransfert — transfert universel, priorité RDP

Orientation corrigée par Maher : exclusivement les transferts de fichiers locaux, USB, réseau local et à travers RDP ou d'autres protocoles de transport. Le produit doit achever de vraies copies, préserver les noms et l'arborescence, signaler ses limites de métadonnées et vérifier les données. La gouvernance générale d'agents IA et l'exécution de traitements distants sont hors périmètre.

## Proposition à construire

Un même transfert conserve son identité, ses blocs validés et son journal lorsqu'il passe d'un transport autorisé à un autre. RDP est une cible prioritaire : commencer une copie dans une session distante, reprendre après reconnexion et employer un chemin réseau autorisé plus rapide lorsqu'il existe.

Le détail technique et les étapes sont dans `VISION_TRANSFERT_RDP.md`. Le canal RDP natif, le changement de protocole sans redémarrage et le multi-chemin ne sont pas encore implémentés. La base 0.3.0 conserve son moteur local et HTTPS avec reprise et delta facultatif.
