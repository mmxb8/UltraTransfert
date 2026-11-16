Recherche R3.1 : optimisation de lecture sans changement des octets comprimés. Voir RECHERCHE_LECTURE_R3.md et reports/reader-r3-summary.md ; candidat uniquement dans research/.

Mise à jour R2.2 : voir RECHERCHE_BUDGET_R2.md et reports/budget-r2-summary.md. Recherche seulement ; moteur/format publié et installateur 0.4.0 inchangés.

Mise à jour recherche R1 : prédiction XOR/différence entière, reconstruction par division et recherche en deux étapes. Voir RECHERCHE_PREDICTIVE.md et reports/predictive-summary.md pour les gains spécialisés et les régressions mesurés. La compression publiée reste inchangée.

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

# Mise à jour — 0.3.1

Le premier banc ci-dessous est conservé comme historique. Les primitives ont été déplacées dans `ultra/compression.py` et intégrées au mode HTTPS facultatif. Voir `COMPRESSION_HTTPS.md` pour les mesures réelles et la validation actuelle (69 tests). Le sélecteur ne démontre pas encore de gain face à la meilleure recette fixe testée.

---

# Laboratoire de compression — premier banc d’essai

15 novembre 2026. Expérience isolée : le moteur de transfert de production reste en version 0.3.0. Aucun nouveau codec neuronal, brevet ou algorithme inédit n’est revendiqué.

## Résultats mesurés et estimés

54 tests passent, dont 10 nouveaux tests de laboratoire. Les transformations et codecs reconstruisent les octets exacts ; les trames corrompues, tronquées ou excessives sont refusées. La suite exerce les tailles non alignées et plusieurs débits de sélection.

Le banc contient six jeux synthétiques d’environ 2 Mio. Cinq répétitions par configuration, ordre mélangé, bibliothèque système Zstandard 1.5.7. Le temps CPU de recherche, compression, reconstruction et hachage est mesuré. Le réseau n’est pas exécuté : la durée affichée est une estimation séquentielle à 10 Mbit/s, sans recouvrement des étapes. Le tableau compare le mode adaptatif au meilleur temps médian estimé parmi raw, zlib1, zstd1 et zstd3.

| Jeu synthétique | Meilleure référence testée | Référence : durée estimée | Adaptatif : durée estimée | Variation estimée |
|---|---|---:|---:|---:|
| float32_signal_synthetic | zstd3 | 1.51091 s | 0.88329 s | +41.54 % de gain |
| gzip_of_pseudo_random | raw | 1.68088 s | 1.68861 s | -0.46 % de gain |
| json_logs_synthetic | zstd3 | 0.03082 s | 0.03646 s | -18.31 % de gain |
| mixed_logs_and_random | zstd1 | 0.85808 s | 0.86676 s | -1.01 % de gain |
| pseudo_random | raw | 1.68034 s | 1.68792 s | -0.45 % de gain |
| uint32_counter_synthetic | zlib1 | 0.60692 s | 0.01448 s | +97.61 % de gain |

Les gains sur compteurs et signaux numériques sont liés à des structures synthétiques favorables aux permutations d’octets. Cette technique est connue, notamment dans Blosc ; ces mesures ne prouvent aucune nouveauté. Les journaux, données aléatoires et contenus déjà comprimés montrent les limites et le surcoût de la recherche adaptative. Aucun corpus réel d’entreprise, fichier vidéo, modèle IA réel, lien RDP ou SSD/USB physique n’a été mesuré. Les comparaisons n’incluent pas Blosc, 7-Zip/LZMA, Brotli ni tous les codecs existants.

Le prototype est conservé dans research/ comme outil expérimental, pas activé dans les transferts : ses régressions empêchent une généralisation. Les détails, choix de recettes et cinq répétitions sont dans reports/compression-lab.json.

## Piste de recherche à poursuivre

Construire une recette de compression sans perte à partir de la structure des données, puis transmettre cette recette et un résidu exact. Une grammaire bornée de prédicteurs et de transformations réversibles permettrait de rechercher des combinaisons et des paramètres ; la recette n’exécuterait pas du code arbitraire fourni par un modèle. L’apprentissage doit être validé sur des données distinctes de l’échantillon d’ajustement.

Une piste plus coûteuse serait un modèle probabiliste partagé avec codage entropique. Sa version, ses paramètres, les dictionnaires transmis et le coût d’entraînement/inférence doivent être inclus dans le bilan. Un modèle génératif ne remplace jamais les bits manquants par une approximation. La reconstruction doit rester déterministe entre les deux extrémités, avec contrôle final exact. La compression fondée sur des modèles prédictifs a déjà été étudiée ; elle ne constitue pas, seule, une invention nouvelle.

Le critère principal est le temps réel de transfert complet, avec préparation, métadonnées/dictionnaires, transport, reconstruction et vérification. La meilleure taille comprimée peut être plus lente à obtenir. Tester plusieurs débits et machines, y compris RDP quand un environnement Windows réel sera disponible.

## Sources primaires

- Google DeepMind, Language Modeling Is Compression : https://arxiv.org/abs/2309.10668
- Zstandard, performances et dictionnaires : https://facebook.github.io/zstd/ et https://github.com/facebook/zstd
- Blosc, filtres réversibles : https://www.blosc.org/c-blosc2/reference/h/c-blosc2.html
