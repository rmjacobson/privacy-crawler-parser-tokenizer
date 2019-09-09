#!/usr/bin/python3

# Privacy Policy Project
# HTML Parser
# Tries to preserve document structure while still allowing for easier sentence tokenization.
# https://www.digitalocean.com/community/tutorials/how-to-work-with-web-data-using-requests-and-beautiful-soup-with-python-3
# https://www.digitalocean.com/community/tutorials/how-to-scrape-web-pages-with-beautiful-soup-and-python-3

from bs4 import BeautifulSoup, Comment, NavigableString, CData, Tag, ProcessingInstruction
import sys, datetime, re, nltk

class Parser():
	html_file = ""			# input html file
	timestamp = ""			# time segmentation started
	outfile_all = ""		# outfile containing text able to be sentence-tokenized
	outfile_list = ""		# outfile containing bulleted/numbered lists
	outfile_link = ""		# outfile containing every link in document, numbered

	invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
	skipped_tags = ["header", "footer", "nav", "a"]
	
	link_num = 0			# counter for links encountered in policy
	list_num = 0			# counter for lists encountered in policy

	pattern_h_or_p = re.compile("(p)|(h\d)")
	pattern_list = re.compile("[u|o]l")

	def __init__(self, argv):
		super(Parser, self).__init__()

		try:
			self.html_file = argv[1]
		except Exception as e:
			print("Usage: structural_parser.py <inputfile>")
			sys.exit(2)

		with open(self.html_file, "r") as f:
			contents = f.read()
	
		self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
		self.soup = BeautifulSoup(contents, 'html.parser')
		self.outfile_all = self.html_file[:-5] + self.timestamp + '.txt'
		self.outfile_list = self.html_file[:-5] + self.timestamp + '_list.txt'
		self.outfile_link = self.html_file[:-5] + self.timestamp + '_link.txt'


# https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
def skip_tag(element):
	if element.name in parser.invisible_tags:
		return True
	if element.name in parser.skipped_tags:
		return True
	if isinstance(element, Comment):
		return True
	return False


# taken from BeautifulSoup4 source: element.py:950 as of 9/3/2019
# Get all child strings, concatenated using the given separator.
# edited to include pieces from _all_strings (element.py:925), but also to
# replace links with [LINK] tags to identify them later.
def get_text(element, separator="", types=(NavigableString, CData, Tag)):		
		text = []

		for descendant in element.children:
			if ((types is None and not isinstance(descendant, NavigableString))
				or
				(types is not None and type(descendant) not in types)):
				continue
			if descendant.name == "a":
				descendant_text = str(descendant)
				parser.link_num = parser.link_num + 1
				with open(parser.outfile_link, "a") as f:
					f.write("[LINK" + str(parser.link_num) + "]: " + descendant_text + "\n")
				text.append(descendant_text.replace(descendant_text, 
							"[LINK" + str(parser.link_num) + "]" + descendant.string))
			elif descendant.name == "li":
				text.append(get_text(descendant))
			else:
				text.append(str(descendant))

		return separator.join(text)


# https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
# does DFS on bs4 tree searching for text to process
def walk_tree(soup):
	for element in soup.find_all(recursive=False):
		name = getattr(element, "name", None)

		if skip_tag(element):
			print("skipping <" + name + "> tag" )
			element.decompose()
			continue

		# deal with lists by dumping them in list file
		# links are processed along with other links in the files
		# no support for nested lists
		if parser.pattern_list.match(name):
			parser.list_num = parser.list_num + 1
			print("PUT LIST" + str(parser.list_num) + " IN DUMP FILE " + parser.outfile_list)
			with open(parser.outfile_list, "a") as f:
				f.write("[LIST" + str(parser.list_num) + "]:" + get_text(element))
			with open(parser.outfile_all, "a") as f:
				f.write("[LIST" + str(parser.list_num) + "]\n")
			element.decompose()
		elif parser.pattern_h_or_p.match(name):
			with open(parser.outfile_all, "a") as f:
				f.write(get_text(element) + "\n")

		walk_tree(element)


if __name__ == '__main__':
	parser = Parser(sys.argv)
	walk_tree(parser.soup)
