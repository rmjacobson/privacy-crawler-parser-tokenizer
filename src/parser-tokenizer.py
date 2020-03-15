"""
Privacy Policy Project
HTML Parser
Takes in HTML file, splits all text from paragraphs (<p>), headers (<hX>),
lists (<ul> and <ol>), and links (<a>), and dumps each into separate files.
Preserves document structure and traceability in sentence outputs.
"""

from bs4 import BeautifulSoup, Comment, NavigableString
import argparse, csv, datetime, matplotlib, matplotlib.pyplot as plt, nltk, os, re, signal, sys, time
from multiprocessing import Pool, Lock, Value, cpu_count
from nltk.tokenize import sent_tokenize
from utils.utils import mkdir_clean, print_progress_bar, VerifyJsonExtension
from verification.verify import remove_bad_tags
from statistics.sentences import apply_sentence_rules, build_rule_dict, generate_rule_bar_fig, generate_rule_hist_figs

class SequentialElement:
    """
    Class for elements of the sequential list to retain traceability.
    """
    def __init__(self, content_string, tag_type, tag_index):
        self.content_string = content_string
        self.tag_type = tag_type
        self.tag_index = tag_index

class ParserData:
    """
    Class for data used during the parsing of a single policy.  This
    data structure is initialized to be empty at start of every
    parsing process.
    """
    def __init__(self, rule_dict):
        self.seq_list = []
        self.paragraph_list = []
        self.header_list = []
        self.list_list = []
        self.rule_hits = rule_dict.copy()
        self.rule_hits = self.rule_hits.fromkeys(self.rule_hits, 0)
        self.rule_hits["GOOD"] = 0

def skip_tag(element):
    """ Check if given tag is relevant to the parser.
    https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
    
    In:     element - bs4 tag
    Out:    Boolean: True if tag is irrelevant, False if tag is relevant
    """
    if isinstance(element, Comment):
        # this is a commnent in the HTML code
        return True
    if isinstance(element, NavigableString):
        # bs4 datatype, don't want to retain bs4 tree navigation inside strings
        return True
    return False

    # def is_only_links(self, element):
    #     """
    #     Check if passed-in element consists only of hyperlinks.
    #     I     element - bs4 tag
    #     Out:  Boolean - True if element only links, False otherwise
    #     """
    #     ret = True
    #     children = element.findChildren(recursive=False)
    #     for child in children:
    #         name = getattr(child, "name", None)
    #         if name != "a":
    #             ret = False
    #     return ret

def write_tag_list_to_csv(parser, l, output_file):
    """
    Output contents of given tag list to csv file.
    Every element of tag list is an index of the sequential list
    where the actual tag element information can be found.
    Note: need to be careful of list bounds on the sequential list.

    In:     parser to access sequential list, l to write out, string
            of output file path.
    Out:    CSV file corresponding to list.
    """
    tag_list = []
    headings = ("Sequential Index","Tag Index","Preceeded By","Proceeded By","Tag Text")
    for tag_index, seq_index in enumerate(l, start=0):
        # do the exceptions for edges of lists or for short lists
        try:
            prec_by = parser.seq_list[seq_index-1].tag_type + str(parser.seq_list[seq_index-1].tag_index)
        except IndexError as e:
            prec_by = "None"
        try:
            proc_by = str(parser.seq_list[seq_index+1].tag_type + str(parser.seq_list[seq_index+1].tag_index))
        except IndexError as e:
            proc_by = "None"

        tag_tuple = (
            seq_index,
            tag_index,
            prec_by,
            proc_by,
            parser.seq_list[seq_index].content_string)
        tag_list.append(tag_tuple)

    with open(output_file,"w") as fp:
        csv_writer = csv.writer(fp)
        csv_writer.writerow(headings)
        csv_writer.writerows(tag_list)

