# Benchmarks for evaluating PDF processing programs.

## Setup

### Python
Install [Anaconda](https://www.anaconda.com/download/#macos) Python 3 distribution.
Install [SpaCy](https://spacy.io/usage/)

### UniDoc
Build [pdf_info](https://github.com/peterwilliams97/unidoc-examples/blob/benchmark/pdf/analysis/pdf_info.go) and [pdf_extract_text](https://github.com/peterwilliams97/unidoc-examples/blob/benchmark/pdf/text/pdf_extract_text.go)

(This branch has test programs modified to work with this script.)

	pushd $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/text/
	go build pdf_to_text.go
	popd
	cp $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/text/pdf_to_text .

	pushd $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/analysis/
	go build pdf_info.go
	popd
	cp $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/analysis/pdf_info .


### Reference PDF readers
Install Poppler, mupdf, PdfBox, etc

#### mupdf on Mac
brew install mupdf-tools

### Check all PDF text converters

Check that these tools are running

	./pdf_info test.pdf

	./pdf_to_text test.pdf

	mutool draw -F txt test.pdf

	pdftotext test.pdf


## Running
	python benchmark.py ~/testdata/**/*.pdf ~/testdata/*.pdf > results.txt

This will compare UniDoc to Poppler text extraction over the PDF files in ~/testdata and write the
summary to results.txt.

This is an example [results.txt](results.txt).

## Interpretation.

A line from [results.txt](results.txt) is

	801 0.085 0.114 0.148: 01767-0240c6.txt [1.3] 0.712 MB 2 pages ~/testdata/Wild_comes_the_molten_ore.pdf

* This is the 802nd (801 with zero-offset) successful comparison.
* It was run on `~/testdata/Wild_comes_the_molten_ore.pdf` which ois `PDF version 1.3`, `0.712 MBytes` and has `2 pages`.
* The [Jaccard distance](https://en.wikipedia.org/wiki/Jaccard_index) between the UniDoc and Poppler text extractions are `0.085`, `0.114` and `0.148` for `unigrams`, `bigrams` and `trigrams` respectively, which is a fairly good, but not great match.

## Using Results
If you can assume that one of the PDF text extractors works well then you go to the PDF files that give the most different text extraction, the ones at the bottom of the results, and work on them.

