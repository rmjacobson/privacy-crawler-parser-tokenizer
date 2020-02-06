#!/usr/bin/python3

"""
Privacy Policy Project
HTML Parser
Takes in HTML file, splits all text from paragraphs (<p>), headers (<hX>),
lists (<ul> and <ol>), and links (<a>), and dumps each into separate files.
Preserves document structure and traceability in sentence outputs.
"""

from bs4 import BeautifulSoup, Comment, NavigableString, CData, Tag, ProcessingInstruction
import sys, os, time, datetime, re, nltk, csv
from nltk.tokenize import sent_tokenize
import matplotlib
import matplotlib.pyplot as plt
from multiprocessing import Pool, Lock, Value, cpu_count, current_process
import signal

pattern_header = re.compile("h\d")
pattern_list = re.compile("[u|o]l")
pattern_prefix_noise = re.compile("^(?:[a-zA-Z0-9]|[-](?=[^-]*$)){1,3}$\:*")
pattern_uppercase_first = re.compile("[A-Z]")
pattern_sentence_end_punc = re.compile("[\.?!]$")

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
    def __init__(self):  
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

def skip_tag(element):
    """ Check if given tag is relevant to the parser.
    https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
    
    Param:  element - bs4 tag
    Return: Boolean: True if tag is irrelevant, False if tag is relevant
    """
    if element.name in ["style", "script", "noscript", "head", "title", "meta", "[document]"]:
        # this is an "invisible" tag the reader would not see
        return True
    if element.name in ["header", "footer", "nav"]:
        # this is a "skipped" tag
        return True
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
    #     Param:  element - bs4 tag
    #     Return: Boolean - True if element only links, False otherwise
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

    with open(output_file,'w') as fp:
        csv_writer = csv.writer(fp)
        csv_writer.writerow(headings)
        csv_writer.writerows(tag_list)

def walk_tree(soup, parser):
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
        if skip_tag(element):
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
                if prev_element.endswith(':'):
                    text = sent_tokenize(prev_element)[-1] + '\n'
                    parser.seq_list[-1].content_string = parser.seq_list[-1].content_string.replace(text.strip(), '')
                    if parser.seq_list[-1].content_string.strip() == '':
                        parser.seq_list[-1].content_string = '<META: This element identified as list prefix -- moved to content string of that list./META>'
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

def compare_parsed_text(parser, auto_stripped_text):
    """
    This is a stupid workaround to the fact that bs4 parsers generally suck.
    Tries to measure whether parsing was "successful" by looking at the 
    automatically scraped text of the policy to the text we parse here.
    Note: can't match/replace entire elements at a time because of 
    weirdness in how certain things get scraped by bs4.
    """
    for element in parser.seq_list:
        element_segment_list = element.content_string.splitlines()
        for segment in element_segment_list:
            try:
                auto_stripped_text = auto_stripped_text.replace(segment.strip(), "", 1)
            except ValueError:
                pass  # do nothing!
    return sent_tokenize(auto_stripped_text)

def is_header_fragment(sentence):
    """
    > 60% words start with a capital letter, usually when things
    # that are usually in <hX> tags are part of <p> tags.
    """
    words = sentence.split()
    ncaps = 0
    for word in words:
        caps = [l for l in word if l.isupper()]
        if len(caps) > 0:
            ncaps += 1
    if (ncaps / len(words)) > 0.6:
        return True
    else:
        return False

