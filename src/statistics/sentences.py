"""
Privacy Policy Project
"""
import argparse, datetime, json, matplotlib, matplotlib.pyplot as plt, os, random, re, signal
from csv import reader, writer
from math import ceil, sqrt
from matplotlib.ticker import MaxNLocator
import matplotlib.gridspec as gridspec
from multiprocessing import Pool, Lock, Value, cpu_count
from nltk.tokenize import sent_tokenize
from numpy import bincount, arange
from random import sample
from utils.utils import mkdir_clean, print_progress_bar, VerifyJsonExtension

class Policy:
    def __init__(self, file, rule_dict):
        self.file = file
        self.lengths = []
        self.sentences = []
        self.rule_hits = rule_dict.copy()
        self.rule_hits = self.rule_hits.fromkeys(self.rule_hits, 0)
        self.rule_hits["GOOD"] = 0
        # self.rule_hits["length"] = 0

def build_rule_dict(file):
    """
    Build rule dictionary from input JSON file, then compile the regexs
    contained in that file so they can be matched.  Note that the input
    JSON must be properly formatted for *reading* in from the JSON,
    not necessarily properly formatted for native regex.  Escaped
    characters must be double-escaped with an extra backslash because
    they will otherwise not be read in as correct JSON.  If you make
    changes to the rules.json file, please ensure that you have done
    this or the Python json module will complain.  Most good text
    editors will notify you about this if you have the language set to
    JSON when you edit the rules.json file.

    In:     string path to rules.json file.
    Out:    dict of compiled regexs with rule names as keys.
    """
    with open(file, "r") as fp:
        rule_dict = json.load(fp)
    for name in rule_dict:
        if name == "HEAD_FRAG" or name == "SHORT":
            continue
        rule_dict[name][0] = re.compile(rule_dict[name][0])
    return rule_dict

def is_short(sentence, threshold=5):
    """
    Check if the text contains too few words to be a valid sentence.
    The threshold is set to 5 by default but can be changed depending
    on the input SHORT rule.

    In:     sentence text, threshold integer.
    Out:    Boolean.
    """
    words = sentence.split()
    return len(words) < threshold

def is_header_fragment(sentence, threshold=0.6):
    """
    > threshold percentage of words start with a capital letter,
    usually when things # that are usually in <hX> tags are part
    of <p> tags.

    In:     sentence text, threshold float.
    Out:    Boolean.
    """
    words = sentence.split()
    ncaps = 0
    for word in words:
        caps = [l for l in word if l.isupper()]
        if len(caps) > 0:
            ncaps += 1
    if (ncaps / len(words)) > threshold:
        return True
    else:
        return False

def apply_sentence_rules(sentence, rule_dict):
    """
    Take in sentence rules from the rule_dict provided as an input to
    this program.  Match every rule against the regex in the rule_dict
    (except HEAD_FRAG because it has its own function), and append
    the name of the rule to the list to be returned.

    In:     sentence string, rule dictionary of regexs.
    Out:    list of rule names that apply to the sentence.
    """
    # print(sentence)
    rule_hits = []
    for name, rule in rule_dict.items():
        if name == "SHORT":
            if is_short(sentence, rule_dict[name][0]):
                rule_hits.append(name)
            continue
        if name == "HEAD_FRAG":
            if is_header_fragment(sentence, rule_dict[name][0]):
                rule_hits.append(name)
            continue
        if rule[1] == "True" and rule[0].match(sentence):
            hit = True
            rule_hits.append(name)
        if rule[1] == "False" and not rule[0].match(sentence):
            hit = True
            rule_hits.append(name)
    if len(rule_hits) == 0:
        rule_hits.append("GOOD")
    # rule_hits.append("length")
    return rule_hits

def generate_rule_bar_fig(rule_hits, outfile):
    """
    Creates bar graph of policy's sentence rule hits, saves to file.

    In:     rule_hits (list of rule names as strings), output file.
    Out:    N/A
    """
    plt.bar(range(len(rule_hits)), list(rule_hits.values()), align="center", color="blue")
    plt.xticks(range(len(rule_hits)), list(rule_hits.keys()), rotation=30, fontsize=8)
    plt.ylabel("# of Sentences in Policy")
    plt.savefig(outfile)

def extract_sentences(file):
    """
    Reads in csv file from pre-generated parser output and looks at
    every line to gather sentences from it, then apply the input
    ruleset on those sentences, and return statistics.
    """
    policy_stats = Policy(file, rule_dict)

    with open(parser_output_dir + file, "r") as fp:
        csv_reader = reader(fp)
        elements = list(csv_reader)

    sentence_list = []
    for elem in elements:   # for every possible object
        sentences = sent_tokenize(elem[-1])
        for sentence in sentences:  # for every sentence in that object
            rule_hits = apply_sentence_rules(sentence, rule_dict)
            policy_stats.lengths.append(len(sentence.split()))
            sentence_list.append((len(sentence.split()), sentence, rule_hits))
            for name in policy_stats.rule_hits.keys(): # loop through all the keys in the dict
                if name in rule_hits: # and increment the policy_stats dict if that key is in the sentence's keys
                    policy_stats.rule_hits[name] += 1
            policy_stats.sentences.append(rule_hits)

    # write sentences to csv file
    headings = ("Number of Words","Sentence Text","Rule Hits")
    with open(output_folder + file + "_sentences.csv", "w") as fp:
        csv_writer = writer(fp)
        csv_writer.writerow(headings)
        csv_writer.writerows(sentence_list)

    # create bar graphs of policy's sentence rule hits
    generate_rule_bar_fig(policy_stats.rule_hits, output_folder + file[:-4] + "_rule_bar.pdf")

    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(random_files), prefix = "Sentence Statistics Progress:", suffix = "Complete", length = 50)

    return policy_stats

