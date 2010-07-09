ROOTSYS := ${ROOTSYS}

ifeq ($(ROOTSYS),)
  genreflex=genreflex
  cppflags=
else
  genreflex=$(ROOTSYS)/bin/genreflex
  cppflags=-I$(ROOTSYS)/include -L$(ROOTSYS)/lib
endif

ifeq ($(shell $(genreflex) --help | grep -- --with-methptrgetter),)
  genreflexflags=
  cppflags2=
else
  genreflexflags=--with-methptrgetter
  cppflags2=-Wno-pmf-conversions
endif

example01Dict.so: example01.cxx example01.h
	$(genreflex) example01.h $(genreflexflags)
	g++ -o $@ example01_rflx.cpp example01.cxx -shared -lReflex $(cppflags) $(cppflags2)
