# Distribution et sécurité

Cette version est une **bêta non signée**, compilée sous Linux avec NSIS.
La compilation d'un EXE n'est pas un essai Windows. Aucun résultat Microsoft
Defender, SmartScreen, Smart App Control ou autre antivirus n'est revendiqué.
Il est impossible de garantir aucune détection ou aucun blocage sur tous les
postes. Une signature reconnue améliore l'identification de l'éditeur sans
garantir la réputation immédiate d'une nouvelle version.

Le programme ne désactive ni antivirus ni SmartScreen, ne crée aucune exclusion,
n'injecte pas de code et ne contourne pas les règles RDP d'une entreprise.
Les binaires officiels CPython sont conservés sans modification ; le code
applicatif reste lisible, sans UPX, obfuscation, téléchargement à l'installation
ou démarrage automatique. L'installateur fonctionne pour le compte courant.

Les SHA-256 détectent une modification quand la référence est fiable ; ils ne
prouvent pas à eux seuls l'identité de l'éditeur. Le manifeste installé contrôle
les octets déployés avant le premier lancement, pas une chaîne de confiance
signée. Les dépendances viennent de python.org et PyPI, avec versions et
empreintes verrouillées ; le hash du ZIP CPython correspond à sa page officielle.

Avant une distribution publique recommandée :

1. Construire et tester sur Windows 10/11 x64 propre, avec utilisateur standard,
   chemins Unicode, installation hors ligne, copie, interruption/reprise,
   émission/réception TLS, mise à niveau et désinstallation.
2. Vérifier la préservation des données et l'absence de service/connexion
   automatique. Distinguer un essai Wine d'un véritable essai Windows.
3. Signer les exécutables du projet et l'installateur avec une identité
   Authenticode reconnue, horodater puis vérifier la signature. Aucune clé privée
   ni identité de signature n'est incluse ici. Pour cette bêta, l'installateur
   et son désinstalleur restent non signés.
4. Scanner les **octets finaux**, publier les résultats datés et les empreintes.
   Un résultat négatif n'est pas une garantie pour tous les moteurs futurs.
   En cas de faux positif, demander l'analyse à l'éditeur concerné, pas au client
   de désactiver sa protection. Aucune soumission publique de fichiers privés.

Références officielles :
https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation
https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options
https://nsis.sourceforge.io/Docs/Chapter4.html

Pour signaler un problème, transmettre uniquement un exemple non confidentiel,
la version et le message d'erreur. Relire les diagnostics avant de les partager ;
ne jamais publier les jetons d'invitation, clés TLS ou fichiers clients.
