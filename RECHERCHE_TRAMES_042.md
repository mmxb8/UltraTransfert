# UltraTransfert 0.4.2 — coût des trames

16 novembre 2026. Deux optimisations sans changement de format ni de ratio.

## Modifications

- Extraction Zstandard par `ctypes.string_at(out, n)` : seule la zone écrite est copiée. L’ancien `out.raw[:n]` copiait d’abord toute la capacité. Les bornes, contrôles des codes de retour et refus des données surnuméraires sont conservés.
- Préparation prédictive : SHA-256 calculé une seule fois sur les octets originaux et réutilisé pour les deux en-têtes. Comparaison des tailles complètes avant allocation de la trame, puis une seule concaténation. Un en-tête plus long peut toujours déclencher le retour au brut.
- Le décodeur, les SHA-256 de blocs/flux/fichiers, la publication temporaire, fsync et le moteur de reprise ne sont pas allégés. Les formats UTCP1/UTCL1/UTCS1 restent identiques.
- Version source 0.4.2 bêta. Le code R4.3 et le correctif Windows de main sont préservés. La recherche petits fichiers reste facultative et séparée du programme.

## Mesures du calcul et de la mémoire

288 aller-retours encodage/décodage, neuf répétitions par cas/révision, ordre mélangé. Données jusqu’à 4 Mio, entrées chaudes en mémoire. Temps CPU des deux opérations, avec hachage et framing ; le contrôle indépendant d’égalité est hors temps. Mémoire mesurée séparément sur trois préparations par cas : pic Python pendant encodage seulement, entrée et espaces natifs des codecs exclus. Les résultats bruts et les SHA-256 des corpus sont conservés.

| Corpus / recette | CPU avant → après (ms) | Gain CPU | Pic Python encodage avant → après (Mio) |
|---|---:|---:|---:|
| random / raw-1-none | 9.84 → 9.11 | +7.4 % | 4.00 → 4.00 |
| random / zlib1-4-none | 149.51 → 144.27 | +3.5 % | 13.35 → 13.35 |
| random / zstd1-1-none | 19.15 → 12.71 | +33.6 % | 12.03 → 8.02 |
| random / zstd3-4-subtract | 45.57 → 44.08 | +3.3 % | 21.33 → 21.33 |
| repeated / raw-1-none | 8.65 → 9.15 | -5.8 % | 4.00 → 4.00 |
| repeated / zlib1-4-none | 31.83 → 23.69 | +25.6 % | 8.00 → 8.00 |
| repeated / zstd1-1-none | 17.33 → 11.42 | +34.1 % | 8.03 → 4.02 |
| repeated / zstd3-4-subtract | 110.58 → 121.99 | -10.3 % | 21.33 → 21.33 |
| float32 / raw-1-none | 8.14 → 8.50 | -4.3 % | 4.00 → 4.00 |
| float32 / zlib1-4-none | 133.50 → 140.09 | -4.9 % | 11.55 → 11.55 |
| float32 / zstd1-1-none | 30.74 → 27.15 | +11.7 % | 11.67 → 7.66 |
| float32 / zstd3-4-subtract | 132.96 → 130.42 | +1.9 % | 21.33 → 21.33 |
| stdlib / raw-1-none | 10.72 → 9.58 | +10.6 % | 4.00 → 4.00 |
| stdlib / zlib1-4-none | 149.99 → 149.85 | +0.1 % | 11.63 → 11.63 |
| stdlib / zstd1-1-none | 37.91 → 32.26 | +14.9 % | 9.16 → 5.14 |
| stdlib / zstd3-4-subtract | 158.87 → 155.28 | +2.3 % | 21.33 → 21.33 |

Le brut ne change pratiquement pas de chemin : ses variations illustrent le bruit du banc. Certains cas régressent malgré la suppression démontrable du travail redondant. Ne pas présenter ces écarts comme un gain garanti. Le gain mémoire Zstandard dépend d’une bibliothèque système disponible ; le runtime Windows embarqué utilise zlib en son absence.

## Transferts HTTPS complets

