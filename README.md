# ml-bio-papers

Неофициальные русские переводы и конспекты научных статей по ML в биоинформатике (метагеномика, белки, молекулы).

Сайт: https://dlgrv.github.io/ml-bio-papers/ (планируется, GitHub Pages + Quarto)

## Статьи

| Год | Статья | Журнал | Статус перевода |
|---|---|---|---|
| 2019 | Kraken 2 | Genome Biology | — |
| 2023 | MetaPhlAn 4 | Nature Biotechnology | — |
| 2024 | Taxometer | Nature Communications | — |
| 2024 | YACHT | Bioinformatics | — |
| 2026 | Perseus | препринт (PMC) | — |
| 2026 | Kraken2 vs MetaPhlAn4 (сравнение) | PLOS Computational Biology | — |

Статусы: `—` не начат · `MT` машинный перевод · `MT + LLM review` проверен второй моделью · `выверено` вычитано человеком.

## Структура

```
ml-bio-papers/
├── README.md
├── TRANSLATION.md            # глоссарий + правила перевода
├── _quarto.yml               # конфиг сайта (Quarto)
├── .github/workflows/        # Action: render + publish на gh-pages
├── papers/                   # по папке на статью
│   └── YYYY-name/
│       ├── index.qmd         # перевод/конспект = страница сайта
│       └── meta.yml          # DOI, авторы, журнал, лицензия, статус
├── glossary/
└── index.qmd                 # главная сайта: таблица статей
```

## Лицензии

- Оригиналы статей — под лицензиями издателей (в основном CC BY 4.0; Perseus — CC BY-NC 4.0). Ссылка на оригинал и лицензия указываются в шапке каждого перевода.
- Переводы в этом репозитории — CC BY 4.0, автор перевода: Leonid Dolgirev.
- Переводы неофициальные; в случае расхождений оригинал главнее.
