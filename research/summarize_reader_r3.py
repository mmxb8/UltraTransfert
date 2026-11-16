"""Regenerate the R3 report from retained measurements."""
import json
from pathlib import Path


def load(name):return json.loads(Path('reports',name+'.json').read_text())


def main():
    memory=load('reader-r31-memory')
    fixed=load('reader-r3-fixed-https')
    adaptive=load('reader-r3-https');validation=load('reader-r3-validation-https')
    stress=load('reader-r3-stress')
    count=sum(len(r['raw']) for r in (fixed,adaptive,validation))
    lines=['# Bilan R3.1 — lecteur de blocs avec moins de copies mémoire', '',
           '16 novembre 2026. Candidat de recherche uniquement, sans modification du moteur, '
           'des codecs publiés, de l’interface ou de l’installateur 0.4.0.', '',
           '**Résultat : réduction du pic mémoire Python ; gains de transfert modestes et variables.** '
           'Aucun gain de compression : les mêmes trames sont transmises. Aucune supériorité générale.', '',
           '## Changements et cycles', '',
           '- R3.0 évite le détour bytearray → bytes lorsque la trame est reçue entièrement, et le tampon intermédiaire pour une lecture contenue dans un seul bloc.',
           '- R3.1 ajoute une vue en lecture seule du payload UTCP1 brut, après contrôle de l’en-tête, longueur et SHA-256 ; les autres recettes passent par le décodeur R1 inchangé.',
           '- Le lecteur rend toujours des bytes au moteur. Les contrôles de bloc, du flux complet et du terminal restent exécutés ; les derniers octets ne sont rendus qu’après validation du terminal.',
           '- Les patches restent limités aux bancs et tests. Aucun format réseau ni négociation publiés ne sont changés.', '',
           '## Lecture isolée en mémoire', '',
           '16 Mio + 117 octets pseudoaléatoires, trames brutes préparées hors chronométrage ; '
           '15 répétitions mélangées par cellule, soit 180 lectures par révision. '
           'Reconstruction et hachages inclus, réseau/écriture/encodage exclus. '
           'Le pic tracé exclut les entrées déjà construites et les espaces natifs.', '',
           '| Format | Lecture (Kio) | Ancien (ms) | R3.1 (ms) | Gain temps | Pic ancien (Mio) | Pic R3.1 (Mio) | Baisse du pic |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for fmt in ('UTCL1','UTCP1'):
        for size in (65536,1048576,4194304):
            rows={r['reader']:r for r in memory['summary'] if r['format']==fmt and r['buffer_bytes']==size}
            a,b=rows['BlockReader'],rows['LeanBlockReader']
            lines.append(f'| {fmt} | {size//1024} | {a["median_wall_seconds"]*1000:.3f} | {b["median_wall_seconds"]*1000:.3f} | {100*(1-b["median_wall_seconds"]/a["median_wall_seconds"]):+.1f} % | {a["python_peak_bytes"]/2**20:.2f} | {b["python_peak_bytes"]/2**20:.2f} | {100*(1-b["python_peak_bytes"]/a["python_peak_bytes"]):.1f} % |')
    lines += ['', 'Au tampon moteur de 1 Mio, le gain UTCP1 est de 9,3 %, sous la cible '
              'initiale de 10 % ; le pic Python passe de 17,00 à 9,01 Mio (−47,0 %). '
              'Ce sont des mesures isolées, pas un gain de transfert ou une mesure RSS.', '',
              '## HTTPS à recettes fixes — effet du lecteur isolé', '',
              'Sept répétitions par cellule. Les encodages R2 et R3 ont été comparés '
              'octet par octet pour chaque jeu/recette : six égalités confirmées dans '
              'reader-r3-fixed-frame-equality.json. Les volumes HTTP mesurés sont aussi identiques.', '',
              '| Données | Mbit/s | Recette UTCP1 | Ancien (s) | R3.1 (s) | Gain |',
              '|---|---:|---|---:|---:|---:|']
    for name in fixed['dataset_sha256']:
        for rate in (50,1000):
            rows={r['method']:r for r in fixed['summary'] if r['dataset']==name and r['link_mbps']==rate}
            for method in ('utcp-raw','utcp-subtract4'):
                a,b=rows[method+'_R2'],rows[method+'_R3']
                assert a['median_http_plaintext_bytes']==b['median_http_plaintext_bytes']
                av,bv=a['median_total_seconds'],b['median_total_seconds']
                lines.append(f'| {name} | {rate} | {method} | {av:.6f} | {bv:.6f} | {100*(1-bv/av):+.1f} % |')
    lines += ['', 'La cible d’au moins un gain médian complet de 5 % est atteinte sur les '
              'sources Python en brut UTCP1 à 1000 Mbit/s : 0,039065 → 0,036942 s '
              '(−5,4 %), mais le brut HTTPS normal reste à 0,030321 s. Les bornes des '
              'mesures se chevauchent : ancien 0,037860–0,056252 s, R3 0,036435–0,039629 s. '
              'Ne pas présenter ce petit écart comme statistiquement établi ou universel. '
              'Les autres cas fixes sont neutres, modestement favorables ou défavorables '
              '(notamment −3,3 % sur gzip avec recette subtract4 à haut débit).', '',
              '## Sélecteur adaptatif : attribution limitée', '',
              'Les campagnes avec R2.2 vs R2.2 + lecteur R3 restent intégralement conservées. '
              'Leurs gains ne sont pas tous dus au lecteur : le budget du sélecteur dépend '
              'du temps mesuré, et la recette peut varier entre répétitions.', '',
              '- Signal synthétique à 50 Mbit/s : médiane apparente améliorée de 14,6 %, mais 4/5 transferts R2 envoient 543 246 octets HTTP, contre 411 458 pour R3. Le changement de recette empêche d’attribuer ce gain au lecteur.',
              '- JSON à 1000 Mbit/s : régression apparente de 28,7 % ; R3 choisit plus souvent le brut. Cette régression reste visible, sans sélectionner uniquement les répétitions favorables.',
              '- Les cinq jeux supplémentaires proviennent du checkpoint R2 ; ils sont distincts des huit premiers mais ne constituent pas un corpus externe public ou une nouvelle validation indépendante de tous les réglages antérieurs.', '',
              '## Validation', '',
              f'- {count} copies HTTPS de comparaison réussies : {len(adaptive["raw"])} premières, {len(validation["raw"])} sur les cinq autres jeux, {len(fixed["raw"])} à recettes fixes.',
              '- 266 tests Linux réussis, dont neuf nouveaux : lectures fragmentées et non alignées, readinto, terminal vérifié avant retour, longueurs, corruption, en-têtes malformés, compatibilité des recettes et TLS avec reprise/plage/refus de publication corrompue.',
              f'- Stress TLS réel local : fichier de {stress["large_bytes"]//2**30} Gio, {stress["source_files"]} fichiers dont {stress["empty_files"]} vides, Unicode/caché et dossier vide. Interruption puis reprise de {stress["resumed_bytes"]//2**20} Mio ; inventaire et tous les SHA-256 comparés indépendamment.',
              '- Le gros fichier est composé de 256 répétitions d’un bloc pseudoaléatoire de 4 Mio, pas d’un fichier externe ou de 1 Gio d’aléas indépendants. Le stress est non plafonné et ne constitue pas une comparaison de débit.',
              '- Compilation Python et helper C++ sous Linux réussie. Aucun essai supplémentaire Windows/RDP, support USB physique, antivirus ou signature.', '',
              '## Périmètre des mesures', '',
              'Boucle TLS locale, caches chauds, débit applicatif plafonné par connexion '
              'en segments de 16 Kio ; ni latence/pertes imposées ni machines distinctes. '
              'Temps complets : préparation source/inventaire/SHA-256, TLS, sélection/codec, '
              'transport, reconstruction, écriture/fsync et contrôles moteur. Exclus : '
              'création du corpus/certificat, arrêt serveur et hachage indépendant supplémentaire. '
              'CPU des deux extrémités dans les JSON ; mémoire tracée Python uniquement '
              'dans le microbanc, aucune mesure RSS native totale. Les en-têtes HTTP sont '
              'comptés avant TLS. Aucun changement de compression, dictionnaire ou recette gratuite.', '',
              'Références conservées : HTTPS brut, version publiée, référence choisie dans '
              'le banc CPU antérieur parmi Zstd, LZMA/XZ stdlib et Blosc1, ainsi que recettes '
              'fixes UTCP1. Pas de nouvelle mesure CPU comparative des codecs, pas de '
              'Blosc2/TurboPFor/SPDP/7-Zip exécutés. Aucun corpus externe téléchargé.', '',
              '## Décision et reprise', '',
              'Conserver R3.1 comme candidat mémoire, sans l’activer en production. '
              'Ne pas attribuer les variations adaptatives au lecteur seul. Prochaines étapes : '
              'stabiliser le classement des recettes près du seuil, mesurer séparément le '
              'coût des empreintes et la fermeture des gros flux comprimés, puis tester '
              'des hôtes distincts et corpus externes avec RSS native. Une négociation '
              'explicite reste nécessaire pour intégrer UTCP1 ou un repli HTTP brut. '
              'Le canal RDP natif et les essais Windows réels restent à réaliser.']
    Path('reports/reader-r3-summary.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