def generate_rule_hist_figs(policy_sentence_stats, num_files):
    """
    Creates aggregate representation of the rule_vals dictionaries
    collected from every successfully parsed file.  Produces histograms
    of every sentence parsing rule and presents them as a single image.
    """
    rule_dict_list = [rule_dict for rule_dict,fname in policy_sentence_stats]
    
    fig = plt.figure(figsize=(20,10))

    result = [d['SHORT'] for d in rule_dict_list]
    short_fig = fig.add_subplot(321)
    short_fig.set_xlabel('SHORT Rule Hit Count')
    short_fig.set_ylabel('Number of Policies')
    short_fig.hist(result, num_files)

    result = [d['LONG'] for d in rule_dict_list]
    long_fig = fig.add_subplot(322)
    long_fig.set_xlabel('LONG Rule Hit Count')
    long_fig.set_ylabel('Number of Policies')
    long_fig.hist(result, num_files)

    result = [d['START_CAP'] for d in rule_dict_list]
    start_fig = fig.add_subplot(323)
    start_fig.set_xlabel('START_CAP Rule Hit Count')
    start_fig.set_ylabel('Number of Policies')
    start_fig.hist(result, num_files)

    result = [d['END_PUNC'] for d in rule_dict_list]
    end_fig = fig.add_subplot(324)
    end_fig.set_xlabel('END_PUNC Rule Hit Count')
    end_fig.set_ylabel('Number of Policies')
    end_fig.hist(result, num_files)

    result = [d['PRE_NOISE'] for d in rule_dict_list]
    pre_fig = fig.add_subplot(325)
    pre_fig.set_xlabel('PRE_NOISE Rule Hit Count')
    pre_fig.set_ylabel('Number of Policies')
    pre_fig.hist(result, num_files)

    result = [d['HEAD_FRAG'] for d in rule_dict_list]
    head_fig = fig.add_subplot(326)
    head_fig.set_xlabel('HEAD_FRAG Rule Hit Count')
    head_fig.set_ylabel('Number of Policies')
    head_fig.hist(result, num_files)

    outfile_rule_hists = output_folder + 'rule_hists.png'
    fig.tight_layout()
    fig.savefig(outfile_rule_hists)

def apply_sentence_rules(parser, sentence):
    num_words = len(sentence.split())
    rule_hits = []
    if num_words < 5:
        # probably due to things like addresses or header fragments
        parser.rule_vals["SHORT"] += 1
        rule_hits.append("SHORT")
    if num_words > 85:
        # probably a run-on sentence that hasn't been properly parsed
        parser.rule_vals["LONG"] += 1
        rule_hits.append("LONG")
    if not pattern_uppercase_first.match(sentence):
        # probably due to improperly scraped fragment (like from a div)
        # might be able to go back to these and re-parse
        parser.rule_vals["START_CAP"] += 1
        rule_hits.append("START_CAP")
    if not pattern_sentence_end_punc.search(sentence):
        # usually the beginning of a list (and ends with ':')
        parser.rule_vals["END_PUNC"] += 1
        rule_hits.append("END_PUNC")
    if pattern_prefix_noise.match(sentence):
        # things like "1. " or "A: " that are more like headings in an outline
        # might be able to go back to these and re-parse
        parser.rule_vals["PRE_NOISE"] += 1
        rule_hits.append("PRE_NOISE")
    if is_header_fragment(sentence):
        # > 50% words start with a capital letter, usually when things
        # that are usually in <hX> tags are part of <p> tags.
        parser.rule_vals["HEAD_FRAG"] += 1
        rule_hits.append("HEAD_FRAG")
    if sentence.startswith("<META: ") and sentence.endswith("/META>"):
        # these in-string tags used to describe things the parser
        # does that may affect the content of the sentencs.
        parser.rule_vals["META"] += 1
        rule_hits.append("META")
    if len(rule_hits) == 0:
        # if none of the above rules are flagged, call the sentence good
        parser.rule_vals["GOOD"] += 1
   
    return rule_hits

def extract_sentences(parser, outfile_sentences, outfile_rule_bar):
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
    parser.rule_vals.update({rule:0 for rule in parser.rule_vals})
    processed_tags = ['p','h']
    sentences_list = []

    # loop through sequential list to build sentences/tuple list
    for i, element in enumerate(parser.seq_list, start=0):
        if any(tag in element.tag_type for tag in processed_tags):
            sentences = sent_tokenize(element.content_string)
            for j, sentence in enumerate(sentences, start=0):
                rule_hits = apply_sentence_rules(parser, sentence)
                sentence_tuple = (i, element.tag_type, element.tag_index, j, sentence, '-'.join(map(str, rule_hits)))
                sentences_list.append(sentence_tuple)

    # write all sentences to single csv file
    headings = ("Sequential Index","Tag Type", "Tag Index", "Sentence Index in Tag", "Sentence Text", "Rule Hits")
    with open(outfile_sentences,'w') as fp:
        csv_writer = csv.writer(fp)
        csv_writer.writerow(headings)
        csv_writer.writerows(sentences_list)

    # create bar graphs of policy's sentence rule hits
    plt.bar(range(len(parser.rule_vals)), list(parser.rule_vals.values()), align='center')
    plt.xticks(range(len(parser.rule_vals)), list(parser.rule_vals.keys()), rotation=30, fontsize=8)
    plt.ylabel("# of Sentences in Policy")
    plt.savefig(outfile_rule_bar)