def walk_tree(soup, parser):
    """ DFS walk of bs4 html tree.  Only looks at specific tags, works on
    theory that only these tags will contain important/visible text.
    https://stackoverflow.com/questions/4814317/depth-first-traversal-on-beautifulsoup-parse-tree
    
    In:     soup - bs4 instance of the html parser
    Out:    N/A
    """
    paragraph_index = 0
    header_index = 0
    list_index = 0
    pattern_header = re.compile("h\d")
    pattern_list = re.compile("[u|o]l")

    for element in soup.find_all(recursive=False):
        if skip_tag(element):
            continue

        element_name = getattr(element, "name", None)
        text = ""

        if element_name == "p":
            text = element.get_text().strip() + "\n"
            # if "\n" in text.strip():
            #     # text = text.replace("\n", "").replace("\r", "").replace("                ", "")
            #     text = " ".join(text.split())
            #     print(text)
            #     print("detected weird newline")
            # text = " ".join(text.split())
            parser.paragraph_list.append(len(parser.seq_list))
            parser.seq_list.append(SequentialElement(text, "p", paragraph_index))
            paragraph_index += 1
        elif pattern_header.match(element_name):
            text = element.get_text().strip() + "\n"
            parser.header_list.append(len(parser.seq_list))
            parser.seq_list.append(SequentialElement(text, "h", header_index))
            header_index += 1
        elif pattern_list.match(element_name):
            # If the last thing in the sequence ends in a colon, move it to be part 
            # of the list element rather than whatever it was previously because it is 
            # probably a list prefix.
            if len(parser.seq_list) > 0:
                prev_element = parser.seq_list[-1].content_string.strip()
                if prev_element.endswith(":"):
                    text = sent_tokenize(prev_element)[-1] + "\n"
                    parser.seq_list[-1].content_string = parser.seq_list[-1].content_string.replace(text.strip(), "")
                    if parser.seq_list[-1].content_string.strip() == "":
                        parser.seq_list[-1].content_string = "<META: This element identified as list prefix -- moved to content string of that list./META>"
            for descendant in element.children:
                if skip_tag(descendant):
                    continue
                text = text + descendant.get_text().strip() + "\n"
            parser.list_list.append(len(parser.seq_list))
            parser.seq_list.append(SequentialElement(text, "l", list_index))
            list_index += 1

            # continue for lists because the entire list and its descendants have already
            # been parsed
            continue

        walk_tree(element, parser)

def compare_parsed_text(seq_list, auto_stripped_text):
    """
    This is a stupid workaround to the fact that bs4 parsers generally suck.
    Tries to measure whether parsing was "successful" by looking at the 
    automatically scraped text of the policy to the text we parse here.
    Note: can't match/replace entire elements at a time because of 
    weirdness in how certain things get scraped by bs4.

    In:     sequential list of elements, stripped text of policy HTML doc.
    Out:    sentence-tokenized version of remaining text.
    """
    for element in seq_list:
        element_segment_list = element.content_string.splitlines()
        for segment in element_segment_list:
            try:
                auto_stripped_text = auto_stripped_text.replace(segment.strip(), "", 1)
            except ValueError:
                pass  # do nothing!
    return sent_tokenize(auto_stripped_text)

