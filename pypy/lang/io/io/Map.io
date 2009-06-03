Map do(
    //doc Map with(key1, value1, key2, value2, ...) Returns a new map containing the given keys and values
    with := method(
    	m := Map clone
    	args := call message arguments 
    	for(i, 0, args size - 1, 2,
    		m atPut(call evalArgAt(i), call evalArgAt(i+1))
    	)
    	m
    )

    asJson := method(
    	"{" .. self keys map(k, k asJson .. ":" .. self at(k) asJson) join(",") .. "}"
    )

    //doc Map asList Converts a Map to a list of lists. Each element in the returned list will be a list of two elements: the key, and the value.
    asList := method(
    	self keys map(k, list(k, self at(k)))
    )
 
        //doc Map asObject Create a new Object whose slotDescriptionMap will be equal to self
    	asObject := method(
    		o := Object clone
    		self foreach(k, v, o setSlot(k, getSlot("v")))
            o
    	)
)