def process_policy(fname):
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
    outfile_sequential = output_folder + fname[:-5] + timestamp + '_sequential.txt'
    outfile_sentences = output_folder + fname[:-5] + timestamp + '_sentences.csv'
    outfile_paragraphs = output_folder + fname[:-5] + timestamp + '_paragraphs.csv'
    outfile_headers = output_folder + fname[:-5] + timestamp + '_headers.csv'
    outfile_lists = output_folder + fname[:-5] + timestamp + '_lists.csv'
    outfile_compare = output_folder + fname[:-5] + timestamp + '_compare.txt'
    outfile_rule_bar = output_folder + fname[:-5] + timestamp + '_rule_bar.png'

    # walk tree to parse all the beautiful soup tags and build comparison text
    soup = BeautifulSoup(html_contents, 'html.parser')
    parser = ParserData()
    walk_tree(soup, parser)

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
        out_string = out_string + element.tag_type + str(element.tag_index) + '\n' + element.content_string + "\n"
    with open(outfile_sequential, "a") as fp:
        fp.write(out_string)

    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(files), prefix = 'Parsing Progress:', suffix = 'Complete', length = 50)

    # Decide whether the parsing was successful
    remaining_sentences = compare_parsed_text(parser,auto_stripped_text)
    lock = Lock()   # do full lock here because err.txt & success.txt are shared files
    if len(remaining_sentences) > 5:
        # parsing failed --> don't bother doing anything else to this policy
        lock.acquire()
        try:
            num_failed_policies.value += 1
            with open(outfile_compare, "a") as fp:
                fp.write("\n\n".join(remaining_sentences) + "\n")
            with open("err.txt", "a") as fp:
                fp.write(fname[:-5] + " has " + str(len(remaining_sentences)) + " left.\n")
        finally:
            lock.release()
        return None
    else:
        # parsing succeeded --> sentence tokenize as much as possible from
        extract_sentences(parser, outfile_sentences, outfile_rule_bar)
        lock.acquire()
        try:
            with open("success.txt", "a") as fp:
                fp.write(fname[:-5] + " has " + str(parser.rule_vals["GOOD"]) + " good sentences.\n")
        finally:
            lock.release()
        return (parser.rule_vals.copy(), fname)

def start_process(i, failed):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # print('Starting', current_process().name)
    global index, num_failed_policies
    index = i
    num_failed_policies = failed

if __name__ == '__main__':
    dataset_html = "../../data/policies/html/"
    dataset_text = "../../data/policies/text_redo/"
    output_folder = "./output/"
    timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
    parse_index = Value('i',0)          # shared val, index of current parsed file
    num_failed_policies = Value('i',0)  # shared val, number of policies on which parsing failed at some point

    # use this for a selection of 500 random files
    # files = [line.rstrip('\n') for line in open("./rand_files.txt")]
    # use this for the entire dataset
    files = [name for name in os.listdir(dataset_html) if os.path.isfile(os.path.join(dataset_html, name))]
    total_files = len(files)
    print("got files, start pool")
    
    # Use Multithreading pool because the pool will automatically avoid
    # the chunking idle-process problem where one chunk needs less time
    # than another because of difference in policy length.
    # https://nathangrigg.com/2015/04/python-threading-vs-processes
    # https://pymotw.com/3/multiprocessing/communication.html
    # https://docs.python.org/3.7/library/multiprocessing.html#sharing-state-between-processes
    # https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Value
    # https://stackoverflow.com/questions/44774853/exit-multiprocesses-gracefully-in-python3
    pool_size = cpu_count() * 2
    matplotlib.use('agg')   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=(parse_index, num_failed_policies)
    )
    policy_sentence_stats = pool.map(process_policy, files)
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    # remove policies that failed parsing
    policy_sentence_stats = list(filter(None, policy_sentence_stats))
    num_successful_policies = total_files - num_failed_policies.value

    print("Generating last rule histogram...")
    generate_rule_hist_figs(policy_sentence_stats, num_successful_policies)

    print("Successfully parsed " + str((num_successful_policies / total_files) * 100) + "% of the " + str(total_files) + " files.")
