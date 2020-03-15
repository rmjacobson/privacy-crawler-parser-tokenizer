#!/usr/bin/python3

"""
Privacy Policy Project
List Statistics
Randomly samples policy list output files to get the number of
lists per file.  Outputs boxplots with statistics about number of lists
per file and the average length of the lists in the files.
"""

import argparse, datetime, matplotlib, matplotlib.pyplot as plt, os, signal
from csv import reader, writer
from multiprocessing import Pool, Value, cpu_count
from random import sample
from utils.utils import mkdir_clean, print_progress_bar

class Policy:
    def __init__(self, file, num_lists):
        self.file = file
        self.num_lists = num_lists
        self.avg_list_len = 0
        self.lists = []

def get_list_statistics(file):
    """
    For every policy, open ip the list.csv file.  Read the number of
    entries to get the number of lists per file, then count the number
    of \n characters per list entry to figure out how many items are in
    each list.  Get average of the items per list, report back.

    In:     list CSV file to read.
    Out:    Policy object to return to the Pool list at the end.
    """
    with open(parser_output_dir + file, "r") as fp:
        csv_reader = reader(fp)
        elements = list(csv_reader)
    
    policy_stats = Policy(file, len(elements))
    num_items = []
    for l in elements:
        content_string = l[4]
        policy_stats.lists.append(content_string)
        num_items.append(content_string.count("\n") + 1)
    policy_stats.avg_list_len = sum(num_items)/len(num_items)

    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(random_files), prefix = "Sentence Statistics Progress:", suffix = "Complete", length = 50)

    return policy_stats

def generate_boxplots(num_lists, avg_list_len, output_folder):
    """
    Generate 2 boxplots: one for the number of lists per policy, one
    for the average length of the lists in each policy.

    In:     number of lists per policy list, average list length list,
            output folder in which to save the visualization PNG.
    Out:    N/A
    """
    fig = plt.figure()
    box_num_lists = fig.add_subplot(121)
    box_num_lists.set_title("Number of Lists per Policy")
    box_num_lists.set_xlabel("")
    box_num_lists.set_ylabel("")
    box_num_lists.boxplot(num_lists)
    box_num_lists.set_xticklabels([str(len(num_lists)) + " files in sample"], fontdict=None, minor=False)
    box_avg_len = fig.add_subplot(122)
    box_avg_len.set_title("Average # of Elements per List per Policy")
    box_avg_len.set_xlabel("")
    box_avg_len.set_ylabel("")
    box_avg_len.boxplot(avg_list_len)
    box_avg_len.set_xticklabels([str(len(num_lists)) + " files in sample"], fontdict=None, minor=False)
    fig.tight_layout()
    fig.savefig(output_folder + "visualization.png")

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
    argparse = argparse.ArgumentParser(description="Get list statistics from Parser output.")
    argparse.add_argument(  "-n", "--num_samples",
                            type=int,
                            default=0,
                            required=False,
                            help="number of files this program should read from the directory.")
    argparse.add_argument(  "parser_output_dir",
                            help="directory containing html files to verify.")
    argparse.add_argument(  "-o", "--output_folder",
                            default="./list_stats_output" + timestamp + "/",
                            required=False,
                            help="directory to dump sentence stats output.  Will be created if does not exist.")
    args = argparse.parse_args()
    parser_output_dir = args.parser_output_dir
    output_folder = args.output_folder
    mkdir_clean(output_folder)

    files = [name for name in os.listdir(parser_output_dir) if name.endswith("lists.csv")]
    try:
        random_files = sample(files, args.num_samples)
    except ValueError:
        print("ValueError: args.num_samples > # files in parser_output_dir, defaulting to all files in that directory.")
        random_files = files
    if args.num_samples == 0:
        random_files = files

    index = Value("i",0)          # shared val, index of current parsed file
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    policy_list = pool.map(get_list_statistics, random_files)    # map keeps domain_list order
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    num_lists = [p.num_lists for p in policy_list]
    avg_list_len = [p.avg_list_len for p in policy_list]
    generate_boxplots(num_lists, avg_list_len, output_folder)