180 copies HTTPS authentifiées, négociation `predictive` réelle et vérification indépendante de la destination. Trois corpus de 2 Mio, deux plafonds applicatifs par connexion et cinq répétitions mélangées. Un worker, boucle locale Linux et caches chauds. Le temps inclut inventaire/hachage initial, préparation serveur, TLS client, manifeste, compression, décodage, écriture/fsync et contrôles finaux ; fixtures, certificat commun, arrêt serveur et SHA-256 indépendant supplémentaire sont hors temps. Le plafond par morceaux de 16 Kio n’émule ni RTT, ni pertes, ni deux ordinateurs.

La recette zlib fixe isole le changement de trame et correspond au codec disponible dans le runtime Windows sans DLL Zstandard. Le sélecteur adaptatif reste sensible aux mesures CPU ; ses choix peuvent différer entre deux répétitions. Brut et gzip sont les transports de référence existants. Aucun changement global n’est conservé après le banc.

| Corpus | Mbit/s | zlib fixe avant → après (s) | Adaptatif avant → après (s) | Brut (s) | gzip (s) |
|---|---:|---:|---:|---:|---:|
| random | 50 | 0.44505 → 0.43444 | 0.38654 → 0.38109 | 0.36368 | 0.51736 |
| random | 1000 | 0.23788 → 0.14664 | 0.06553 → 0.06281 | 0.04632 | 0.20202 |
| float32 | 50 | 0.28991 → 0.27929 | 0.18624 → 0.16303 | 0.36283 | 0.43134 |
| float32 | 1000 | 0.10764 → 0.11321 | 0.05201 → 0.07047 | 0.04654 | 0.15406 |
| stdlib | 50 | 0.33069 → 0.29887 | 0.15299 → 0.15568 | 0.37135 | 0.16111 |
| stdlib | 1000 | 0.11831 → 0.12497 | 0.05813 → 0.06186 | 0.04107 | 0.07326 |

Décision : conserver les deux optimisations pour la baisse de mémoire et du travail inutile, avec mêmes octets et contrôles. Les mesures HTTPS n’établissent pas un avantage régulier. À 1 Gbit/s, le brut gagne tous les trois cas après modification. Les recettes adaptatives changent avec le temps de calcul ; aucune nouvelle supériorité générale ni meilleure compression en volume n’est démontrée.

## Validation et reprise

- `python build.py` compile Python et le helper C++ avec les avertissements traités en erreurs.
- `python -m unittest discover -s tests -v` : **304 tests réussis, aucun ignoré**, en 41,865 s ; journal `reports/frame-cost-full-tests.log`. Trois tests supplémentaires comparent les octets au commit f95b002, couvrent les retours au brut, les tailles vides/non alignées/maximales, la corruption, les troncatures et les bornes Zstandard.
- Les tests existants couvrent notamment le TLS prédictif négocié avec interruption/reprise, plages partielles, refus du protocole absent, les mutations source et le correctif d’identité Windows.
- Correction de la chaîne GitHub : `python -m build` était masqué par le fichier local `build.py` et ne produisait aucun wheel. Remplacé par `python -m pip wheel --no-deps --wheel-dir wheels .`. Paquet 0.4.2 réellement construit, installé dans un dossier isolé puis importé depuis ce dossier : copie/reprise et aller-retour prédictif vérifiés. Preuve : `reports/frame-cost-installed-wheel.json`.
- Banc reproductible : `python -m research.benchmark_frame_cost --rounds 9 --https-rounds 5 --output reports/frame-cost-20261116.json`.
- Données et contexte complets : `reports/frame-cost-20261116.json`. Le code de référence gelé est dans le banc ; la référence publiée est f95b002.
- Relancer `.github/workflows/windows-validation.yml` après publication sur mmxb8. La session navigateur est actuellement déconnectée et le connecteur représente l’ancienne identité sans droit d’écriture sur mmxb8. Aucun push ni nouveau test Windows n’est annoncé.
- La dernière validation Windows réussie concerne uniquement la 0.4.1 au commit f95b002. Les modifications 0.4.2 restent à valider sur les runners. Aucun test Windows 10/11, SmartScreen, signature reconnue ou RDP réel n’est ajouté par ce cycle.
- Une tâche horaire travaillait en parallèle dans son propre checkout : récupérer son checkpoint plus récent avant fusion/publication. Ne pas remplacer l’archive principale par ce checkout sans réconciliation.

Les optimisations ne créent aucun service supplémentaire et ne modifient pas les actifs Bitcoin.
