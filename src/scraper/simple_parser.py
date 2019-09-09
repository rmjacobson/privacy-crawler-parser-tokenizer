#!/usr/bin/python3

# Privacy Policy Project
# HTML Text Parser
# Takes in HTML file, splits all text from paragraphs (<p>), headers (<hX>),
# lists (<ul> and <ol>), and links (<a>), and dumps each into separate files.
# Does not preserve document structure, just splits component parts.

from bs4 import BeautifulSoup, Comment, NavigableString, CData, Tag, ProcessingInstruction
import sys, datetime, re, nltk


class Parser():
	html_file = ""			# input html file
	timestamp = ""			# time splitting started
	outfile_paragraphs = ""	# outfile containing paragraphs
	outfile_headers = ""	# outfile containing headers
	outfile_lists = ""		# outfile containing bulleted/numbered lists
	outfile_links = ""		# outfile containing every link in document, numbered

	invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
	skipped_tags = ["header", "footer", "nav"]

	pattern_header = re.compile("h\d")
	pattern_list = re.compile("[u|o]l")

	def __init__(self, argv):
		super(Parser, self).__init__()

		try:
			self.html_file = argv[1]
		except Exception as e:
			print("Usage: simple_parser.py <inputfile>")
			sys.exit(2)

		with open(self.html_file, "r") as f:
			contents = f.read()
	
		self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
		self.soup = BeautifulSoup(contents, 'html.parser')
		self.outfile_paragraphs = self.html_file[:-5] + self.timestamp + '_paragraphs.txt'
		self.outfile_headers = self.html_file[:-5] + self.timestamp + '_headers.txt'
		self.outfile_lists = self.html_file[:-5] + self.timestamp + '_lists.txt'
		self.outfile_links = self.html_file[:-5] + self.timestamp + '_links.txt'


# https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
def skip_tag(element):
	if element.name in parser.invisible_tags:
		return True
	if element.name in parser.skipped_tags:
		return True
	if isinstance(element, Comment):
		return True
	return False


# https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
# does DFS on bs4 tree searching for text to process
def walk_tree(soup):
	for element in soup.find_all(recursive=False):
		name = getattr(element, "name", None)

		if skip_tag(element):
			print("skipping <" + name + "> tag" )
			continue

		if name == "p":
			print("PUT PARAGRAPH IN DUMP FILE " + parser.outfile_paragraphs)
			with open(parser.outfile_paragraphs, "a") as f:
				f.write(element.get_text() + "\n")
		elif parser.pattern_header.match(name):
			print("PUT HEADER IN DUMP FILE " + parser.outfile_headers)
			with open(parser.outfile_headers, "a") as f:
				f.write(element.get_text() + "\n")
		elif parser.pattern_list.match(name):
			print("PUT LIST IN DUMP FILE " + parser.outfile_lists)
			with open(parser.outfile_lists, "a") as f:
				f.write(element.get_text()) 
		elif name == "a":
			print("PUT LINK IN DUMP FILE " + parser.outfile_links)
			with open(parser.outfile_links, "a") as f:
				f.write(element.get_text() + "\n")

		walk_tree(element)


if __name__ == '__main__':
	parser = Parser(sys.argv)
	walk_tree(parser.soup)
