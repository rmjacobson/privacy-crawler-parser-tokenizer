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


class SequentialElement:
    def __init__(self, content_string, tag_type, index):  
        self.content_string = content_string
        self.tag_type = tag_type
        self.index = index


class SimpleParser:
    """ Strip readable/visible text from HTML document. """

    invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
    skipped_tags = ["header", "footer", "nav"]

    pattern_header = re.compile("h\d")
    pattern_list = re.compile("[u|o]l")

    filler_sentences = "This is a sentence. This is a sentence. This is a sentence. This is a sentence. This is a sentence. This is a sentence."

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
        self.failed = 0
        self.sequential_list = []
        self.paragraph_list = []
        self.header_list = []
        self.list_list = []

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

    def is_only_links(self, element):
        ret = True
        children = element.findChildren(recursive=False)
        for child in children:
            name = getattr(child, "name", None)
            if name != "a":
                ret = False
        return ret

    def output_list_to_file(self, l, output_file):
        out_string = ""
        for i in l:
            if i < 1:
                element = '<' + self.sequential_list[i].tag_type + ", preceded by None, proceeded by " + self.sequential_list[i+1].tag_type + '>\n'
            elif i > (len(self.sequential_list) - 2):
                element = '<' + self.sequential_list[i].tag_type + ", preceded by " + self.sequential_list[i-1].tag_type + ", proceeded by None>\n"
            else:
                element = '<' + self.sequential_list[i].tag_type + ", preceded by " + self.sequential_list[i-1].tag_type + ", proceeded by " + self.sequential_list[i+1].tag_type + '>\n'
            out_string = out_string + element + self.sequential_list[i].content_string + "\n"
        with open(output_file, "a") as f:
            f.write(out_string)

    def walk_tree(self, soup):
        """ DFS walk of bs4 html tree.  Only looks at specific tags, works on
        theory that only these tags will contain important/visible text.
        https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
        
        Param:  soup - bs4 instance of the html parser
        Return: n/a
        """

        paragraph_index = 0
        header_index = 0
        list_index = 0

        for element in soup.find_all(recursive=False):
            name = getattr(element, "name", None)

            if self.skip_tag(element):
                # print("skipping <" + name + "> tag" )
                # with open(self.outfile_ignored, "a") as f:
                #     f.write(element.get_text(strip=True) + "\n")
                continue

            text = ""

            if name == "p":
                text = element.get_text().strip() + "\n"
                self.paragraph_list.append(len(self.sequential_list))
                self.sequential_list.append(SequentialElement(text, "p" + str(len(self.paragraph_list) - 1), paragraph_index))
                paragraph_index = paragraph_index + 1
            elif self.pattern_header.match(name):
                text = element.get_text() + "\n"
                self.header_list.append(len(self.sequential_list))
                self.sequential_list.append(SequentialElement(text, "h" + str(len(self.header_list) - 1), header_index))
                header_index = header_index + 1
            elif self.pattern_list.match(name):
                for descendant in element.children:
                    if self.skip_tag(descendant):
                        continue
                    text = text + descendant.get_text() + "\n"

                self.list_list.append(len(self.sequential_list))
                self.sequential_list.append(SequentialElement(text, "l" + str(len(self.list_list) - 1), list_index))
                list_index = list_index + 1

                continue

            # elif name == "a":
                # print("PUT LINK IN DUMP FILE " + self.outfile_links)
            #     with open(self.outfile_links, "a") as f:
            #         f.write(element.get_text(strip=True) + "\n")

            self.walk_tree(element)

    def remove_text(self, txt_contents, fname):
        """ Remove text from txt_contents based on lines from specific
        output file.
        
        Param:  txt_contents - string representation of stripped text
                fname - filename the stripped text comes from
        Return: txt_contents - updated string representation of 
                               stripped text
        """
        try:
            with open(fname, "r") as fp:
                line = fp.readline()
                while line:
                    txt_contents = txt_contents.replace(line.strip(), "", 1)
                    line = fp.readline()
            return txt_contents
        except EnvironmentError: # parent of IOError, OSError *and* WindowsError where available
            self.failed = self.failed + 1
            print("FAILED: " + fname + " because current parsing does not get any text.")
            return fname + " failed because the current parsing does not get any text. " + self.filler_sentences

    def compare_parsed_text(self, txt_contents, fname):
        """ Search contents of stripped text for each line from each
        file of the output, then write the remainder to last output
        file.  Enables human to check effectiveness of simple parser.

        Param:  txt_contents - string representation of stripped text
                fname - filename the stripped text comes from
        Return: list of strings containing a single sentence each.
        """
        txt_contents = self.remove_text(txt_contents, self.outfile_sequential)
        # txt_contents = self.remove_text(txt_contents, self.outfile_ignored)
        # txt_contents = self.remove_text(txt_contents, self.outfile_lists)
        # txt_contents = self.remove_text(txt_contents, self.outfile_paragraphs)
        # txt_contents = self.remove_text(txt_contents, self.outfile_headers)

        remaining_sentences = sent_tokenize(txt_contents)
        for sentence in remaining_sentences:
            with open(self.outfile_compare, "a") as fp:
                fp.write(str(sentence) + "\n")
        return remaining_sentences


    def run(self):
        """ Run the SimpleParser.

        Param:  n/a
        Return: n/a
        """
        index = 0
        self.outfile = "output.txt"
        for fname in self.files:
            index = index + 1
            with open(self.dataset_html + fname, "r") as fp:
                html_contents = fp.read()
            with open(self.dataset_text + fname[:-5] + ".txt", "r") as fp:
                txt_contents = fp.read()
            if html_contents == "":
                print("Skipping " + fname + " because it has no html contents.")
                # this isn't considered failure because html empty isn't the parser's fault
                continue
            if txt_contents == "":
                print("Skipping " + fname + " because it has no text contents.")
                # this isn't considered failure because if the whole text is empty, there's no way to compare
                continue

            soup = BeautifulSoup(html_contents, 'html.parser')
        
            self.outfile_sequential = output_folder + fname + self.timestamp + '_sequential.txt'
            self.outfile_ignored = output_folder + fname + self.timestamp + '_ignored.txt'
            self.outfile_paragraphs = output_folder + fname + self.timestamp + '_paragraphs.txt'
            self.outfile_headers = output_folder + fname + self.timestamp + '_headers.txt'
            self.outfile_lists = output_folder + fname + self.timestamp + '_lists.txt'
            self.outfile_links = output_folder + fname + self.timestamp + '_links.txt'
            self.outfile_compare = output_folder + fname + self.timestamp + '_compare.txt'

            self.walk_tree(soup)

            self.output_list_to_file(self.paragraph_list, self.outfile_paragraphs)
            self.output_list_to_file(self.header_list, self.outfile_headers)
            self.output_list_to_file(self.list_list, self.outfile_lists)
            print(self.paragraph_list)
            out_string = ""
            for element in self.sequential_list:
                out_string = out_string + element.tag_type + '\n' + element.content_string + "\n"
            with open(self.outfile_sequential, "a") as f:
                    f.write(out_string)

            remaining_sentences = self.compare_parsed_text(txt_contents, fname)
            if len(remaining_sentences) > 5:
                self.failed = self.failed + 1
                with open(self.outfile, "a") as fp:
                    fp.write(fname + " has " + str(len(remaining_sentences)) + " left.\n")
            sys.stdout.write("\033[K")
            print("Processing " + fname + " (" + str(index) + " of " + str(total_files) + ")", end='\r')

        print("Successfully parsed " + str(((total_files - self.failed) / total_files) * 100) + "% of the " + str(total_files) + " files.")


if __name__ == '__main__':
    dataset_html = "../../data/policies/html/"
    dataset_text = "../../data/policies/text_redo/"
    output_folder = "./"
    files =["netflix_1.html"]
    total_files = len(files)
    parser = SimpleParser(dataset_html, dataset_text, files)

    # total_files = len([name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))])
    # parser = SimpleParser(dataset_html, dataset_text, os.listdir(dataset_html))
    
    parser.run()
