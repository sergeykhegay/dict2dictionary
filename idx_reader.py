#! python3
import io
# import logging

# logging.basicConfig(level=logging.DEBUG, 
# 					format='%(asctime)s - %(levelname)s - %(message)s')


class InputError(Exception):
	"""docstring for InputError"""
	pass	

class Entry(object):
	def __init__(self, string=None, offset=None, size=None):
		self.word_str = None
		self.word_offset = 0
		self.word_size = 0

	def __repr__(self):
		return self.word_str


class ByteStream(object):
	"""A simple wrapper for bytes"""
	def __init__(self, bytes):
		super(ByteStream, self).__init__()
		self.bytes = bytes
		
		assert(type(bytes)==type(b''), "Must be initialized by bytes")

	def readall():
		result = self.bytes[:]
		self.bytes = b''
		return result[:]

	def read(n=-1):
		result = b''
		if n == -1:
			result = self.readall()
		else:
			result = self.bytes[:n]
			self.bytes = self.bytes[n:]

		return result

		

class ByteStreamReader(object):
	"""docstring for UnicodeReader"""

	class EOFError(Exception):
		pass
			

	def __init__(self, filename) :
		self.filename = filename
		self.file = open(filename, "rb")
		self.EOF = False

	def __del__(self):
		if self.file:
			self.file.close()

	def _count_leading_ones(self, byte):
		result = 0
		number = int.from_bytes(byte, byteorder='big')
		for i in range(8):
			if (number >> (7 - i)) & 1:
				result += 1
			else:
				break
		return result

	def read_byte(self):
		result = self.file.read(1)

		if result == b'':
			self.EOF = True
		return result
	
	def read_n_bytes(self, n=1):
		byte_array = b''
		for i in range(4):
			byte_array += self.read_byte()
		return byte_array

	def read_unicode_literal(self, count=[0]):
		"""Reads a utf-8 literal from stream.

		count variable is set to the number of bytes read
		"""
		byte = self.read_byte()				
		byte_array = byte
		num_of_ones = self._count_leading_ones(byte)

		# This is done due to utf-8 specification.
		# A literal can be consisted from up to 4 bytes.
		# The number of bytes is encoded in the first byte.
		# That is:
		# 0xxxxxxx - 1 byte
		# 110xxxxx - 2 bytes
		# 1110xxxx - 3 bytes
		# 11110xxx - 4 bytes
		if num_of_ones != 0:
			num_of_ones -= 1
		assert num_of_ones in [0, 1, 2, 3], "Not a unicode literal?"

		for i in range(num_of_ones):
			byte = self.read_byte()
			byte_array += byte

		count[0] = len(byte_array)
		return byte_array.decode(encoding="utf-8")

	def read_unicode_string(self, delimeter=u'\n', count=[0]):
		result = u''

		count = [0]
		while True:
			count_tmp = [0]
			literal = self.read_unicode_literal(count=count_tmp)
			count[0] += count_tmp[0]
			if literal and literal != delimeter:
				result += literal
			else:
				break

		return result

	def read_int32(self, count=[0]):
		# TODO:
		# I'm hesitant about how bytes are converted to integer value
		# If the first byte in the array begins with 1, does it mean 
		# that the result is going to be negative?
		# So I just added a leading zero byte here. Just in case.
		# I should hack this later.
		#
		# Update: I found signed parameter.
		if self.EOF:
			return None

		byte_array = self.read_n_bytes(n=4)
		count[0] = len(byte_array)
		return int.from_bytes(b'\0' + byte_array, byteorder="big", signed=False)

	def read_int64(self, count=[0]):
		# I should fix this
		if self.EOF:
			return None

		byte_array = self.read_n_bytes(n=8)
		count[0] = len(byte_array)
		return int.from_bytes(b'\0' + byte_array, byteorder="big", signed=False)


class InfoParser(object):
	"""Parses .ifo file"""

	NUM_OPTS = ["wordcount", "synwordcount", "idxoffsetbits", "idxfilesize"]
	TEXT_OPTS = ["bookname", "author", "email", "website", 
				"description", "date", "sametypesequence", "version"]
	OPTIONS = NUM_OPTS + TEXT_OPTS

	def __init__(self, filename):
		# super(IdxParser, self).__init__()
		
		self.filename = filename

		self.version = None
		self.bookname = None			# required
		self.wordcount = None			# required
		self.synwordcount = None		# required if ".syn" file exists.
		self.idxfilesize = None       	# required
		self.idxoffsetbits = None     	# New in 3.0.0
		self.author = None
		self.email = None
		self.website = None
		self.description = None			# use <br> for new line.
		self.date = None
		self.sametypesequence = None	# very important.

		self._parse()

		if self._valid() != True:
			raise InputError("Wrong data! Required options are missing")

	def parse(self):
		fin = open(self.filename, "r")

		# check the file has a standard header
		header = fin.readline().strip()
		if header != "StarDict's dict ifo file":
			raise InputError("Wrong .ifo file format")

		for line in fin:
			line = line.strip()
			if line == "": 
				continue

			try:			
				option, option_body = line.split("=", maxsplit=1)
			except ValueError(e):
				raise InputError("Wrong .ifo file format. Bad option.")

			if option not in self.OPTIONS:
				raise InputError("No such option: {0}".format(option))

			if option in self.NUM_OPTS:
				option_body = int(option_body)
			setattr(self, option, option_body)

		fin.close()
	
	def valid(self):
		return (self.bookname != None and
			 	self.wordcount != None and
			 self.idxfilesize != None and
			self.sametypesequence != None)

	def get_info(self):
		result = {}
		for option in self.OPTIONS:
			value = getattr(self, option)
			if value != None: 
				result[option] = value
		return result	

	# this is done in case if someone reimplements parse method
	_parse = parse
	_valid = valid


class IndexParser(object):
	"""IdxParser"""

	def __init__(self, info, idx_filename):
		super(IndexParser, self).__init__()
		self.info = info
		self.filename = idx_filename
		self.byte_reader = ByteStreamReader(idx_filename)
		self.index = []
		self._parse()

	def _read_word_string(self):
		return self.byte_reader.read_unicode_string(delimeter=u'\0')

	def _read_data_offset(self):
		result = 0
		if "idxoffsetbits" in self.info and self.info["idxoffsetbits"] == 64:
			result = self.byte_reader.read_int64()
		else:
			result = self.byte_reader.read_int32()
		return result

	def _read_data_size(self):
		return self.byte_reader.read_int32()

	def parse(self):
		while not self.byte_reader.EOF:
			word_str = self._read_word_string()
			data_offset = self._read_data_offset()
			data_size = self._read_data_size()

			if data_size != None:
				self.index.append( (word_str, data_offset, data_size) )
			else:
				break
		
	def get_index(self):
		return self.index[:]

	_parse = parse


class DataParser(object):
	def __init__(self, info):
		super(DataParser, self).__init__()
		self.info = info
	
	
			
info = InfoParser("./dictionaries/RuKrRu.ifo").get_info()
print(info)
# reader = ByteStreamReader("./hello.txt")
# print(reader.read_unicode_string(delimeter=u'\0'))
# print(reader.read_int32())
# print(reader.read_int32())
# print(reader.read_int32())
# print(reader.read_unicode_string())
index = IndexParser(info, "./dictionaries/RuKrRu.idx").get_index()

count = 0
for i in index:
	print("{0:8}   {1:8}   {2}".format(i[1], i[2], i[0]))
	count += 1
	if count == 20:
		break
# print(info.version)
# print(info.wordcount)