def generate_rule_hist_figs(files, rule_hits, lengths, num_files, rule_dict, outfile):
    """
    Creates aggregate representation of the rule_vals dictionaries
    collected from every successfully parsed file.  Produces histograms
    of every sentence parsing rule and presents them as a single image.
    Does not include "GOOD" rules.

    In:     rule_hits list of all policies rule_hits dictionaries,
            the number of files that were inspected for sentences,
            the rule dict providing the names of rules as keys,
            string filepath to output figure to.
    Out:    figure containing histograms of all rules.
    """
    num_files = len(rule_hits)
    rows = ceil(sqrt(len(rule_dict)) + 1) + 1
    cols = ceil(sqrt(len(rule_dict))) - 1
    # fig = plt.figure(figsize=(rows*10,cols*10))
    # i = 0
    # for i, (name, rule) in enumerate(rule_dict.items(), start=1):
    #     count = [d[name] for d in rule_hits]
    #     subfig = fig.add_subplot(rows,cols,i)
    #     subfig.set_xlabel(name + " Rule Hit Count")
    #     subfig.set_ylabel("Number of Policies")
    #     subfig.xaxis.set_major_locator(MaxNLocator(integer=True))
    #     subfig.hist(count, num_files, rwidth=0.5)
    #     print(i)
    # len_boxplot = fig.add_subplot(rows-1,1,5)
    # len_boxplot.set_xlabel("Sentence Length per Policy")
    # len_boxplot.set_ylabel("")
    # filenames = ["_".join(i.split("_", 2)[:2]) for i in files]
    # len_boxplot.boxplot(lengths)
    # fig.tight_layout()
    # fig.savefig(outfile)
    fig = plt.figure(figsize=(rows*10,cols*10))
    gs = fig.add_gridspec(rows, cols)
    r = 0
    c = 0
    for i, (name, rule) in enumerate(rule_dict.items(), start=1):
        count = [d[name] for d in rule_hits]
        # standalone_fig = hist(count, bins=arange(num_files + 1) - 0.5)
        standalone_fig = plt.figure()
        plt.hist(count, bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 250, 300, 350, 400], rwidth=0.5, figure=standalone_fig)
        plt.xlabel(name + " Rule Hit Count", figure=standalone_fig)
        plt.ylabel("# of Policies", figure=standalone_fig)
        standalone_fig.savefig(outfile[:-4] + "_" + name + ".pdf")
        subfig = fig.add_subplot(gs[r, c])
        subfig.set_xlabel(name + " Rule Hit Count")
        subfig.set_ylabel("# of Policies")
        # subfig.hist(count, bins=arange(num_files + 1) - 0.5)
        subfig.hist(count, bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 250, 300, 350, 400], rwidth=0.5)
        if c < cols-1:
            c += 1
        else:
            c = 0
            r += 1
        print_progress_bar(i, len(rule_dict.items()) + 1, prefix = "Rule Histograms Progress:", suffix = "Complete", length = 50)
    if c != 0:
        r +=1
    len_boxplot = fig.add_subplot(gs[r:, :])
    len_boxplot.set_xlabel("Sentence Length per Policy")
    len_boxplot.set_ylabel("")
    len_boxplot.tick_params(bottom=False, labelbottom=False)
    len_boxplot.boxplot(lengths)
    print_progress_bar(i + 1, len(rule_dict.items()) + 1, prefix = "Rule Histograms Progress:", suffix = "Complete", length = 50)
    fig.tight_layout()
    fig.savefig(outfile)

def start_process(i):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global index
    index = i

if __name__ == '__main__':
    timestamp = "_{0:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
    argparse = argparse.ArgumentParser(description="Read and apply sentence rules to contents of parser output.")
    argparse.add_argument(  "-n", "--num_samples",
                            type=int,
                            default=0,
                            required=False,
                            help="number of files this program should read from the directory.")
    argparse.add_argument(  "rules",
                            help="json file containing list of sentence rules.",
                            action=VerifyJsonExtension)
    argparse.add_argument(  "parser_output_dir",
                            help="directory containing html files to verify.")
    argparse.add_argument(  "-o", "--output_folder",
                            default="./sentence_stats_output" + timestamp + "/",
                            required=False,
                            help="directory to dump sentence stats output.  Will be created if does not exist.")
    args = argparse.parse_args()
    parser_output_dir = args.parser_output_dir
    output_folder = args.output_folder
    rule_dict = build_rule_dict(args.rules)
    mkdir_clean(output_folder)

    files = [name for name in os.listdir(parser_output_dir) if name.endswith("paragraphs.csv")]
    try:
        random_files = sample(files, args.num_samples)
    except ValueError:
        print("ValueError: args.num_samples > # files in parser_output_dir, defaulting to all files in that directory.")
        random_files = files
    if args.num_samples == 0:
        random_files = files

    print("Tokenizing " + str(len(random_files)) + " files...")

    index = Value("i",0)          # shared val, index of current parsed file
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    policy_list = pool.map(extract_sentences, random_files)    # map keeps domain_list order
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    # print("Generating last rule histogram...")
    rule_hits = [p.rule_hits for p in policy_list]
    lengths = [p.lengths for p in policy_list]
    generate_rule_hist_figs(random_files, rule_hits, lengths, len(rule_hits), rule_dict, output_folder + "rule_hists.pdf")
    print("Done")
