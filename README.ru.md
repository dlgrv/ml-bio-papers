<div align="center">

# ml-bio-papers

Неофициальные переводы и структурированные конспекты научных статей по машинному обучению в биологии — метагеномика, белки, молекулы.

Каждый перевод указывает оригинал (DOI), лицензию, под которой он сделан, и статус проверки: машинный перевод, машинный перевод + проверка второй LLM-моделью или вычитано человеком.

![Papers](https://img.shields.io/badge/Статьи-6-3451b2?style=flat-square)
![License of translations](https://img.shields.io/badge/Переводы-CC%20BY%204.0-18794e?style=flat-square)
![Originals](https://img.shields.io/badge/Оригиналы-Open%20access-915930?style=flat-square)

**[Индекс статей](#статьи)** | [Правила перевода](TRANSLATION.md) | [Глоссарий](glossary/README.md)

</div>

## Languages

| Язык | README |
| --- | --- |
| 🇬🇧 English | [README.md](README.md) |
| 🇷🇺 Русский | [README.ru.md](README.ru.md) |

---

## Статьи

| Год | Статья | Журнал | Оригинал (DOI) | Полный текст | Лицензия | Статус |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | Kraken 2 | Genome Biology | [10.1186/s13059-019-1891-0](https://doi.org/10.1186/s13059-019-1891-0) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/) | CC BY 4.0 | machine-translated |
| 2023 | MetaPhlAn 4 | Nature Biotechnology | [10.1038/s41587-023-01688-w](https://doi.org/10.1038/s41587-023-01688-w) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10635831/) | CC BY 4.0 | machine-translated |
| 2024 | Taxometer | Nature Communications | [10.1038/s41467-024-52771-y](https://doi.org/10.1038/s41467-024-52771-y) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11437175/) | CC BY 4.0 | — |
| 2024 | YACHT | Bioinformatics | [10.1093/bioinformatics/btae047](https://doi.org/10.1093/bioinformatics/btae047) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10868342/) | CC BY 4.0 | — |
| 2026 | Perseus | препринт | [PMC13001417](https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/) | CC BY-NC 4.0 | — |
| 2026 | Сравнение Kraken2 vs MetaPhlAn4 | PLOS Computational Biology | [10.1371/journal.pcbi.1013883](https://doi.org/10.1371/journal.pcbi.1013883) | [PLOS](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1013883) | CC BY 4.0 | machine-translated |

Полные оригиналы (PDF/HTML) НЕ копируются в этот репозиторий — каждый перевод ссылается на оригинал из таблицы выше и в своей шапке. Бинарники рисунков и формул из PMC OA могут лежать в `papers/<slug>/assets/` (та же лицензия, что у оригинала; атрибуция в шапке статьи).

В случае любых расхождений оригинал главнее.

## Структура

```
ml-bio-papers/
├── README.md               # этот файл (English)
├── README.ru.md            # русская версия
├── TRANSLATION.md          # правила перевода: что не переводится, формат шапки, стиль
├── glossary/               # один термин = один единый перевод во всех статьях
└── papers/                 # по папке на статью
    └── YYYY-name/
        ├── index.md        # перевод / конспект = будущая страница сайта
        └── meta.yml        # DOI, авторы, журнал, лицензия, статус, Zenodo DOI
```

## Лицензия

- Переводы и конспекты в этом репозитории: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), автор перевода: Leonid Dolgirev.
- Оригинальные статьи сохраняют лицензии издателей (в основном CC BY 4.0; Perseus — CC BY-NC 4.0). DOI и лицензия оригинала указаны в шапке каждого перевода.
- Переводы неофициальные; авторы оригиналов их не проверяли. В случае любых расхождений оригинал главнее.
