# R3 — réduire les copies mémoire du flux de compression

Hypothèse avant modification : le lecteur actuel copie une trame entière dans
un bytearray puis dans bytes, même lorsque le réseau rend la trame complète.
Chaque lecture moteur d'un Mio passe aussi par un bytearray intermédiaire.
Éviter ces copies peut réduire CPU et allocations sans changer le format,
les codecs, la sélection, les hachages ou la vérification du terminal.

Critères : restitution exacte et mêmes refus sur corruption/troncature/terminal
absent ou incorrect ; gain médian visé de 10 % sur lecture mémoire du brut
encadré et baisse du pic Python ; viser 5 % de durée HTTPS complète en moins
sur au moins un gros cas rapide face au même encodeur R2.2. Rapporter tous les
échecs et régressions. Le candidat reste uniquement dans research/ tant que
les validations représentatives, Windows et compatibilité manquent.

Comparaisons à réaliser : lecteur publié vs candidat avec les mêmes octets
UTCL1 puis UTCP1, tailles arbitraires, lectures courtes fragmentées et
frontières de blocs. HTTPS : brut normal, blocs bruts, Zstd, sélecteur R2.2,
même sélecteur + nouveau lecteur. CPU et tailles incluent le framing, la
reconstruction et les empreintes. Les mesures mémoire isolées ne sont pas
des mesures réseau. Le pacing applicatif et le coût de fermeture des réponses
comprimées restent des confondants à analyser, pas des gains de compression.

## Bilan et reproduction

Bilan complet : `reports/reader-r3-summary.md`. R3.0 et R3.1 sont conservés,
sans modifier le sélecteur R2.2. Les résultats adaptatifs ont révélé un biais
possible d'attribution (recettes variant selon le chronométrage) : une campagne
supplémentaire à recettes fixes et encodages identiques isole donc le lecteur.

```sh
python3 -m unittest discover -s tests -p test_reader_research.py -v
python3 -m research.benchmark_reader_r3 --output reports/reader-r31-memory.json
python3 -m research.benchmark_predictive_https --cpu-report reports/budget-r22-cpu.json --extra-methods budget_R2 budget_R3 raw_blocks_legacy raw_blocks_R3 --rounds 5 --mbps 50 1000 --output reports/reader-r3-https.json
python3 -m research.benchmark_budget_validation https --cpu-report reports/budget-validation-cpu.json --extra-methods budget_R2 budget_R3 raw_blocks_legacy raw_blocks_R3 --rounds 5 --mbps 50 1000 --output reports/reader-r3-validation-https.json
python3 -m research.benchmark_predictive_https --cpu-report reports/budget-r22-cpu.json --extra-methods utcp-raw_R2 utcp-raw_R3 utcp-subtract4_R2 utcp-subtract4_R3 --rounds 7 --mbps 50 1000 --only float32_held_out_synthetic actual_python_stdlib_bytes gzip_pseudorandom --output reports/reader-r3-fixed-https.json
python3 -m research.validate_reader_r3
python3 -m research.summarize_reader_r3
```

Pour reproduire R3.0 en mémoire, importer LeanBlockReader depuis
`stream_reader_r30.py` et conserver le décodeur R1 standard : cette première
révision n'utilise pas de vue UTCP1. Le fichier historique n'est pas modifié.
Les rapports CPU de référence demandent les mêmes octets sources du système ;
si leurs empreintes diffèrent, recréer d'abord ces rapports plutôt que supprimer
le contrôle d'identité. Voir RECHERCHE_BUDGET_R2.md pour leurs commandes.

Aucun réglage utilisateur supplémentaire. Le paquet garde le véritable EXE
NSIS 0.4.0 existant, non signé/non validé Windows ; ce nouvel essai n'y est pas
inclus. Pour l'utiliser : ouvrir dist/UltraTransfert-0.4.0-Setup-x64-beta.exe,
suivre l'assistant puis choisir source/destination et Copier / reprendre.
