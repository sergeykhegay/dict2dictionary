#! /bin/python
import io

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
			if line == "": continue

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

	# this is done in case if someone reimplements parse method
	_parse = parse
	_valid = valid


class DataParser(object):
	pass

class IndexParser(object):
	"""IdxParser"""

	def __init__(self, info, idx_filename):
		super(IdxParser, self).__init__()
		self.info = info
		self.filename = idx_filename


	class ByteStreamReader(object):
		"""docstring for UnicodeReader"""

		def __init__(self, filename) :
			self.filename = filename
			self.file = open(filename, "rb")

		def __del__(self):
			if self.file:
				self.file.close()

		def count_leading_ones(self, byte):
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
			return result

		def read_n_bytes(self, n=1)
			byte_array = b''
			for i in range(4):
				byte_array += self.read_byte()
			return byte_array

		def read_unicode_literal(self):
			byte = self.read_byte()				
			byte_array = byte
			num_of_ones = self.count_leading_ones(byte)

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

			for i in range(num_of_ones):
				print(byte)
				byte = self.read_byte()
				byte_array += byte

			return byte_array.decode(encoding="utf-8")

		def read_unicode_string(self, delimeter=u'\n'):
			result = u''
			while True:
				literal = self.read_unicode_literal()
				if literal and literal != delimeter:
					result += literal
				else:
					break

			return result

		def read_int32(self):
			# TODO:
			# I'm hesitant about how bytes are converted to integer value
			# If the first byte in the array begins with 1, does it mean 
			# that the result is going to be negative?
			# So I just added a leading zero byte here. Just in case.
			# I should hack this later.
			byte_array = b'0' + self.read_n_bytes(n=4)
			return int.from_bytes(byte_array, byteorder="big")

		def read_int64(self):
			byte_array = b'0' + self.read_n_bytes(n=8)
			return int.from_bytes(byte_array, byteorder="big")
			




info = InfoParser("./dictionaries/RuKrRu.ifo").get_info

reader = IndexParser.ByteStreamReader("./hello.txt")
print(reader.read_unicode_string(delimeter=u'\0'))
# print(info.version)
# print(info.wordcount)
