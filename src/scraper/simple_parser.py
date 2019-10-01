#!/usr/bin/python3

"""
Privacy Policy Project
Simple HTML Parser
Takes in HTML file, splits all text from paragraphs (<p>), headers (<hX>),
lists (<ul> and <ol>), and links (<a>), and dumps each into separate files.
Does not preserve document structure, just splits component parts.
"""

from bs4 import BeautifulSoup, Comment, NavigableString, CData, Tag, ProcessingInstruction
import sys, os, datetime, re, nltk
from nltk.tokenize import sent_tokenize


class SimpleParser:
    """ Strip readable/visible text from HTML document. """

    invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
    skipped_tags = ["header", "footer", "nav"]

    pattern_header = re.compile("h\d")
    pattern_list = re.compile("[u|o]l")

    def __init__(self, dataset_html, dataset_text, files):
        """ Specify the files parsed and compare with text equivalents.
        
        Param:  dataset_html - string to path of the HTML dataset
                dataset_text - string to path of the text dataset
                files - actual list of files to parse
        Return: n/a
        """
        super(SimpleParser, self).__init__()

        self.dataset_html = dataset_html
        self.dataset_text = dataset_text
        self.files = files
    
        self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())

    def skip_tag(self, element):
        """ Check if given tag is relevant to the parser.
        https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
        
        Param:  element - bs4 tag
        Return: Boolean: True if tag is irrelevant, False if tag is relevant
        """
        if element.name in self.invisible_tags:
            return True
        if element.name in self.skipped_tags:
            return True
        if isinstance(element, Comment):
            return True
        if isinstance(element, NavigableString):
            return True
        return False

    def walk_tree(self, soup):
        """ DFS walk of bs4 html tree.  Only looks at specific tags, works on
        theory that only these tags will contain important/visible text.
        https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
        
        Param:  soup - bs4 instance of the html parser
        Return: n/a
        """
        for element in soup.find_all(recursive=False):
            name = getattr(element, "name", None)

            if self.skip_tag(element):
                # print("skipping <" + name + "> tag" )
                # with open(self.outfile_ignored, "a") as f:
                #     f.write(element.get_text(strip=True) + "\n")
                continue

            text = ""

            if name == "p":
                # print("PUT PARAGRAPH IN DUMP FILE " + self.outfile_paragraphs)
                text = element.get_text(strip=True) + "\n"
                with open(self.outfile_paragraphs, "a") as f:
                    f.write(element.get_text(strip=True) + "\n")
            elif self.pattern_header.match(name):
                # print("PUT HEADER IN DUMP FILE " + self.outfile_headers)
                text = element.get_text(strip=True) + "\n"
                with open(self.outfile_headers, "a") as f:
                    f.write(element.get_text(strip=True) + "\n")
            elif self.pattern_list.match(name):
                # print("PUT LIST IN DUMP FILE " + self.outfile_lists)
                for descendant in element.children:
                    if self.skip_tag(descendant):
                        continue
                    with open(self.outfile_lists, "a") as f:
                        f.write(descendant.get_text(strip=True) + "\n")
                    text = text + descendant.get_text(strip=True) + "\n"
                with open(self.outfile_lists, "a") as f:
                    f.write("\n")
                text = text + "\n"

            # elif name == "a":
                # print("PUT LINK IN DUMP FILE " + self.outfile_links)
            #     with open(self.outfile_links, "a") as f:
            #         f.write(element.get_text(strip=True) + "\n")

            with open(self.outfile_sequential, "a") as f:
                f.write(text)

            self.walk_tree(element)

    def remove_text(self, txt_contents, fname):
        """ Remove text from txt_contents based on lines from specific
        output file.
        
        Param:  txt_contents - string representation of stripped text
                fname - filename the stripped text comes from
        Return: txt_contents - updated string representation of 
                               stripped text
        """
        with open(fname, "r") as fp:
            line = fp.readline()
            while line:
                txt_contents = txt_contents.replace(line.strip(), "", 1)
                line = fp.readline()
        return txt_contents

    def compare_parsed_text(self, txt_contents, fname):
        """ Search contents of stripped text for each line from each
        file of the output, then write the remainder to last output
        file.  Enables human to check effectiveness of simple parser.

        Param:  txt_contents - string representation of stripped text
                fname - filename the stripped text comes from
        Return: n/a
        """
        txt_contents = self.remove_text(txt_contents, self.outfile_sequential)
        # txt_contents = self.remove_text(txt_contents, self.outfile_ignored)
        # txt_contents = self.remove_text(txt_contents, self.outfile_lists)
        # txt_contents = self.remove_text(txt_contents, self.outfile_paragraphs)
        # txt_contents = self.remove_text(txt_contents, self.outfile_headers)

        remaining_sentences = sent_tokenize(txt_contents)
        with open(self.outfile_compare, "a") as f:
            f.write(str(remaining_sentences))
        return remaining_sentences


    def run(self):
        """ Run the SimpleParser.

        Param:  n/a
        Return: n/a
        """
        for fname in self.files:
            with open(self.dataset_html + fname + ".html", "r") as fp:
                html_contents = fp.read()

            soup = BeautifulSoup(html_contents, 'html.parser')
        
            self.outfile_sequential = output_folder + fname + self.timestamp + '_sequential.txt'
            self.outfile_ignored = output_folder + fname + self.timestamp + '_ignored.txt'
            self.outfile_paragraphs = output_folder + fname + self.timestamp + '_paragraphs.txt'
            self.outfile_headers = output_folder + fname + self.timestamp + '_headers.txt'
            self.outfile_lists = output_folder + fname + self.timestamp + '_lists.txt'
            self.outfile_links = output_folder + fname + self.timestamp + '_links.txt'
            self.outfile_compare = output_folder + fname + self.timestamp + '_compare.txt'

            self.walk_tree(soup)

            with open(self.dataset_text + fname + ".txt", "r") as fp:
                txt_contents = fp.read()

            remaining_sentences = self.compare_parsed_text(txt_contents, fname)
            print(fname + " has " + str(len(remaining_sentences)) + " left.")


if __name__ == '__main__':
    dataset_html = "../../data/policies/html/"
    dataset_text = "../../data/policies/text_test/"
    output_folder = "output/"
    # files = ["google_1", "google_2", "ebay_1", "amazon_1",
    #          "facebook_1", "facebook_2", "netflix_1",
    #          "netflix_2", "twitter_1", "wikipedia_1", "yahoo_1",
    #          "yahoo_2"]
    files = ["google_1","ebay_1","amazon_1",
             "facebook_1", "netflix_1", "twitter_1",
             "wikipedia_1", "yahoo_1", "redbubble_1",
             "blizzard_1", "instagram_1", "stackoverflow_1",
             "steelers_1", "studentuniverse_1"]
    parser = SimpleParser(dataset_html, dataset_text, files)
    parser.run()