def extract_sentences(parser, outfile_sentences, outfile_rule_bar):
    """ 
    Takes readable text from the parser's list outputs and attempts to
    tokenize the strings into sentences.

    Looks at entire sequential list, currently only acts on paragraph
    and header tags.  Creates list of 6-tuples for every element in 
    the sequential list:
    (sequential index, tag type, tag index, sentence index in tag, sentence text, rule hits)

    In:     all element lists, including sequential list.
    Out:    csv file containing all sentence tokens with rule hits if applicable
            bar graph showing numbers of rule hits on sentences in policy.
    """
    # parser.rule_hits.update({rule:0 for rule in parser.rule_hits})
    processed_tags = ["p","h"]
    sentences_list = []

    # loop through sequential list to build sentences/tuple list
    for i, element in enumerate(parser.seq_list, start=0): # for every tag in the sequential list
        if any(tag in element.tag_type for tag in processed_tags):
            sentences = sent_tokenize(element.content_string)
            for j, sentence in enumerate(sentences, start=0): # for every sentence in each tag
                rule_hits = apply_sentence_rules(sentence, rule_dict)
                for name in parser.rule_hits.keys(): # check every rule in the dict
                    if name in rule_hits: # and increment the parser dict if that key is in the sentence's keys
                        parser.rule_hits[name] += 1
                sentence_tuple = (i, element.tag_type, element.tag_index, j, sentence, len(sentence.split()), "-".join(map(str, rule_hits)))
                sentences_list.append(sentence_tuple)

    # write all sentences to single csv file
    headings = ("Sequential Index","Tag Type", "Tag Index", "Sentence Index in Tag", "Sentence Text", "Number of Words" "Rule Hits")
    with open(outfile_sentences,"w") as fp:
        csv_writer = csv.writer(fp)
        csv_writer.writerow(headings)
        csv_writer.writerows(sentences_list)

    # create bar graphs of policy's sentence rule hits
    generate_rule_bar_fig(parser.rule_hits, outfile_rule_bar)

def process_policy(fname):
    """
    Entry function for each subprocess.  Reads in the HTML contents and
    stripped text of the input policy filename, creates all the output
    files needed for this policy, instantiates a bs4 object and an
    object to hold statistics about the policy, walks the bs4 tree,
    outputs each tag-type's list to its own CSV file, then builds
    the sequential list of all elements in the HTML file, then hands
    everything off to the sentence extraction phase.

    In:     policy filename.
    Out:    tuple containing policy rule_hits dict and the filename.
    """
    with open(dataset_html + fname, "r") as fp:
        html_contents = fp.read()
    with open(dataset_text + fname[:-5] + ".txt", "r") as fp:
        auto_stripped_text = fp.read()
    if html_contents == "":
        print("Skipping " + fname + " because it has no html contents.")
        # this isn't considered failure because html empty isn't the parser's fault
        return None
    if auto_stripped_text == "":
        print("Skipping " + fname + " because it has no text contents.")
        # this isn't considered failure because if the whole text is empty, there's no way to compare
        return None

    # build all the output files
    outfile_sequential = parser_output_folder + fname[:-5] + timestamp + "_sequential.txt"
    outfile_paragraphs = parser_output_folder + fname[:-5] + timestamp + "_paragraphs.csv"
    outfile_headers = parser_output_folder + fname[:-5] + timestamp + "_headers.csv"
    outfile_lists = parser_output_folder + fname[:-5] + timestamp + "_lists.csv"
    outfile_compare = parser_output_folder + fname[:-5] + timestamp + "_compare.txt"
    outfile_rule_bar = tokenizer_output_folder + fname[:-5] + timestamp + "_rule_bar.png"
    outfile_sentences = tokenizer_output_folder + fname[:-5] + timestamp + "_sentences.csv"

    # walk tree to parse all the beautiful soup tags and build comparison text
    try:
        soup = BeautifulSoup(html_contents, "html.parser")
    except Exception as e:
        print("Skipping " + fname + " because it can't be read by BeautifulSoup.")
        return None   # if there's no soup, we don't care
    parser = ParserData(rule_dict)
    walk_tree(remove_bad_tags(soup), parser)

    # output the parsed tags to their appropriate files
    if len(parser.paragraph_list) > 0:
        write_tag_list_to_csv(parser, parser.paragraph_list, outfile_paragraphs)
    if len(parser.header_list) > 0:
        write_tag_list_to_csv(parser, parser.header_list, outfile_headers)
    if len(parser.list_list) > 0:
        write_tag_list_to_csv(parser, parser.list_list, outfile_lists)

    # go through entire sequential list to build sequential file
    out_string = ""
    for element in parser.seq_list:
        out_string = out_string + element.tag_type + str(element.tag_index) + "\n" + element.content_string + "\n"
    with open(outfile_sequential, "a") as fp:
        fp.write(out_string)

    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(files), prefix = "Parsing-Tokenizing Progress:", suffix = "Complete", length = 50)

    # Decide whether the parsing was successful
    remaining_sentences = compare_parsed_text(parser.seq_list,auto_stripped_text)
    lock = Lock()   # do full lock here because err.txt & success.txt are shared files
    if len(remaining_sentences) > 5:
        # parsing failed --> don't bother doing anything else to this policy
        lock.acquire()
        try:
            num_failed_policies.value += 1
            with open(outfile_compare, "a") as fp:
                fp.write("\n\n".join(remaining_sentences) + "\n")
            with open(parser_output_folder + "err.txt", "a") as fp:
                fp.write(fname[:-5] + " has " + str(len(remaining_sentences)) + " left.\n")
        finally:
            lock.release()
        return None
    else:
        # parsing succeeded --> sentence tokenize as much as possible from
        extract_sentences(parser, outfile_sentences, outfile_rule_bar)
        lock.acquire()
        try:
            with open(parser_output_folder + "success.txt", "a") as fp:
                fp.write(fname[:-5] + " has " + str(parser.rule_hits["GOOD"]) + " good sentences.\n")
        finally:
            lock.release()
        return (parser.rule_hits.copy(), fname)

