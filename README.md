<div align="center">

# ml-bio-papers

Unofficial Russian translations and structured summaries of scientific papers on machine learning in biology — metagenomics, proteins, molecules.

Every translation states its original source (DOI), the license it is made under, and its review status: machine translation, machine translation + LLM review, or human-verified.

![Papers](https://img.shields.io/badge/Papers-6-3451b2?style=flat-square)
![License of translations](https://img.shields.io/badge/Translations-CC%20BY%204.0-18794e?style=flat-square)
![Originals](https://img.shields.io/badge/Originals-Open%20access-915930?style=flat-square)

**[Paper index](#papers)** | [Translation conventions](TRANSLATION.md) | [Glossary](glossary/README.md) | [About the statuses](#translation-statuses)

</div>

| Language | README |
| --- | --- |
| 🇬🇧 English | [README.md](README.md) |
| 🇷🇺 Русский | [README.ru.md](README.ru.md) |

---

## Papers

| Year | Paper | Journal | Translation status |
| --- | --- | --- | --- |
| 2019 | Kraken 2 | Genome Biology | — |
| 2023 | MetaPhlAn 4 | Nature Biotechnology | — |
| 2024 | Taxometer | Nature Communications | — |
| 2024 | YACHT | Bioinformatics | — |
| 2026 | Perseus | preprint (PMC) | — |
| 2026 | Kraken2 vs MetaPhlAn4 comparison | PLOS Computational Biology | — |

Originals are NOT copied into this repository. Each paper folder links the original (DOI) and states the original's license.

## Translation statuses

| Status | Meaning |
| --- | --- |
| `—` | not started |
| `MT` | machine translation, unchecked |
| `MT + LLM review` | machine translation verified by a second model (numbers, links, terminology) |
| `verified` | additionally proofread by a human |

In case of any discrepancy, the original prevails.

## Structure

```
ml-bio-papers/
├── README.md               # this file
├── README.ru.md            # Russian version
├── TRANSLATION.md          # translation conventions: what stays byte-identical, header format, style
├── glossary/               # one term = one Russian translation across all papers
└── papers/                 # one folder per paper
    └── YYYY-name/
        ├── index.md        # translation / summary = future site page
        └── meta.yml        # DOI, authors, journal, license, status, Zenodo DOI
```

## License

- Translations and summaries in this repository: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), translation author: Leonid Dolgirev.
- Original papers keep their publishers' licenses (mostly CC BY 4.0; Perseus is CC BY-NC 4.0). The original's DOI and license are stated in every translation header.
- Translations are unofficial; the original authors have not reviewed them. In case of any discrepancy, the original prevails.
