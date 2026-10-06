<div align="center">

# ml-papers

Unofficial translations and structured summaries of scientific ML papers — metagenomics, NLP, agents, and related areas.

Every translation states its original source (DOI), the license it is made under, and its review status: machine translation, machine translation + LLM review, or human-verified.

![Papers](https://img.shields.io/badge/Papers-7-3451b2?style=flat-square)
![License of translations](https://img.shields.io/badge/Translations-CC%20BY%204.0-18794e?style=flat-square)
![Originals](https://img.shields.io/badge/Originals-Open%20access-915930?style=flat-square)

**[Paper index](#papers)** | [Translation conventions](TRANSLATION.md) | [Glossary](glossary/README.md)

</div>

## Languages

| Language | README |
| --- | --- |
| 🇬🇧 English | [README.md](README.md) |
| 🇷🇺 Русский | [README.ru.md](README.ru.md) |

---

## Papers

| Year | Paper | Journal | Original (DOI) | Full text | License | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2019 | BERT | NAACL-HLT | [10.18653/v1/N19-1423](https://doi.org/10.18653/v1/N19-1423) | [arXiv](https://arxiv.org/abs/1810.04805) | CC BY 4.0 | machine-translated |
| 2019 | Kraken 2 | Genome Biology | [10.1186/s13059-019-1891-0](https://doi.org/10.1186/s13059-019-1891-0) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/) | CC BY 4.0 | machine-translated |
| 2023 | MetaPhlAn 4 | Nature Biotechnology | [10.1038/s41587-023-01688-w](https://doi.org/10.1038/s41587-023-01688-w) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10635831/) | CC BY 4.0 | machine-translated |
| 2024 | Taxometer | Nature Communications | [10.1038/s41467-024-52771-y](https://doi.org/10.1038/s41467-024-52771-y) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11437175/) | CC BY 4.0 | machine-translated |
| 2024 | YACHT | Bioinformatics | [10.1093/bioinformatics/btae047](https://doi.org/10.1093/bioinformatics/btae047) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10868342/) | CC BY 4.0 | machine-translated |
| 2026 | Perseus | preprint | [PMC13001417](https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/) | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13001417/) | CC BY-NC 4.0 | machine-translated |
| 2026 | Kraken2 vs MetaPhlAn4 comparison | PLOS Computational Biology | [10.1371/journal.pcbi.1013883](https://doi.org/10.1371/journal.pcbi.1013883) | [PLOS](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1013883) | CC BY 4.0 | machine-translated |

Full PDF/HTML originals are NOT copied into this repository — each translation links the original above and in its header. Open-access figure and formula binaries from PMC may be stored under `papers/<slug>/assets/` (same license as the original, attributed in the paper header).

In case of any discrepancy, the original prevails.

## Structure

```
ml-papers/
├── README.md               # this file
├── README.ru.md            # Russian version
├── TRANSLATION.md          # translation conventions: what stays byte-identical, header format, style
├── topics.yml              # allowlist for meta.yml → topics
├── glossary/               # one term = one consistent translation across all papers
└── papers/                 # one folder per paper
    └── YYYY-name/
        ├── index.md        # translation / summary = future site page
        └── meta.yml        # DOI, authors, journal, license, status, topics, Zenodo DOI
```

`meta.yml` must include a non-empty `topics` list. Every entry must appear in [`topics.yml`](topics.yml) (any count from the allowlist). `make lint` rejects unknown or missing topics.

## License

- Translations and summaries in this repository: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), translation author: Leonid Dolgirev.
- Original papers keep their publishers' licenses (mostly CC BY 4.0; Perseus is CC BY-NC 4.0). The original's DOI and license are stated in every translation header.
- Translations are unofficial; the original authors have not reviewed them. In case of any discrepancy, the original prevails.
