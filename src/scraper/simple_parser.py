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
# import detectEnglish


class SimpleParser:
    """ Strip readable/visible text from HTML document. """

    invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
    skipped_tags = ["header", "footer", "nav"]

    pattern_header = re.compile("h\d")
    pattern_list = re.compile("[u|o]l")

    UPPERLETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LETTERS_AND_SPACE = UPPERLETTERS + UPPERLETTERS.lower() + ' \t\n'

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

        self.ENGLISH_WORDS = self.loadDictionary()

    def loadDictionary(self):
        dictionaryFile = open('dictionary.txt')
        englishWords = {}
        for word in dictionaryFile.read().split('\n'):
            englishWords[word] = None
            dictionaryFile.close()
        return englishWords

    def getEnglishCount(self, message):
        message = message.upper()
        message = self.removeNonLetters(message)
        possibleWords = message.split()
        if possibleWords == []:
            return 0.0 # no words at all, so return 0.0
        matches = 0
        for word in possibleWords:
            if word in self.ENGLISH_WORDS:
                matches += 1
        return float(matches) / len(possibleWords)

    def removeNonLetters(self, message):
        lettersOnly = []
        for symbol in message:
            if symbol in self.LETTERS_AND_SPACE:
                lettersOnly.append(symbol)
        return ''.join(lettersOnly)

    def isEnglish(self, message, wordPercentage=20, letterPercentage=85):
        # By default, 20% of the words must exist in the dictionary file, and
        # 85% of all the characters in the message must be letters or spaces
        # (not punctuation or numbers).
        wordsMatch = self.getEnglishCount(message) * 100 >= wordPercentage
        numLetters = len(self.removeNonLetters(message))
        messageLettersPercentage = float(numLetters) / len(message) * 100
        lettersMatch = messageLettersPercentage >= letterPercentage
        return wordsMatch and lettersMatch

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

    def get_grandchildren(self, element):
        ret = []
        children = element.findChildren(recursive=False)
        for child in children:
            grandchildren = child.findChildren(recursive=False)
            for grandchild in grandchildren:
                ret.append(grandchild)
        # if len(ret) == 0:
        #     print("no grandchildren: ")
        return ret

    def is_only_links(self, element):
        ret = True
        children = element.findChildren(recursive=False)
        for child in children:
            name = getattr(child, "name", None)
            if name != "a":
                ret = False
        return ret

    def process_known_tags(self, element):
        name = getattr(element, "name", None)

        if name == "p":
            # print("PUT PARAGRAPH IN DUMP FILE " + self.outfile_paragraphs)
            text = element.get_text() + "\n"
            with open(self.outfile_paragraphs, "a") as f:
                f.write(element.get_text() + "\n")
            # with open(self.outfile_sequential, "a") as f:
            #     f.write(text)
        elif self.pattern_header.match(name):
            # print("PUT HEADER IN DUMP FILE " + self.outfile_headers)
            text = element.get_text() + "\n"
            with open(self.outfile_headers, "a") as f:
                f.write(element.get_text() + "\n")
            # with open(self.outfile_sequential, "a") as f:
            #     f.write(text)
        elif self.pattern_list.match(name):
            # print("PUT LIST IN DUMP FILE " + self.outfile_lists)
            for descendant in element.children:
                if self.skip_tag(descendant) or self.is_only_links(descendant):
                    continue
                with open(self.outfile_lists, "a") as f:
                    f.write(descendant.get_text() + "\n")
                text = text + descendant.get_text() + "\n"
            with open(self.outfile_lists, "a") as f:
                f.write("\n")
            # text = text + "\n"
            # with open(self.outfile_sequential, "a") as f:
            #     f.write(text)


    def process_div(self, element):
        """ Divs are like mini self-contained html pages, except that
        text is obnoxiously not required to be under a separate tag.
        This will processor works by trying to find and extract or
        replace *all* tags that aren't solely sentence-itemizable text
        (like paragraphs) and then grabbing the entire remainder of the
        div as a single paragraph-like chunk.

        Param: element - bs4 node element.
        Return: n/a - all output added to output files.
        """
        children = element.findChildren(recursive=False)
        element_string = str(element)
        element_string_orig = str(element)
        for child in children:
            child_string = str(child)
            name = getattr(child, "name", None)
            if name == "div":
                # print("Found div.  old string = " + element_string)
                element_string = element_string.replace(child_string, self.process_div(child), 1)
                # print("New string = " + element_string)
                continue
            # self.process_known_tags(child, True)
            if name == "p" or name == "a":
                # print("Found tag <" + name + "> replacing \'" + child_string + "\' with \'" + child.get_text() + "\'")
                element_string = element_string.replace(child_string, child.get_text(), 1)
            if self.pattern_header.match(name) or self.pattern_list.match(name):
                # print("found header --> deleting")
                element_string = element_string.replace(child_string, "", 1)
            # print("div contents: " + element_string + "\n")
            self.process_known_tags(child)

        return element_string


    def walk_tree(self, soup):
        """ DFS walk of bs4 html tree.  Only looks at specific tags, works on
        theory that only these tags will contain important/visible text.
        https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
        
        Param:  soup - bs4 instance of the html parser
        Return: n/a
        """
        for element in soup.find_all(recursive=False):
            if self.skip_tag(element):
                # print("skipping <" + name + "> tag" )
                # with open(self.outfile_ignored, "a") as f:
                #     f.write(element.get_text(strip=True) + "\n")
                continue

            name = getattr(element, "name", None)
            text = ""
            from_div = False

            if name == "p":
                # print("PUT PARAGRAPH IN DUMP FILE " + self.outfile_paragraphs)
                text = element.get_text() + "\n"
                with open(self.outfile_paragraphs, "a") as f:
                    f.write(element.get_text() + "\n")
                # with open(self.outfile_sequential, "a") as f:
                #     f.write(text)
            elif self.pattern_header.match(name):
                # print("PUT HEADER IN DUMP FILE " + self.outfile_headers)
                text = element.get_text() + "\n"
                with open(self.outfile_headers, "a") as f:
                    f.write(element.get_text() + "\n")
                # with open(self.outfile_sequential, "a") as f:
                #     f.write(text)
            elif self.pattern_list.match(name):
                # print("PUT LIST IN DUMP FILE " + self.outfile_lists)
                for descendant in element.children:
                    if self.skip_tag(descendant) or self.is_only_links(descendant):
                        continue
                    with open(self.outfile_lists, "a") as f:
                        f.write(descendant.get_text() + "\n")
                    text = text + descendant.get_text() + "\n"
                with open(self.outfile_lists, "a") as f:
                    f.write("\n")
                text = text + "\n"
                # with open(self.outfile_sequential, "a") as f:
                #     f.write(text)
            elif name == "div":
                grandchildren = self.get_grandchildren(element)
                if len(grandchildren) == 0:
                    text = self.process_div(element)
                    from_div = True
                    div_soup = BeautifulSoup(text, 'html.parser')
                    text = div_soup.get_text()
                    with open(self.outfile_sequential, "a") as f:
                        f.write(text + "\n")
                    continue


            if from_div == False:
                with open(self.outfile_sequential, "a") as f:
                    f.write(text)



            # elif name == "div":
            #     grandchildren = self.get_grandchildren(element)
            #     if len(grandchildren) == 0:
            #         text = element.get_text(strip=True) + "\n"
            #         if self.isEnglish(text) and not self.is_only_links(element):
            #             with open(self.outfile_sequential, "a") as f:
            #                 f.write(text)
            #             continue
                    # else:
                    #     print(text)
                # elif "Facebookpixel" in element.get_text(strip=True):
                #     print(len(grandchildren))
                #     for grandchild in grandchildren:
                #         gname = getattr(grandchild, "name", None)
                #         print(gname)
                #     print(element.get('class'))
                #     print(element.get_text(strip=True) + "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
                    
                # if div has grandchildren, continue
                # do isEnglish() on those divs and add to sequential.txt if so
                    # may need to increase sensitivity of isEnglish
                # not sure whether or not we need to remove the div after this to 
                    # avoid repeating text

            # elif name == "a":
                # print("PUT LINK IN DUMP FILE " + self.outfile_links)
            #     with open(self.outfile_links, "a") as f:
            #         f.write(element.get_text(strip=True) + "\n")

            # with open(self.outfile_sequential, "a") as f:
            #     f.write(text)

            # self.process_known_tags(element, False)
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
        txt_contents = self.remove_text(txt_contents, self.outfile_lists)
        # txt_contents = self.remove_text(txt_contents, self.outfile_paragraphs)
        txt_contents = self.remove_text(txt_contents, self.outfile_headers)

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

            # remove all unwanted/non-visible text elements
            rm_elements = ['script', 'noscript', 'meta', 'style', 'link', 'img',
                       'iframe', 'header', 'head', 'footer', 'nav']
            for element in soup(rm_elements):
                element.decompose()
        
            self.outfile_sequential = output_folder + fname + self.timestamp + '_sequential.txt'
            self.outfile_ignored = output_folder + fname + self.timestamp + '_ignored.txt'
            self.outfile_paragraphs = output_folder + fname + self.timestamp + '_paragraphs.txt'
            self.outfile_headers = output_folder + fname + self.timestamp + '_headers.txt'
            self.outfile_lists = output_folder + fname + self.timestamp + '_lists.txt'
            self.outfile_links = output_folder + fname + self.timestamp + '_links.txt'
            self.outfile_compare = output_folder + fname + self.timestamp + '_compare.txt'

            self.walk_tree(soup)

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
    output_folder = "output/"

    # dataset_html = "./"
    # dataset_text = "./"
    # output_folder = "./"
    # files = ["google_1", "google_2", "ebay_1", "amazon_1",
    #          "facebook_1", "facebook_2", "netflix_1",
    #          "netflix_2", "twitter_1", "wikipedia_1", "yahoo_1",
    #          "yahoo_2"]
    
    # files = ["google_1","ebay_1","amazon_1",
    #          "facebook_1", "netflix_1", "twitter_1",
    #          "wikipedia_1", "yahoo_1", "redbubble_1",
    #          "blizzard_1", "instagram_1", "stackoverflow_1",
    #          "steelers_1", "studentuniverse_1"]

    # files =["angieslist_1.html", "avis_2.html", "facebook_1.html", "journaltimes_1.html"]
    # files =["divtest.html"]
    # files =["angieslist_1.html"]
    # total_files = len(files)
    # parser = SimpleParser(dataset_html, dataset_text, files)

    total_files = len([name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))])
    parser = SimpleParser(dataset_html, dataset_text, os.listdir(dataset_html))
    
    parser.run()
