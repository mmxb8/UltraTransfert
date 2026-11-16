# Laboratoire de compression et banc HTTPS

Exécuter depuis le dossier UltraTransfert :

```sh
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_compression
python3 -m research.benchmark_https_compression --rounds 3 --mbps 50
```

Sous Windows, remplacer `python3` par `py -3`. La stdlib fournit zlib. Si une bibliothèque système Zstandard compatible est déjà présente et trouvée par ctypes, les variantes zstd1/zstd3 sont aussi testées. Aucune DLL native téléchargée n'est incluse. Le comportement Windows et la disponibilité de Zstandard sous Windows n'ont pas été testés.

`compression.py` propose des permutations réversibles de largeur 1/2/4/8/16, les codecs raw/zlib1 et Zstandard facultatif, une trame de laboratoire bornée à 4 Mio et un contrôle SHA-256 des octets reconstruits. Un sélecteur échantillonne le bloc et estime le meilleur compromis selon un débit fourni. Aucune IA ni nouveau codec neuronal n'est embarqué. Le sélecteur peut se tromper et être plus lent que le transfert brut.

Le format UTCL1 reste expérimental. Il est maintenant utilisé dans le flux UTCS1 du mode HTTPS facultatif `--compression ultra`, avec négociation des codecs et terminal vérifié. Il n’est pas utilisé par RDP natif et ne constitue pas un format d’archive. Le laboratoire ne remplace pas les contrôles de fichiers du moteur principal. Lire RECHERCHE_COMPRESSION.md pour le détail des mesures et limites.

`ultra/compression.py` porte désormais les primitives ; `research/compression.py` conserve les imports des premières expériences. `AdaptiveEncoder` réutilise une recette, vérifie des échantillons de chaque bloc et effectue une nouvelle recherche au plus tard tous les 16 blocs. Le sélecteur peut encore régresser, surtout sur réseau rapide et petites données.

## Regroupement R4.2 (laboratoire uniquement)

Lire RECHERCHE_GROUPES_R4.md et reports/bundle-r42-decision.md.
Le paramètre Python manifest_codec='deflate1' de pack active UTSB2 :
manifeste borné, comprimé seulement s'il réduit la taille, SHA-256 exact.
Le défaut reste UTSB1 ; le nouveau lecteur accepte les deux formats.
Les anciens lecteurs refusent UTSB2. Aucun format utilisateur n'est modifié.

Banc reproductible : python3 -m research.benchmark_bundle_r4 --rounds 5 --methods
bundle-auto bundle-auto-mdeflate tar-zstd1 tar-lzma1 zip-deflate files-raw-w4
--output reports/bundle-r42-final.json
(commande sur une seule ligne).

## R4.3 — index de restitution, préparation bornée

Référence préservée : smallfile_bundle_r42.py. Le mode spool=True de pack
réduit la RAM de préparation en utilisant du disque temporaire supplémentaire.
Même format, mêmes contrôles ; option de laboratoire sans nouvelle option GUI.

Commandes depuis la racine (sur une ligne chacune) :

- python3 -m unittest discover -s tests -v
- python3 -m research.benchmark_pack_memory_r43
- python3 -m research.benchmark_bundle_scaling_r43
- python3 -m research.benchmark_bundle_r4 --rounds 5 --methods bundle-auto-mdeflate-r42 bundle-auto-mdeflate bundle-auto-mdeflate-spool --output reports/bundle-r43-after-flush.json
- Première passe historique avant optimisation du buffer : python3 -m research.benchmark_bundle_r43_before_flush --rounds 5 --methods bundle-auto-mdeflate-r42 bundle-auto-mdeflate bundle-auto-mdeflate-spool tar-zstd1 tar-lzma1 zip-deflate files-raw-w4 --output reports/bundle-r43-firstpass-replay.json

Les campagnes sont distinctes ; ne pas fusionner leurs médianes pour inventer
une comparaison simultanée. La montée en nombre utilise une graine distincte.
