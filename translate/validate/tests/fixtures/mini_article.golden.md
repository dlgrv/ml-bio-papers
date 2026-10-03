# Improved metagenomic analysis with Kraken 2

## Abstract

Although Kraken’s *k*-mer-based approach provides a fast taxonomic classification of metagenomic sequence data, its large memory requirements can be limiting for some applications. Kraken 2 improves upon Kraken 1 by reducing memory usage by 85%, while maintaining high accuracy and increasing speed fivefold.

## Background

Taxonomic classifiers assign a lowest common ancestor (LCA) to each read [1–3]. The default values are ℓ = 31 and *k* = 35 (see the “Methods” section for full details). It uses 10.6 GB of memory (Fig. 1a, Additional file 1: Table S1).

![Fig. 1](assets/13059_2019_1891_Fig1_HTML.jpg)

**Fig. 1.** Differences in operation between the two versions of Kraken. **a** Both versions begin classifying a *k*-mer.

## Methods

The code is available at [https://github.com/DerrickWood/kraken2](https://github.com/DerrickWood/kraken2). We did not find a significant difference (*p* < 0.05); the error was 1.5 × 10<sup>−3</sup>, with n<sub>*x*</sub> = 1000 reads.

We calculated the mean absolute percentage error (MAPE):

$$\mathrm{MAPE}=\frac{100\%}{n}\sum \limits_{x=1}^n\left|\frac{T_x-{S}_x}{T_x}\right|$$

where *T* is the true value.

Additional data are listed below.

**Additional file 1:** **Table S1.** Comparison of accuracy and computational performance.

## Acknowledgements

The authors would like to thank James R. White for the helpful discussions.

## References

1. Kim D, Song L. Centrifuge: rapid and sensitive classification of metagenomic sequences. Genome Res. 2016;26:1721–1729. doi:10.1101/gr.210641.116
2. Langmead B, Wilks C. Scaling read aligners to hundreds of threads on general-purpose processors. Bioinformatics. 2018;35(3):421–32. doi:10.1093/bioinformatics/bty648
