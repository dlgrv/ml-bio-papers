# TODO — план переводов

Пилот: **Kraken2** (самая короткая статья, на ней обкатываем конвейер).

Порядок чтения из методички: NCBI Taxonomy (10 мин, не статья) → Kraken2 → MetaPhlAn4 → PLOS-сравнение → Taxometer → Perseus → YACHT (самая математичная).

## Конвейер каждой статьи

1. Вытащить текст из PMC (не PDF — чистый текст без OCR-ошибок).
2. MT-перевод (субагент, глоссарий из `glossary/` обязателен).
3. Скриптовая проверка: количество заголовков/ссылок/DOI/чисел = оригиналу.
4. Ревью второй моделью по рубрике MQM → внести правки → перепроверить скриптом.
5. Заполнить `meta.yml` + шапку перевода, обновить таблицы в README.md / README.ru.md.
6. (опционально) Zenodo DOI, добавить в meta.yml.

## Статьи

- [ ] **P0 — Kraken2** (пилот)
  - Wood D.E., Lu J., Langmead B. "Improved metagenomic analysis with Kraken 2". Genome Biology 20:257 (2019)
  - DOI: https://doi.org/10.1186/s13059-019-1891-0
  - Текст: https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/ (Springer-страница пустая — брать PMC)
  - Лицензия: CC BY 4.0 · папка: `papers/2019-kraken2/` · ~2500 слов, легко-средне
- [ ] **P1 — MetaPhlAn4**
  - Blanco-Míguez A. et al. "Extending and improving metagenomic taxonomic profiling with uncharacterized species using MetaPhlAn 4". Nature Biotechnology (2023)
  - DOI: https://doi.org/10.1038/s41587-023-01688-w
  - Текст: https://pmc.ncbi.nlm.nih.gov/articles/PMC10635831/
  - Лицензия: CC BY 4.0 · папка: `papers/2023-metaphlan4/` · средне-жёстко, 40–60 мин
- [ ] **P1 — Сравнение Kraken2 vs MetaPhlAn4**
  - Karagiannis, Chen et al. "Integrative analysis across metagenomic taxonomic classifiers… (Integrative Longevity Omics Study)". PLOS Computational Biology (2026)
  - DOI: https://doi.org/10.1371/journal.pcbi.1013883
  - Текст: https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1013883
  - Лицензия: CC BY 4.0 · папка: `papers/2026-k2-vs-mpa4/` · средне, 40–50 мин
- [ ] **P2 — Taxometer**
  - Kutuzova S. et al. "Taxometer: Improving taxonomic classification of metagenomics contigs". Nature Communications 15:8357 (2024)
  - DOI: https://doi.org/10.1038/s41467-024-52771-y
  - Текст: https://pmc.ncbi.nlm.nih.gov/articles/PMC11437175/
  - Лицензия: CC BY 4.0 · папка: `papers/2024-taxometer/` · средне, 45–60 мин · ближайшая работа к проекту
- [ ] **P2 — Perseus**
  - Nguyen, Schatz. "Perseus: Lineage-Aware Refinement of Kraken2 Taxonomic Classification for Long Read Metagenomes" (2026)
  - Текст: https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/ (препринт; проверить, не вышла ли рецензируемая версия в Bioinformatics — при цитировании брать её)
  - Лицензия: **CC BY-NC 4.0** (некоммерческая!) · папка: `papers/2026-perseus/` · средне-жёстко, 45–60 мин · ключевая для проекта
- [ ] **P3 — YACHT** (самая математичная — оставить напоследок)
  - Koslicki D. et al. "YACHT: an ANI-based statistical test to detect microbial presence/absence in a metagenomic sample". Bioinformatics 40(2) (2024)
  - DOI: https://doi.org/10.1093/bioinformatics/btae047
  - Текст: https://pmc.ncbi.nlm.nih.gov/articles/PMC10868342/ (OUP напрямую отдаёт 403)
  - Лицензия: CC BY (проверить блок License перед публикацией) · папка: `papers/2024-yacht/` · жёстко, 1.5–2 ч

## Инфраструктура (после пилота)

- [ ] Quarto-сайт: `_quarto.yml`, `index.qmd` (listing по `papers/`), Action `.github/workflows/publish.yml` → gh-pages
- [ ] Zenodo-DOI для готовых переводов
- [ ] Хабр-пост по лучшей статье (Taxometer или Perseus)
