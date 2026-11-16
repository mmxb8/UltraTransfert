Recherche R3.1 : optimisation de lecture sans changement des octets comprimés. Voir RECHERCHE_LECTURE_R3.md et reports/reader-r3-summary.md ; candidat uniquement dans research/.

Mise à jour R2.2 : voir RECHERCHE_BUDGET_R2.md et reports/budget-r2-summary.md. Recherche seulement ; moteur/format publié et installateur 0.4.0 inchangés.

Recherche R1 : les trames UTCP1 ne sont pas négociées par le protocole publié. Le banc research/benchmark_predictive_https.py injecte des codecs de recherche uniquement dans ses essais. Ne pas utiliser ces patches avec des clients habituels. Voir RECHERCHE_PREDICTIVE.md.

---

Mise à jour 0.3.19 : connexions HTTPS persistantes et framing HTTP borné pour brut/gzip/ultra. Codecs et sélecteur inchangés ; aucun nouveau gain de ratio de compression revendiqué. Mesures de transfert complet, CPU et mémoire dans RAPPORT.md. Aucun essai Windows/RDP réel.

---

Mise à jour 0.3.18 : ergonomie du formulaire principal sur écran peu haut, 211 tests Linux. Moteur/codecs inchangés ; aucune nouvelle comparaison de compression. Géométrie simulée, sans validation visuelle Windows/RDP. Contrôles 1 Gio local et HTTPS avec reprise réussis.

---

Mise à jour 0.3.17 : arrêt coopératif des inventaires et contrôles finaux. 202 tests Linux ; codecs inchangés et aucune nouvelle comparaison de compression. Contrôles 1 Gio local et HTTPS avec reprise réussis.

---

Mise à jour 0.3.16 : préparation répétée sans réinstallation du complément conforme. 195 tests Linux ; moteur et codecs inchangés, aucune nouvelle comparaison de compression. Contrôles locaux 1 Gio et HTTPS avec reprise réussis.

---

Mise à jour 0.3.15 : arrêt de l’inventaire initial local depuis l’interface, moteur/codecs inchangés. 190 tests Linux, contrôle HTTPS ultra avec reprise et contrôle local 1 Gio. Aucune nouvelle mesure comparative de compression ; fonctions expérimentales toujours facultatives.

---

Mise à jour 0.3.14 : bilan utilisateur courant en mémoire ; moteur et codecs inchangés. 185 tests Linux, contrôle HTTPS ultra mixte avec reprise et contrôle local 1 Gio réussis. Aucune nouvelle mesure comparative de compression ; les résultats ci-dessous restent historiques. Windows/RDP réels non validés.

---

# Mise à jour 0.3.13 — élagage facultatif de la recherche

Option serveur --selection-pruning, uniquement avec --compression ultra, **désactivée par défaut**. L'échantillon d'un candidat dont encodage + transport estimés ne peuvent plus battre un candidat vérifié n'est pas décodé pour poursuivre son évaluation : il ne sera pas retenu. Tous les blocs reçus et fichiers gardent leurs contrôles habituels. Aucun codec inédit.

176 tests Linux passent. Recherche CPU médiane réduite de 3,3 à 27,3 % sur douze cas synthétiques, mais régressions de CPU complet et de temps HTTPS dans certains cas. Le banc final de 240 copies HTTPS inclut brut, gzip1, Zstd1/3 avec/sans permutation4 et ancien sélecteur, préparation source et vérifications. Exemple défavorable à 1000 Mbit/s loopback : signal 0,1125 → 0,1187 s ; bonne référence fixe 0,1070 s, brut 0,1028 s. Aucun bénéfice général établi ; l'ancien principe de sélection reste donc le défaut. Voir RAPPORT.md et reports/selection-0.3.13.json / https-compression-0.3.13.json pour toutes les mesures, exclusions et commandes.

Le coût de reconstruction reste estimé à partir de l'émetteur. Pas de test sur un destinataire Windows, un lien RDP, des supports physiques ou un réseau distant. L'interface normale et ses réglages prudents ne changent pas. Les mesures historiques ci-dessous ne doivent pas être mélangées aux nouveaux totaux.

---

Mise à jour 0.3.12 : moteur et codecs inchangés, 170 tests Linux. Cycle consacré à la préparation source hors ligne ; aucune nouvelle mesure de compression.

Mise à jour 0.3.11 : codecs inchangés, 159 tests Linux. Limite volontaire de copie ajoutée ; aucune nouvelle mesure de compression ni gain de réactivité RDP démontré.

Mise à jour 0.3.10 : codecs et format inchangés ; 152 tests Linux. Cycle consacré à l’annulation de préparation du partage, sans nouveau gain de compression.

Mise à jour 0.3.9 : compression et moteur inchangés, 143 tests Linux. Cycle consacré aux diagnostics de lancement ; aucune nouvelle mesure de compression. Les résultats ci-dessous sont historiques.

