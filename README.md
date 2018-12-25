# Benchmarks for evaluating PDF processing programs.

## Setup

### Python
Install [Anaconda](https://www.anaconda.com/download/#macos) Python 3 distribution.
Install [SpaCy](https://spacy.io/usage/)

### UniDoc
Build [pdf_info](https://github.com/peterwilliams97/unidoc-examples/blob/render/pdf/analysis/pdf_info.go) and [pdf_extract_text](https://github.com/peterwilliams97/unidoc-examples/blob/render/pdf/text/pdf_extract_text.go)

	pushd $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/text/
	go build pdf_extract_text.go
	popd
	cp $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/text/pdf_extract_text .

	pushd $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/analysis/
	go build pdf_info.go
	popd
	cp $GOPATH/src/github.com/unidoc/unidoc-examples/pdf/analysis/pdf_info .


### Reference PDF readers
Install poppler and PdfBox

Check that poppler is running

	pdftotext <some pdf file>


## Running
	python benchmark.py ~/testdata/**/*.pdf ~/testdata/*.pdf > results.txt

This will compare UniDoc to Poppler text extraction over the PDF files in ~/testdata and write the
summary to results.txt.

This is an example (results.txt).
