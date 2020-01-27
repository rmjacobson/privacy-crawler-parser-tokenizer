#!/usr/bin/python3

"""
Privacy Policy Project
Simple HTML Parser
Takes in HTML file, splits all text from paragraphs (<p>), headers (<hX>),
lists (<ul> and <ol>), and links (<a>), and dumps each into separate files.
Does not preserve document structure, just splits component parts.
"""

from bs4 import BeautifulSoup, Comment, NavigableString, CData, Tag, ProcessingInstruction
import sys, os, datetime, re, nltk, csv
from nltk.tokenize import sent_tokenize
import matplotlib.pyplot as plt


def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


class SequentialElement:
    def __init__(self, content_string, tag_type, tag_index):  
        self.content_string = content_string
        self.tag_type = tag_type
        self.tag_index = tag_index


class SimpleParser:
    """ Strip readable/visible text from HTML document. """

    invisible_tags = ["style", "script", "noscript", "head", "title", "meta", "[document]"]
    skipped_tags = ["header", "footer", "nav"]

    pattern_header = re.compile("h\d")
    pattern_list = re.compile("[u|o]l")
    pattern_prefix_noise = re.compile("^(?:[a-zA-Z0-9]|[-](?=[^-]*$)){1,3}$\:*")
    pattern_uppercase_first = re.compile("[A-Z]")
    pattern_sentence_end_punc = re.compile("[\.?!]$")

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
        self.total_sentences = 0
        self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
        self.failed = 0
        self.seq_list = []
        self.paragraph_list = []
        self.header_list = []
        self.list_list = []
        self.rule_vals = {
            "SHORT"     : 0,
            "LONG"      : 0,
            "START_CAP" : 0,
            "END_PUNC"  : 0,
            "PRE_NOISE" : 0,
            "HEAD_FRAG" : 0,
            "META"      : 0,
            "GOOD"      : 0
        }

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
        """
        Check if passed-in element consists only of hyperlinks.
        Param:  element - bs4 tag
        Return: Boolean - True if element only links, False otherwise
        """
        ret = True
        children = element.findChildren(recursive=False)
        for child in children:
            name = getattr(child, "name", None)
            if name != "a":
                ret = False
        return ret

    def write_tag_list_to_csv(self, l, output_file):
        """
        Output contents of given tag list to csv file.
        Every element of tag list is an index of the sequential list
        where the actual tag element information can be found.
        Note: need to be careful of list bounds on the sequential list.
        """
        tag_list = []
        headings = ("Sequential Index","Tag Index","Preceeded By","Proceeded By","Tag Text")
        for tag_index, seq_index in enumerate(l, start=0):
            if seq_index < 1:
                tag_tuple = (
                    seq_index,
                    tag_index,
                    "None",
                    self.seq_list[seq_index+1].tag_type + str(self.seq_list[seq_index+1].tag_index),
                    self.seq_list[seq_index].content_string)
            elif seq_index > (len(self.seq_list) - 2):
                tag_tuple = (
                    seq_index,
                    tag_index,
                    self.seq_list[seq_index-1].tag_type + str(self.seq_list[seq_index-1].tag_index),
                    "None",
                    self.seq_list[seq_index].content_string)
            else:
                tag_tuple = (
                    seq_index,
                    tag_index,
                    self.seq_list[seq_index-1].tag_type + str(self.seq_list[seq_index-1].tag_index),
                    self.seq_list[seq_index+1].tag_type + str(self.seq_list[seq_index+1].tag_index),
                    self.seq_list[seq_index].content_string)
            tag_list.append(tag_tuple)

        with open(output_file,'w') as fp:
            csv_writer = csv.writer(fp)
            csv_writer.writerow(headings)
            csv_writer.writerows(tag_list)

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
            if self.skip_tag(element):
                continue

            element_name = getattr(element, "name", None)
            text = ""

            if element_name == "p":
                text = element.get_text().strip() + "\n"
                # if '\n' in text.strip():
                #     # text = text.replace('\n', '').replace('\r', '').replace('                ', '')
                #     text = " ".join(text.split())
                #     print(text)
                #     print("detected weird newline")
                # text = " ".join(text.split())
                self.paragraph_list.append(len(self.seq_list))
                self.seq_list.append(SequentialElement(text, "p", paragraph_index))
                paragraph_index = paragraph_index + 1
            elif self.pattern_header.match(element_name):
                text = element.get_text().strip() + "\n"
                self.header_list.append(len(self.seq_list))
                self.seq_list.append(SequentialElement(text, "h", header_index))
                header_index = header_index + 1
            elif self.pattern_list.match(element_name):
                # If the last thing in the sequence ends in a colon, move it to be part 
                # of the list element rather than whatever it was previously because it is 
                # probably a list prefix.
                if len(self.seq_list) > 0:
                    prev_element = self.seq_list[-1].content_string.strip()
                    if prev_element.endswith(':'):
                        text = sent_tokenize(prev_element)[-1] + '\n'
                        self.seq_list[-1].content_string = self.seq_list[-1].content_string.replace(text.strip(), '')
                        if self.seq_list[-1].content_string.strip() == '':
                            self.seq_list[-1].content_string = '<META: This element identified as list prefix -- moved to content string of that list./META>'
                for descendant in element.children:
                    if self.skip_tag(descendant):
                        continue
                    text = text + descendant.get_text().strip() + "\n"
                self.list_list.append(len(self.seq_list))
                self.seq_list.append(SequentialElement(text, "l", list_index))
                list_index = list_index + 1

                # continue for lists because the entire list and its descendants have already
                # been parsed
                continue

            self.walk_tree(element)

    def compare_parsed_text(self):
        """
        This is a stupid workaround to the fact that bs4 parsers generally suck.
        Tries to measure whether parsing was "successful" by looking at the 
        automatically scraped text of the policy to the text we parse here.
        Note: can't match/replace entire elements at a time because of 
        weirdness in how certain things get scraped by bs4.
        """
        for element in self.seq_list:
            element_segment_list = element.content_string.splitlines()
            for segment in element_segment_list:
                try:
                    self.auto_stripped_text = self.auto_stripped_text.replace(segment.strip(), "", 1)
                except ValueError:
                    pass  # do nothing!
        return sent_tokenize(self.auto_stripped_text)

    def is_header_fragment(self, sentence):
        """
        > 60% words start with a capital letter, usually when things
        # that are usually in <hX> tags are part of <p> tags.
        """
        words = sentence.split()
        ncaps = 0
        for word in words:
            caps = [l for l in word if l.isupper()]
            if len(caps) > 0:
                ncaps = ncaps + 1
        if (ncaps / len(words)) > 0.6:
            return True
        else:
            return False

    def generate_rule_hist_figs(self, rule_dict_list, num_files):
        # plt.bar(range(len(self.rule_vals)), list(self.rule_vals.values()), align='center')
        # plt.xticks(range(len(self.rule_vals)), list(self.rule_vals.keys()))
        # plt.show()

        fig = plt.figure(figsize=(20,10))

        result = [d['SHORT'] for d in rule_dict_list]
        short_fig = fig.add_subplot(321)
        short_fig.set_xlabel('SHORT Rule Hits per Policy')
        short_fig.set_ylabel('Number of Policies in Sample')
        short_fig.hist(result, num_files)

        result = [d['LONG'] for d in rule_dict_list]
        long_fig = fig.add_subplot(322)
        long_fig.set_xlabel('LONG Rule Hits per Policy')
        long_fig.set_ylabel('Number of Policies in Sample')
        long_fig.hist(result, num_files)

        result = [d['START_CAP'] for d in rule_dict_list]
        start_fig = fig.add_subplot(323)
        start_fig.set_xlabel('START_CAP Rule Hits per Policy')
        start_fig.set_ylabel('Number of Policies in Sample')
        start_fig.hist(result, num_files)

        result = [d['END_PUNC'] for d in rule_dict_list]
        end_fig = fig.add_subplot(324)
        end_fig.set_xlabel('END_PUNC Rule Hits per Policy')
        end_fig.set_ylabel('Number of Policies in Sample')
        end_fig.hist(result, num_files)

        result = [d['PRE_NOISE'] for d in rule_dict_list]
        pre_fig = fig.add_subplot(325)
        pre_fig.set_xlabel('PRE_NOISE Rule Hits per Policy')
        pre_fig.set_ylabel('Number of Policies in Sample')
        pre_fig.hist(result, num_files)

        result = [d['HEAD_FRAG'] for d in rule_dict_list]
        head_fig = fig.add_subplot(326)
        head_fig.set_xlabel('HEAD_FRAG Rule Hits per Policy')
        head_fig.set_ylabel('Number of Policies in Sample')
        head_fig.hist(result, num_files)

        fig.tight_layout()
        fig.savefig(self.outfile_rule_hists)

    def apply_sentence_rules(self, sentence):
        num_words = len(sentence.split())
        rule_hits = []
        if num_words < 5:
            # probably due to things like addresses or header fragments
            self.rule_vals["SHORT"] = self.rule_vals["SHORT"] + 1
            rule_hits.append("SHORT")
        if num_words > 85:
            # probably a run-on sentence that hasn't been properly parsed
            self.rule_vals["LONG"] = self.rule_vals["LONG"] + 1
            rule_hits.append("LONG")
        if not self.pattern_uppercase_first.match(sentence):
            # probably due to improperly scraped fragment (like from a div)
            # might be able to go back to these and re-parse
            self.rule_vals["START_CAP"] = self.rule_vals["START_CAP"] + 1
            rule_hits.append("START_CAP")
        if not self.pattern_sentence_end_punc.search(sentence):
            # usually the beginning of a list (and ends with ':')
            self.rule_vals["END_PUNC"] = self.rule_vals["END_PUNC"] + 1
            rule_hits.append("END_PUNC")
        if self.pattern_prefix_noise.match(sentence):
            # things like "1. " or "A: " that are more like headings in an outline
            # might be able to go back to these and re-parse
            self.rule_vals["PRE_NOISE"] = self.rule_vals["PRE_NOISE"] + 1
            rule_hits.append("PRE_NOISE")
        if self.is_header_fragment(sentence):
            # > 50% words start with a capital letter, usually when things
            # that are usually in <hX> tags are part of <p> tags.
            self.rule_vals["HEAD_FRAG"] = self.rule_vals["HEAD_FRAG"] + 1
            rule_hits.append("HEAD_FRAG")
        if sentence.startswith("<META: ") and sentence.endswith("/META>"):
            # these in-string tags used to describe things the parser
            # does that may affect the content of the sentencs.
            self.rule_vals["META"] = self.rule_vals["META"] + 1
            rule_hits.append("META")
        if len(rule_hits) == 0:
            # if none of the above rules are flagged, call the sentence good
            self.rule_vals["GOOD"] = self.rule_vals["GOOD"] + 1
       
        return rule_hits

    def extract_sentences(self):
        """ 
        Takes readable text from the parser's list outputs and attempts to
        tokenize the strings into sentences.

        Looks at entire sequential list, currently only acts on paragraph
        and header tags.  Creates list of 6-tuples for every element in 
        the sequential list:
        (sequential index, tag type, tag index, sentence index in tag, sentence text, rule hits)

        Params: all element lists, including sequential list
        Return: csv file containing all sentence tokens with rule hits if applicable
                bar graph showing numbers of rule hits on sentences in policy
        """
        self.rule_vals.update({rule:0 for rule in self.rule_vals})
        processed_tags = ['p','h']
        sentences_list = []

        # loop through sequential list to build sentences/tuple list
        for i, element in enumerate(self.seq_list, start=0):
            if any(tag in element.tag_type for tag in processed_tags):
                sentences = sent_tokenize(element.content_string)
                for j, sentence in enumerate(sentences, start=0):
                    rule_hits = self.apply_sentence_rules(sentence)
                    sentence_tuple = (i, element.tag_type, element.tag_index, j, sentence, '-'.join(map(str, rule_hits)))
                    sentences_list.append(sentence_tuple)

        # write all sentences to single csv file
        headings = ("Sequential Index","Tag Type", "Tag Index", "Sentence Index in Tag", "Sentence Text", "Rule Hits")
        with open(self.outfile_sentences,'w') as fp:
            csv_writer = csv.writer(fp)
            csv_writer.writerow(headings)
            csv_writer.writerows(sentences_list)

        # save stats on rule hits to png file
        plt.bar(range(len(self.rule_vals)), list(self.rule_vals.values()), align='center')
        plt.xticks(range(len(self.rule_vals)), list(self.rule_vals.keys()), rotation=30, fontsize=8)
        plt.ylabel("# of Sentences in Policy")
        plt.savefig(self.outfile_rule_bar)

    def run(self):
        """ Run the SimpleParser.

        Param:  n/a
        Return: n/a
        """
        index = 0
        self.outfile = "output.txt"
        rule_dict_list = []
        for fname in self.files:
            index = index + 1
            with open(self.dataset_html + fname, "r") as fp:
                html_contents = fp.read()
            with open(self.dataset_text + fname[:-5] + ".txt", "r") as fp:
                self.auto_stripped_text = fp.read()
            if html_contents == "":
                print("Skipping " + fname + " because it has no html contents.")
                # this isn't considered failure because html empty isn't the parser's fault
                continue
            if self.auto_stripped_text == "":
                print("Skipping " + fname + " because it has no text contents.")
                # this isn't considered failure because if the whole text is empty, there's no way to compare
                continue

            soup = BeautifulSoup(html_contents, 'html.parser')
        
            self.outfile_sequential = output_folder + fname + self.timestamp + '_sequential.txt'
            self.outfile_sentences = output_folder + fname + self.timestamp + '_sentences.csv'
            self.outfile_rule_bar = output_folder + fname + self.timestamp + '_rule_bar.png'
            self.outfile_rule_hists = output_folder + 'rule_hists.png'
            self.outfile_paragraphs = output_folder + fname + self.timestamp + '_paragraphs.csv'
            self.outfile_headers = output_folder + fname + self.timestamp + '_headers.csv'
            self.outfile_lists = output_folder + fname + self.timestamp + '_lists.csv'
            self.outfile_compare = output_folder + fname + self.timestamp + '_compare.txt'

            # walk tree to parse all the beautiful soup tags and build comparison text
            self.walk_tree(soup)

            # output the parsed tags to their appropriate files
            self.write_tag_list_to_csv(self.paragraph_list, self.outfile_paragraphs)
            self.write_tag_list_to_csv(self.header_list, self.outfile_headers)
            self.write_tag_list_to_csv(self.list_list, self.outfile_lists)
            
            # go through entire sequential list to build sequential file
            out_string = ""
            for element in self.seq_list:
                out_string = out_string + element.tag_type + str(element.tag_index) + '\n' + element.content_string + "\n"
            with open(self.outfile_sequential, "a") as f:
                f.write(out_string)

            # Decide whether the parsing was successful
            remaining_sentences = self.compare_parsed_text()
            if len(remaining_sentences) > 5:
                # parsing failed --> don't bother doing anything else to this policy
                self.failed = self.failed + 1
                with open(self.outfile_compare, "a") as fp:
                    fp.write("\n\n".join(remaining_sentences) + "\n")
                with open(self.outfile, "a") as fp:
                    fp.write(fname + " has " + str(len(remaining_sentences)) + " left.\n")
            else:
                # parsing succeeded --> sentence tokenize as much as possible from
                self.extract_sentences()
                rule_dict_list.append(self.rule_vals.copy())

            print_progress_bar(index, len(self.files), prefix = 'Parsing Progress:', suffix = 'Complete', length = 50)

        # output histogram of rule hits for all files
        self.generate_rule_hist_figs(rule_dict_list, len(self.files) - self.failed)


        print("Successfully parsed " + str(((total_files - self.failed) / total_files) * 100) + "% of the " + str(total_files) + " files.")


if __name__ == '__main__':
    dataset_html = "../../data/policies/html/"
    dataset_text = "../../data/policies/text_redo/"
    output_folder = "./output/"
    # files =["netflix_1.html"]
    # files = ["google_1.html","ebay_1.html","amazon_1.html",
    #          "facebook_1.html", "netflix_1.html", "twitter_1.html",
    #          "wikipedia_1.html", "yahoo_1.html", "redbubble_1.html",
    #          "blizzard_1.html", "instagram_1.html", "stackoverflow_1.html",
    #          "steelers_1.html", "studentuniverse_1.html"]
    # files = ["google_1.html", "google_2.html", "ebay_1.html", "amazon_1.html",
    #          "facebook_1.html", "facebook_2.html", "netflix_1.html",
    #          "netflix_2.html", "twitter_1.html", "wikipedia_1.html", "yahoo_1.html",
    #          "yahoo_2.html"]
    files = [name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))]
    total_files = len(files)
    parser = SimpleParser(dataset_html, dataset_text, files)

    # total_files = len([name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))])
    # parser = SimpleParser(dataset_html, dataset_text, os.listdir(dataset_html))
    
    parser.run()