# Mise à jour 0.3.8 — travail redondant supprimé

135 tests Linux réussis. Les blocs bruts ne sont plus construits/hachés deux fois ; les retours au brut comparent les tailles complètes avant allocation. Format, contrôles d'intégrité et algorithmes inchangés. Aucun codec nouveau revendiqué. Le mode reste expérimental, facultatif et désactivé par défaut.

Quinze répétitions CPU sur le chemin brut déjà sélectionné : coût encodage + reconstruction de 4 Mio réduit de 34 à 42 % sur deux blocs synthétiques. Ce n'est pas un gain total de transfert. Le banc actuel de 180 copies HTTPS (cinq répétitions, 50/1000 Mbit/s applicatifs, boucle locale Linux) inclut maintenant inventaire/hachage et configuration serveur dans le total ; exclusions explicites et SHA-256 indépendant. Déjà gzip à 50 Mbit/s : 1,4167 → 1,4095 s, mais brut à 1,3827 s. Le brut reste préférable sur ce cas. Les bonnes références fixes restent généralement meilleures lorsque leur recette est connue. Pas de gain universel ou nouveauté démontré.

Voir RAPPORT.md pour le tableau actuel, les limites et les commandes ; reports/raw-reuse-0.3.8.json et reports/https-compression-0.3.8.json pour toutes les mesures. Les chiffres 0.3.1 ci-dessous sont historiques et leur temps client exclut la préparation source ; ne pas les comparer directement aux nouveaux totaux. Aucun essai Windows/RDP, réseau distant, latence/pertes ou support physique.

---

Mise à jour 0.3.7 : moteur et codecs inchangés ; 127 tests Linux. Cycle consacré au rechargement des connexions sauvegardées, sans nouvelle expérience de compression.

Mise à jour 0.3.6 : codecs et moteur inchangés ; 113 tests Linux. Cycle consacré au partage HTTPS graphique et à son arrêt, sans nouvelle expérience de compression.

Mise à jour 0.3.5 : codecs inchangés ; 104 tests Linux. Cycle consacré à la préparation automatique de connexions HTTPS, sans nouvelle expérience de compression.

Mise à jour 0.3.4 : codecs et compression inchangés ; 91 tests Linux. Le nouveau banc concerne la réception par invitation et le client HTTP, sans compression.

Mise à jour 0.3.3 : moteur de compression inchangé ; 83 tests Linux au total. Les mesures ci-dessous sont historiques, aucune nouvelle mesure de compression dans ce cycle.

# Compression HTTPS expérimentale — UltraTransfert 0.3.1

Le mode `ultra` transforme les blocs de façon réversible, choisit un codec et conserve une recette entre blocs de nature semblable. L’objectif est de réduire le temps complet, en tenant compte du coût de compression, plutôt que de chercher uniquement le plus petit fichier. Il utilise zlib niveau 1 et, si les deux postes le possèdent, Zstandard niveaux 1/3. La permutation d’octets est une technique connue ; aucun algorithme inédit ni supériorité sur le marché n’est revendiqué.

## Utiliser le mode

Depuis le dossier extrait, démarrer le serveur comme pour HTTPS habituel, avec le certificat et le jeton décrits dans README.md :

```sh
python3 -m ultra serve SOURCE --cert server-cert.pem --key server-key.pem --token-file token.txt --compression ultra --link-mbps 50
```

Puis, sur le destinataire :

```sh
python3 -m ultra pull https://localhost:8443 DESTINATION --ca server-cert.pem --token-file token.txt --compression ultra
```

Remplacer localhost et les chemins par les valeurs réelles. Sous Windows, remplacer `python3` par `py -3`. `--link-mbps` représente une estimation fournie par l’utilisateur, pas un plafond réseau ni une mesure automatique. Le mode exige `--compression ultra` aux deux extrémités ; un client habituel peut toujours lire ce serveur sans ce mode, en brut ou gzip selon sa demande. Le mode delta fonctionne aussi avec `--delta` côté serveur et `--reuse-from ANCIENNE_COPIE` côté client.

La sélection expérimentale s’utilise uniquement en ligne de commande. L’interface conserve ses réglages habituels. Aucun Zstandard natif n’est inclus ni téléchargé ; lorsque la bibliothèque n’est pas disponible, zlib et le transfert brut restent négociables. L’exécution et les scripts d’installation restent à valider sur Windows.

## Fonctionnement

