from ctypes import *
import ctypes.util

# Note: OpenSSL on OS X only provides md5 and sha1
libpath = ctypes.util.find_library('ssl')
lib = CDLL(libpath) # Linux, OS X


# FIXME do we really need this anywhere here?
class ENV_MD(Structure):
	# XXX Should there be more to this object?.
	_fields_ = [
		('type', c_int),
		('pkey_type', c_int),
		('md_size', c_int),
	]

class _dummy_env_md(Structure):
	# XXX used for OS X, a bit hairy
	_fields_ = [
		('digest', ENV_MD),
		('two', c_int),
		('three', c_int),
		('four', c_int),
		('five', c_int),
		]

def _new_ENV_MD():
	return _dummy_env_md()

# OpenSSL initialization
lib.OpenSSL_add_all_digests()

def _get_digest(ctx):
	return ctx.digest

# taken from evp.h, max size is 512 bit, 64 chars
lib.EVP_MAX_MD_SIZE = 64

class hash(object):
	"""
	A hash represents the object used to calculate a checksum of a
	string of information.
	
	Methods:
	
	update() -- updates the current digest with an additional string
	digest() -- return the current digest value
	hexdigest() -- return the current digest as a string of hexadecimal digits
	copy() -- return a copy of the current hash object
	
	Attributes:
	
	name -- the hash algorithm being used by this object
	digest_size -- number of bytes in this hashes output
	"""
	def __init__(self, obj, name):
		self.name = name # part of API
		#print 'obj is ', obj
		if isinstance(obj, _dummy_env_md):
			self._obj = obj.digest
		else:
			self._obj = obj  # private
	
	def __repr__(self):
		# format is not the same as in C module
		return "<%s HASH object>" % (self.name)
	
	def copy(self):
		"Return a copy of the hash object."
		ctxnew = _new_ENV_MD()
		lib.EVP_MD_CTX_copy(byref(ctxnew), byref(self._obj))
		return hash(ctxnew, self.name)
	
	def hexdigest(self):
		"Return the digest value as a string of hexadecimal digits."
		dig = self.digest()
		a = []
		for x in dig:
			a.append('%.2x' % ord(x))
		#print '\n--- %r \n' % ''.join(a)
		return ''.join(a)
	
	def digest(self):
		"Return the digest value as a string of binary data."
		tmpctx = self.copy()
		digest_size = tmpctx.digest_size
		dig = create_string_buffer(lib.EVP_MAX_MD_SIZE)
		lib.EVP_DigestFinal(byref(tmpctx._obj), dig, None)
		lib.EVP_MD_CTX_cleanup(byref(tmpctx._obj))
		return dig.raw[:digest_size]
	
	def digest_size(self):
		# XXX This isn't the nicest way, but the EVP_MD_size OpenSSL function
		# XXX is defined as a C macro on OS X and would be significantly 
		# XXX harder to implement in another way.
		# Values are digest sizes in bytes
		return {
			'md5': 16,
			'sha1': 20,
			'sha224': 28,
			'sha256': 32,
			'sha384': 48,
			'sha512': 64,
			}.get(self.name, 0)
	digest_size = property(digest_size, None, None) # PEP 247
	digestsize = digest_size # deprecated, was once defined by sha module
	
	def block_size(self):
		return lib.EVP_MD_CTX_block_size(byref(self._obj))
	block_size = property(block_size, None, None)
	
	def update(self, string):
		"Update this hash object's state with the provided string."
		lib.EVP_DigestUpdate(byref(self._obj), c_char_p(string), c_uint(len(string)))

def new(name, string=''):
	"""
	Return a new hash object using the named algorithm.
	An optional string argument may be provided and will be
	automatically hashed.
	
	The MD5 and SHA1 algorithms are always supported.
	"""
	digest = lib.EVP_get_digestbyname(c_char_p(name))
	
	if not isinstance(name, str):
		raise TypeError("name must be a string")
	if not digest:
		raise ValueError("unknown hash function")
	
	ctx = _new_ENV_MD()
	lib.EVP_DigestInit(pointer(ctx), digest)
	
	h = hash(_get_digest(ctx), name)
	if string:
		if not isinstance(string, str):
			raise ValueError("hash content is not string")
		h.update(string)
	return hash(ctx, name)

# shortcut functions
def openssl_md5(string=''):
	return new('md5', string)

def openssl_sha1(string=''):
	return new('sha1', string)

def openssl_sha224(string=''):
	return new('sha224', string)

def openssl_sha256(string=''):
	return new('sha256', string)

def openssl_sha384(string=''):
	return new('sha384', string)

def openssl_sha512(string=''):
	return new('sha512', string)

