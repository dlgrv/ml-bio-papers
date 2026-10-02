# TODO — translation plan

Pilot: **Kraken2** (shortest paper — use it to shake down the pipeline).

Reading order from the project brief: NCBI Taxonomy (10 min, not a paper) → Kraken2 → MetaPhlAn4 → PLOS comparison → Taxometer → Perseus → YACHT (most math-heavy).

## Per-paper pipeline

1. Extract text from PMC (not PDF — clean text, no OCR errors).
2. MT translation (subagent; glossary from `glossary/` is mandatory).
3. Scripted verification: heading/link/DOI/number counts must match the original.
4. Review by a second model against the MQM rubric → apply fixes → re-run scripted check.
5. Fill `meta.yml` + translation header; update tables in README.md / README.ru.md.
6. (optional) Zenodo DOI, add to meta.yml.

## Papers

- [ ] **P0 — Kraken2** (pilot)
  - Wood D.E., Lu J., Langmead B. "Improved metagenomic analysis with Kraken 2". Genome Biology 20:257 (2019)
  - DOI: https://doi.org/10.1186/s13059-019-1891-0
  - Text: https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/ (Springer page renders empty — use PMC)
  - License: CC BY 4.0 · folder: `papers/2019-kraken2/` · ~2500 words, easy-medium
- [ ] **P1 — MetaPhlAn4**
  - Blanco-Míguez A. et al. "Extending and improving metagenomic taxonomic profiling with uncharacterized species using MetaPhlAn 4". Nature Biotechnology (2023)
  - DOI: https://doi.org/10.1038/s41587-023-01688-w
  - Text: https://pmc.ncbi.nlm.nih.gov/articles/PMC10635831/
  - License: CC BY 4.0 · folder: `papers/2023-metaphlan4/` · medium-hard, 40–60 min
- [ ] **P1 — Kraken2 vs MetaPhlAn4 comparison**
  - Karagiannis, Chen et al. "Integrative analysis across metagenomic taxonomic classifiers… (Integrative Longevity Omics Study)". PLOS Computational Biology (2026)
  - DOI: https://doi.org/10.1371/journal.pcbi.1013883
  - Text: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1013883
  - License: CC BY 4.0 · folder: `papers/2026-k2-vs-mpa4/` · medium, 40–50 min
- [ ] **P2 — Taxometer**
  - Kutuzova S. et al. "Taxometer: Improving taxonomic classification of metagenomics contigs". Nature Communications 15:8357 (2024)
  - DOI: https://doi.org/10.1038/s41467-024-52771-y
  - Text: https://pmc.ncbi.nlm.nih.gov/articles/PMC11437175/
  - License: CC BY 4.0 · folder: `papers/2024-taxometer/` · medium, 45–60 min · closest work to the project
- [ ] **P2 — Perseus**
  - Nguyen, Schatz. "Perseus: Lineage-Aware Refinement of Kraken2 Taxonomic Classification for Long Read Metagenomes" (2026)
  - Text: https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/ (preprint; check whether the peer-reviewed Bioinformatics version is out — cite that one when available)
  - License: **CC BY-NC 4.0** (non-commercial!) · folder: `papers/2026-perseus/` · medium-hard, 45–60 min · key paper for the project
- [ ] **P3 — YACHT** (most math-heavy — do last)
  - Koslicki D. et al. "YACHT: an ANI-based statistical test to detect microbial presence/absence in a metagenomic sample". Bioinformatics 40(2) (2024)
  - DOI: https://doi.org/10.1093/bioinformatics/btae047
  - Text: https://pmc.ncbi.nlm.nih.gov/articles/PMC10868342/ (OUP serves 403 directly)
  - License: CC BY (check the License block before publishing) · folder: `papers/2024-yacht/` · hard, 1.5–2 h

## Infrastructure (after the pilot)

- [ ] Quarto site: `_quarto.yml`, `index.qmd` (listing over `papers/`), Action `.github/workflows/publish.yml` → gh-pages
- [ ] Zenodo DOIs for finished translations
- [ ] Habr post on the best paper (Taxometer or Perseus)