- Le flux UTCS1 transporte des blocs UTCL1 de 4 Mio au maximum, leur recette et leur SHA-256.
- Une recherche sur trois échantillons répartis du premier bloc évalue les couples codec/largeur 1, 2, 4, 8 et 16 ; le transfert brut fait partie des candidats.
- La recette est réutilisée ; une sonde sur chaque bloc permet de revenir au brut quand elle ne compresse plus. Une recherche complète a lieu au plus tard tous les 16 blocs, ou lorsque des données compressibles remplacent le brut. Sur lien très rapide, des reprofilages inutiles restent possibles.
- Si l’encodage complet augmente le volume par rapport à la trame brute, le bloc est envoyé brut. Le coût de la recherche déjà effectuée n’est pas récupérable.
- Le destinataire contrôle les longueurs avant allocation, décompresse dans une limite bornée, inverse la transformation puis vérifie chaque bloc.
- Un terminal explicite contient la longueur et le SHA-256 du flux complet. La coupure, l’absence de terminal, les données supplémentaires et les empreintes incorrectes provoquent une erreur.
- Le moteur conserve en plus ses contrôles de fichiers, de destination, de reprise et de non-écrasement. La fermeture volontaire pour interruption ne prétend pas avoir vérifié le reste du flux.

Le sélectionneur estime le coût de reconstruction sur la machine émettrice ; il ne mesure pas encore les performances réelles de la machine destinataire. La compression par blocs ajoute un peu de métadonnées, même en brut. La mémoire dépend du nombre de transferts parallèles, du bloc et du tampon de lecture.

## Mesures réelles HTTPS

15 novembre 2026. Trois répétitions, ordre aléatoire, trois jeux synthétiques d’environ 8 Mio. Boucle locale TLS avec sortie applicative plafonnée à 50 Mbit/s par connexion, par morceaux de 16 Kio. Les durées incluent les échanges de manifeste/TLS, sélection, compression, reconstruction, écriture/fsync et vérifications du moteur. Préparation du manifeste source et SHA-256 indépendant supplémentaire exclus et signalés dans les résultats bruts. Les écritures et relectures utilisent les caches du serveur.

Durées médianes en secondes :

| Données | Brut | gzip 1 | Zstd 3 | Zstd 3 + permutation 4 | Adaptatif |
|---|---:|---:|---:|---:|---:|
| float32_signal_synthetic | 1.376 | 1.535 | 1.283 | 0.746 | 0.757 |
| logs_then_random_synthetic | 1.376 | 0.847 | 0.752 | 0.767 | 0.760 |
| gzip_of_pseudo_random | 1.376 | 1.555 | 1.406 | 1.429 | 1.414 |

Le signal numérique est transféré environ **45 % plus vite que le brut** ; son trafic HTTP avant chiffrement passe de 8 391 390 à 4 130 528 octets. Cependant, la recette fixe Zstd 3 + permutation 4 est environ **1,5 % plus rapide que le sélectionneur**. Sur les journaux suivis de données aléatoires, l’adaptatif réduit aussi le temps face au brut, mais Zstd 3 fixe est environ **1,1 % plus rapide**. Pour le contenu déjà gzip, le brut reste environ **2,8 % plus rapide que l’adaptatif**.

Ces résultats démontrent une intégration fonctionnelle, pas un codec révolutionnaire. Les références fixes sont meilleures sur ces jeux lorsque leur bonne recette est déjà connue. Le mode reste expérimental et désactivé par défaut. Aucune latence, perte réseau, session RDP, machine distante, clé USB ni charge réelle d’entreprise n’a été mesurée. Les références Zstd utilisent les mêmes trames vérifiées ; gzip et brut utilisent le format HTTPS habituel. Ce banc n’inclut pas tous les codecs du marché.

`reports/https-compression.json` conserve chaque mesure, sa recette de test, les compteurs HTTP côté serveur, les SHA-256 indépendants et les bornes min/max. `block_wire_bytes` compte uniquement les flux UTCS1 complets envoyés, hors HTTP/TLS ; `file_payload_bytes` compte les octets fichier avant compression. Les flux interrompus ne contribuent pas au compteur des flux complets ; ces compteurs ne constituent pas une facturation réseau.

## Validation et prochaine étape

**69 tests passent** : moteur existant, laboratoire, flux multibloc, lectures traversant une frontière, fichiers/dossiers vides et Unicode, négociation sans Zstandard, plages non alignées, delta, interruption/reprise, trames excessives ou corrompues, terminal absent et refus de publier un fichier incomplet. Modules Python et helper C++ Linux compilés.

```sh
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m research.benchmark_https_compression --rounds 3 --mbps 50
```

La prochaine optimisation à prouver est l’adaptation à la vitesse du destinataire et la réduction du coût de sélection sur les blocs courts ou incompressibles. Il faudra ensuite mesurer des dossiers réels, plusieurs débits et des postes Windows distincts. Le canal RDP natif reste à développer ; copier depuis un lecteur redirigé dans RDP emprunte le chemin de copie de dossiers existant et ne bénéficie pas de ce nouveau transport HTTPS.
