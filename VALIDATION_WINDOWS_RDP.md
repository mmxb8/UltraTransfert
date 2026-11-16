# Passer des sources à une version Windows vérifiée

## État réel des sources 0.4.2

La 0.4.2 modifie l'extraction des buffers Zstandard et la préparation des trames
prédictives sans changer les formats. Elle a été contrôlée sous Linux ; aucun
nouveau succès Windows n'est encore enregistré pour ces octets. Le dernier
installateur validé sur Windows Server 2022/2025 reste la 0.4.1 au commit
`f95b0023fc2fd0bd187e09c0a4dac3e6a01cdd53` :
https://github.com/mmxb8/UltraTransfert/actions/runs/43844226030.

Le prototype R2.2 (sélection prédictive) et le lecteur R3.1 sont désormais inclus
comme modules du programme et dans le nouvel installateur, en option explicite.
Leur transport possède un identifiant propre `x-ultra-predictive-v1`. L’ancien
mode expérimental `ultra` reste distinct. Un client demandant la prédiction
refuse un serveur qui ne la négocie pas. Aucun module global n’est modifié au
cours d’un transfert. La compression habituelle reste le choix initial.

À l’émission et à la réception, cocher « Compression prédictive R2.2 / lecture
R3.1 ». Pour la ligne de commande, choisir `--compression predictive` aux deux
extrémités. Les blocs, le bilan du flux et les fichiers sont toujours vérifiés.
Les gains précédents restent limités aux scénarios mesurés : cette intégration
ne démontre aucun nouveau gain de débit ni de compression.

## 1. Véritable Windows sans utiliser le PC personnel

Le fichier `.github/workflows/windows-validation.yml` prépare un installateur
à partir des entrées verrouillées puis le transmet à deux machines Windows
hébergées (`windows-2022` et `windows-2025`). Les jobs vérifient :

- l’empreinte exacte du fichier transféré ;
- l’installation sans Python système, Tcl/Tk et les ressources graphiques ;
- une copie locale interrompue puis reprise ;
- TLS et la compression prédictive avec reprise, plage partielle et SHA-256 ;
- le refus d’une seconde installation silencieuse sur un dossier déjà occupé ;
- les raccourcis et la conservation d’un fichier étranger à la désinstallation ;
- une réinstallation propre, son contrôle et une seconde désinstallation ;
- Microsoft Defender si disponible, avec statut explicite s’il ne l’est pas.

Les rapports JSON et journaux sont conservés en artefacts. Aucun job ne publie
une version et aucun serveur RDP n’est ouvert. Un statut vert ne prouve pas un
rendu visuel correct, Windows 10/11, SmartScreen après téléchargement, ou RDP.
Les runners choisis utilisent Windows Server, pas Windows client.

Le dépôt public dédié est `mmxb8/UltraTransfert`. Le workflow se lance
sur les nouveaux commits de `main`, ou manuellement dans Actions. Son état
et ses artefacts constituent la preuve de chaque exécution : ne pas déduire
une validation Windows de la seule présence de ce fichier. Les tests RDP
réels et la signature reconnue restent des étapes distinctes.

Référence officielle : https://docs.github.com/en/actions/concepts/runners/github-hosted-runners
Les dépôts privés consomment les minutes incluses et peuvent engendrer des frais
selon les réglages du compte. Le workflow n’ajoute aucun abonnement ni budget.

## 2. Essai Windows 10/11 et RDP réel

Utiliser deux PC Windows de test ou des VM Windows déjà licenciées. Ne pas
exposer RDP sur Internet pour ces essais. Ouvrir une session RDP par le chemin
habituel autorisé et rediriger un lecteur dans les ressources locales du client.

Après installation, ouvrir le dossier de l’application puis **Tester_RDP.bat**.
Choisir deux dossiers parents existants, dont au moins un sous `\\tsclient\`.
Le test crée uniquement de nouveaux sous-dossiers temporaires avec des données
synthétiques, interrompt la copie, reprend, contrôle les empreintes, puis retire
ces sous-dossiers. Les fichiers personnels existants ne sont pas remplacés.
Enregistrer le rapport JSON proposé. Refaire dans l’autre sens.

Le test refuse Linux, Wine et une session locale. Le rapport précise que le
canal virtuel RDP natif et une déconnexion/reconnexion complète de la session
ne sont pas testés. Ces deux sujets restent à développer ou vérifier ; une
copie via lecteur redirigé ne constitue pas un canal RDP propriétaire.

Dans la VM Windows propre, le script développeur peut aussi être lancé :

```powershell
./installer/Valider_Windows.ps1 -Installer ./UltraTransfert-0.4.2-Setup-x64-beta.exe -Rapport ./windows.json -ScannerDefender -RequireDefender
```

Il refuse une installation préexistante et conserve les diagnostics en cas
d’échec. Il ne désactive aucune protection et n’ajoute aucune exclusion.
L’exécution PowerShell dépend de la politique de la machine ; ne pas l’abaisser
pour ce test. Le programme de test RDP est lancé directement par le runtime inclus.

## 3. Signature reconnue

L’installateur reste non signé tant qu’un fournisseur n’a pas approuvé le
projet ou l’identité de l’éditeur. Une clé auto-signée n’apporterait pas la
reconnaissance publique recherchée et n’est pas créée ici.

Options vérifiées :

- **SignPath Foundation** : programme gratuit pour les projets open source
  admissibles. Il exige notamment un projet déjà publié, une réputation
  vérifiable, l’authentification multifacteur, une chaîne de compilation
  contrôlée, une politique publique et l’approbation de chaque signature.
  L’acceptation de ce nouveau projet n’est pas acquise.
- **Azure Artifact Signing** : service de signature avec validation d’identité ;
  l’accès Public Trust inclut les développeurs individuels canadiens selon
  Microsoft. L’inscription et les frais éventuels nécessitent une décision de
  l’éditeur, aucune souscription n’est effectuée ici.
- **Microsoft Store / MSIX** : possibilité de signature par le Store après
  adaptation du paquet et certification ; ce n’est pas une signature automatique
  de notre EXE NSIS actuel.

`installer/Signer_Publication.ps1` prépare l’alternative d’un certificat déjà
approuvé dans le magasin personnel Windows. Il exige un rapport réussi et
un scan Defender sur **le même EXE** avant de signer. Il vérifie ensuite la
signature et son éditeur. La signature modifie l’empreinte : il faut relancer
les tests Windows et Defender sur l’EXE signé avant de le publier.

Aucune demande n’a été soumise, aucun certificat n’a été délivré et aucune
approbation externe n’est annoncée. Même une signature valide ne garantit ni
absence de détections antivirus ni réputation immédiate auprès de SmartScreen.

Sources :
https://signpath.org/terms
https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation
https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview
