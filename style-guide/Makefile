MAINFILE := thesis-main
ZIPFILE := style-guide

all: pdf
dvi: $(MAINFILE).dvi
pdf: $(MAINFILE).pdf
zip: pdf $(ZIPFILE).zip

$(ZIPFILE).zip: *.pdf *.eps *.tex *.bib *.cls *.sty Makefile
	rm -rf $(ZIPFILE)
	mkdir $(ZIPFILE)
	cp $^ $(ZIPFILE)
	zip -9 -r $@ $(ZIPFILE)/
	rm -rf $(ZIPFILE)

$(MAINFILE).pdf: *.tex *.bib *.cls
	pdflatex $(MAINFILE)
	bibtex $(MAINFILE)
	pdflatex $(MAINFILE)
	pdflatex $(MAINFILE)
	
$(MAINFILE).dvi: *.tex *.bib *.cls
	latex $(MAINFILE)
	bibtex $(MAINFILE)
	latex $(MAINFILE)
	latex $(MAINFILE)

clean:
	- rm -f *~
	- rm -f *.aux *.log
	- rm -f *.bbl *.blg
	- rm -f *.lof *.lot *.toc

veryclean: clean
	- rm -f *.dvi
	- rm -f $(MAINFILE).pdf
	- rm -f $(ZIPFILE).zip