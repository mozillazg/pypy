LD_LIBRARY_PATH := ${LD_LIBRARY_PATH}:${ROOTSYS}/lib
ROOTSYS := ${ROOTSYS}

example01Dict.so: example01.cxx
	echo $(ROOTSYS)
	$(ROOTSYS)/bin/genreflex example01.cxx
	g++ -o $@ example01_rflx.cpp -shared -I$(ROOTSYS)/include -L$(ROOTSYS)/lib -lReflex

