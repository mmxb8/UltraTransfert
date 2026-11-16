# Construire l'installateur Windows

L'EXE NSIS est un véritable assistant Windows avec licence, choix du raccourci
facultatif, installation par utilisateur, contrôle local, menu Démarrer et
désinstallation déclarée dans les applications Windows. Python n'est pas requis
sur le poste destinataire. Cette bêta non signée reste à valider sur Windows.

## Construction de référence sous Debian / Linux x64

Préparer Python 3.12+, `nsis` et `msitools` depuis les dépôts de la distribution.
Le compilateur utilisé pour cette version est NSIS 3.11. Puis lancer :

```sh
python build_installer.py --cache /chemin/cache --output /chemin/sortie
```

Les téléchargements de construction viennent de python.org et files.pythonhosted.org,
avec empreintes attendues dans `installer/inputs.lock.json`. Aucune dépendance
n'est téléchargée par l'installateur chez l'utilisateur. Pour reconstruire sans
réseau, préremplir le cache avec ces fichiers et passer `--offline`.
`--makensis` et `--msiextract` acceptent les chemins des outils.
La construction refuse un fichier de sortie déjà présent.

Les outils NSIS et msitools proviennent du dépôt Debian vérifié par APT ; ils
ne sont pas inclus dans le cache applicatif. Le résultat n'est pas déclaré
bit à bit reproductible : horodatages NSIS/ZIP et environnement influencent les
octets. Les sources, entrées verrouillées, scripts et rapports permettent une
reconstruction vérifiable, sans promesse d'identité binaire.

## Structure installée

`%LOCALAPPDATA%\Programs\UltraTransfert\app` contient un runtime CPython officiel
x64, Tcl/Tk, cryptography et Zstandard, le code lisible `ultra`, le point d'entrée,
les licences, le QR et SOURCES.zip. Le fichier `_pth` isole les imports du Python
global et du répertoire courant. Les scripts Tcl sont fixés au runtime privé.
L'installateur contient un manifeste SHA-256 des fichiers et exécute un contrôle
hors ligne avant de déclarer l'installation prête.

La désinstallation utilise une liste de fichiers exacte générée à la compilation,
sans suppression récursive. Les fichiers étrangers sont laissés sur place. Les
données copiées, connexions privées et diagnostics sont hors de ce répertoire.
Une mise à niveau retire d'abord la version précédente après confirmation ; elle
ne propose pas de retour arrière automatique en cas d'échec de la nouvelle version.

## Validation Windows obligatoire avant publication recommandée

Lancer l'assistant sous un compte standard propre puis, depuis le dossier app,
exécuter pour le contrôle développeur :

```powershell
& .\runtime\python.exe .\installed_entry.py --smoke-test "$env:TEMP\ultra-smoke.json"
```

Le contrôle explicite inclut un serveur TLS local temporaire, une reprise et la
vérification finale ; il arrête le serveur à la fin. Le contrôle interne de
l'installation n'ouvre aucun port. Tester aussi les parcours réels et RDP :
le contrôle automatique ne couvre pas le canal natif RDP, qui n'est pas livré.

Signer et scanner les octets finaux comme décrit dans SECURITY.md. Aucune
signature reconnue n'est fabriquée avec un certificat auto-signé pour prétendre
éviter SmartScreen. Le rapport de construction enregistre toujours l'absence
de validation Windows, signature et scan tant qu'ils n'ont pas été réalisés.

Le script `installer/Valider_Windows.ps1` automatise sur une VM Windows propre
l'installation silencieuse, le contrôle autonome TLS/reprise, le raccourci et
la désinstallation avec conservation d'un fichier étranger. L'option
`-ScannerDefender` demande un scan Defender avant installation et enregistre
la version des signatures. Ce script est fourni mais n'a pas été exécuté ici.
Il n'efface pas les restes ni les rapports, pour permettre leur analyse.
Il ne teste pas le parcours graphique, la réputation d'un téléchargement ou
la mise à niveau ; ces essais restent également à réaliser.
