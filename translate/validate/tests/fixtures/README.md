# Test fixtures

`mini_article.xml` is a hand-built reduction of PMC6883579 (Wood, Lu, Langmead, "Improved metagenomic
analysis with Kraken 2", Genome Biology 20:257, 2019, DOI 10.1186/s13059-019-1891-0), licensed
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Several sentences are taken from the
article, others are composed for tests; the markup is the real PMC markup. It covers what the
parser must handle: all xref types (bibr group, fig, media, sec), a figure nested inside a
paragraph, a formula with TeX and MathML alternatives, an external link, sub/sup, a
supplementary-material block, an acknowledgement and two references (element- and
mixed-citation).
