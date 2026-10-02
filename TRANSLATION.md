# Translation conventions (TRANSLATION.md)

Unified conventions for all translations in this repository.

## Per-paper pipeline

1. Extract text from PMC (not PDF — clean text, no OCR errors).
2. MT translation (subagent; glossary from `glossary/` is mandatory).
3. Scripted verification: heading/link/DOI/number counts must match the original.
4. Review by a second model against the MQM rubric → apply fixes → re-run scripted check.
5. Fill `meta.yml` + translation header; update the tables in README.md / README.ru.md.
6. (optional) Zenodo DOI, add to meta.yml.

## Pilot and reading order

Pilot: **Kraken2** (shortest paper). Reading order from the project brief:
NCBI Taxonomy (10 min, not a paper) → Kraken2 → MetaPhlAn4 → PLOS comparison → Taxometer → Perseus → YACHT (most math-heavy, do last).

## Не переводится (байт-в-байт из оригинала)

- DOI, URL, имена авторов, названия программ (Kraken2, MetaPhlAn4, Taxometer, Perseus, YACHT, Bracken, MMSeqs2, Centrifuge, Metabuli, sourmash).
- **Все числа и единицы** — символ в символ. Десятичный разделитель остаётся точкой: `66.6%`, не `66,6%`.
- Названия датасетов (CAMI2, Rhizosphere) и баз (NCBI Taxonomy, GTDB).

## Глоссарий

См. `glossary/` — один термин = один единый перевод во всех статьях. Новый термин добавляется в глоссарий в том же PR, где впервые появился.

## Обязательная шапка каждой статьи

```markdown
> **Неофициальный перевод.** Оригинал: {авторы}. «{название}». {журнал}, {год}.
> DOI: [{doi}](https://doi.org/{doi}). Лицензия оригинала: {license}.
> Перевод: {статус}, {дата}. В случае расхождений оригинал главнее.
```

## Стиль

- Читаемость важнее буквальности: не калькировать английский синтаксис.
- Каждый перевод проходит проверку: скриптовую (числа, DOI, ссылки — количество и значения совпадают с оригиналом) и ревью второй моделью по рубрике MQM.
