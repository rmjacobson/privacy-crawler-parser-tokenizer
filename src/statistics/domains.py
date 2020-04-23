#!/usr/bin/python3

"""
Privacy Policy Project
Domain Statistics
Read all the HTML output of the parser to see how many files from each
domain were parsed.
"""

import argparse, datetime, matplotlib, matplotlib.pyplot as plt, os
from utils.utils import mkdir_clean

def count_list_freq(l): 
    """
    Find the frequency of elements in a list
    """
    freq = {}
    for items in l:
        freq[items] = l.count(items)
    return freq

def generate_domain_hist(files, outfile):
    # plt.bar(list(files.keys()), files.values(), width=.5)
    # plt.xticks(range(len(files)), list(files.keys()), rotation=30, fontsize=8)
    plt.hist(files.values(), bins=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 50], rwidth=0.5)
    plt.xlabel("# of Links from Domain")
    plt.ylabel("# of Domains")
    plt.savefig(outfile)

if __name__ == '__main__':
    timestamp = "_{0:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
    argparse = argparse.ArgumentParser(description="Get domain statistics from Crawler output.")
    argparse.add_argument(  "crawler_output_dir",
                            help="directory containing html files to count.")
    argparse.add_argument(  "-o", "--output_folder",
                            default="./domain_stats_output" + timestamp + "/",
                            required=False,
                            help="directory to dump sentence stats output.  Will be created if does not exist.")
    args = argparse.parse_args()
    mkdir_clean(args.output_folder)

    files = [name for name in os.listdir(args.crawler_output_dir) if name.endswith(".html")]
    shortened_files = [i.split("_", 1)[0] for i in files]
    generate_domain_hist(count_list_freq(shortened_files), args.output_folder + "domain_hist.pdf")
