ROOTSYS := ${ROOTSYS}

ifeq ($(ROOTSYS),)
  genreflex=genreflex
  cppflags=
else
  genreflex=$(ROOTSYS)/bin/genreflex
  cppflags=-I$(ROOTSYS)/include -L$(ROOTSYS)/lib
endif

example01Dict.so: example01.cxx
	$(genreflex) example01.cxx
	g++ -o $@ example01_rflx.cpp -shared -lReflex $(cppflags)
