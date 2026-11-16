# Composants redistribués

La licence MIT de ce projet couvre le code UltraTransfert. Elle ne remplace pas
les licences des composants tiers. Les versions et SHA-256 des entrées sont
dans `installer/inputs.lock.json` et dans le rapport de construction.

| Composant Windows | Version | Licence et notices incluses |
| --- | --- | --- |
| CPython embarqué | 3.14.10 x64 | PSF et licences incorporées, runtime/LICENSE.txt |
| Tcl / Tk | 9.0.4 | Licences Tcl/Tk dans runtime/tcl ; issus du MSI officiel CPython |
| cryptography | 50.0.2 | Apache-2.0 ou BSD-3-Clause ; dist-info/licenses dans site-packages |
| cffi | 2.1.1 | MIT ; dist-info/licenses dans site-packages |
| pycparser | 3.12 | BSD-3-Clause ; dist-info/licenses dans site-packages |
| zstandard | 0.25.0 | BSD, notices et licences du backend dans dist-info/licenses |
| NSIS | 3.11 | zlib/libpng et composants tiers, licence de l'installateur NSIS |

Le générateur de QR qrcode 8.2 (BSD) et zxing-cpp 3.1.1 (Apache-2.0) servent au
développement ; ils ne sont pas des dépendances d'exécution du logiciel.
L'icône UT a été dessinée pour ce projet. Aucun contenu de la capture de téléphone
n'est redistribué.

NSIS permet la distribution de programmes sous leur propre licence. Son code
source et ses licences sont disponibles à https://nsis.sourceforge.io/ et
https://sourceforge.net/projects/nsis/files/ . Les sources des composants tiers
restent disponibles sur leurs sites officiels ; aucun binaire tiers n'est
présenté comme un travail original d'UltraTransfert.