def start_process(i, failed):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global index, num_failed_policies
    index = i
    num_failed_policies = failed

if __name__ == '__main__':
    argparse = argparse.ArgumentParser(description="Parse input HTML documents and tokenize sentences from each policy.")
    argparse.add_argument(  "dataset_html",
                            help="input dataset of HTML documents to parse and tokenize.")
    argparse.add_argument(  "dataset_text",
                            help="input dataset of text documents scraped from each HTML document.")
    argparse.add_argument(  "rules",
                            help="json file containing list of sentence rules.",
                            action=VerifyJsonExtension)
    argparse.add_argument(  "parser_output_folder",
                            help="directory to dump outputs from the parser (paragraph/header/sequential.csv files, etc.).")
    argparse.add_argument(  "tokenizer_output_folder",
                            help="directory to dump outputs from the tokenizer (sentences.csv, statistics, etc.")
    args = argparse.parse_args()
    dataset_html = args.dataset_html
    dataset_text = args.dataset_text
    parser_output_folder = args.parser_output_folder
    tokenizer_output_folder = args.tokenizer_output_folder
    rule_dict = build_rule_dict(args.rules)
    mkdir_clean(parser_output_folder)
    mkdir_clean(tokenizer_output_folder)
    timestamp = "_{0:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
    parse_index = Value("i",0)          # shared val, index of current parsed file
    num_failed_policies = Value("i",0)  # shared val, number of policies on which parsing failed at some point

    # use this for the entire dataset
    files = [name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))]
    total_files = len(files)
    
    # Use Multithreading pool because the pool will automatically avoid
    # the chunking idle-process problem where one chunk needs less time
    # than another because of difference in policy length.
    # https://nathangrigg.com/2015/04/python-threading-vs-processes
    # https://pymotw.com/3/multiprocessing/communication.html
    # https://docs.python.org/3.7/library/multiprocessing.html#sharing-state-between-processes
    # https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Value
    # https://stackoverflow.com/questions/44774853/exit-multiprocesses-gracefully-in-python3
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=(parse_index, num_failed_policies)
    )
    policy_sentence_stats = pool.map(process_policy, files) # map keeps domain_list order
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    # remove policies that failed parsing
    policy_sentence_stats = list(filter(None, policy_sentence_stats))
    num_successful_policies = total_files - num_failed_policies.value

    print("Generating last rule histogram...")
    rule_hits_list = [rule_hits for rule_hits,fname in policy_sentence_stats]
    generate_rule_hist_figs(rule_hits_list, num_successful_policies, rule_dict, tokenizer_output_folder + "rule_hists.png")

    print("Successfully parsed " + str(round((num_successful_policies / total_files) * 100, 2)) + "% of the " + str(total_files) + " files.")
    print("Done")
