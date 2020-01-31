#!/usr/bin/python3

"""
Privacy Policy Project
List Statistics
Randomly samples policy list output files to get the number of
lists per file.  Outputs # of lists per polciy, average # of
lists, biggest number of lists.
"""

import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
import random, datetime
import pandas, statistics
import numpy as np
from collections import Counter
from nltk.tokenize import sent_tokenize

class TextSampler:
    """Check one list file from N random website links"""

    def __init__(self, input_folder, output_file, num_samples):
        """ Specify the files parsed and compare with text equivalents. """
        super(TextSampler, self).__init__()

        self.timestamp = '{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
        self.input_folder = input_folder
        self.output_file = output_file + self.timestamp + '.txt'
        self.num_samples = num_samples

    def count_elements(self, seq) -> dict:
        """Tally elements from `seq`."""
        hist = {}
        for i in seq:
            hist[i] = hist.get(i, 0) + 1
        return hist

    def ascii_histogram(self, seq) -> None:
        """A horizontal frequency-table/histogram plot."""
        counted = count_elements(seq)
        for k in sorted(counted):
            print('{0:5d} {1}'.format(k, '+' * counted[k]))

    def Nmaxelements(self, orig_list, n): 
	    final_list = []
	    for i in range(0, n):  
	        max1 = 0
	        for j in range(len(orig_list)):      
	            if orig_list[j] > max1: 
	                max1 = orig_list[j]
	        orig_list.remove(max1); 
	        final_list.append(max1) 
	          
	    return final_list

    # count words in sentences from paragraphs
    def run(self):
        files = [f for f in listdir(self.input_folder) if isfile(join(self.input_folder, f))]
        list_files = [file for file in files if "list" in file]

        print("Sampling from " + str(len(list_files)) + "files.")

        samples = random.sample(list_files, self.num_samples)
        error_num = 0
        # word_count = []
        list_count = 0
        list_count_list = []
        for f in samples:
            try:
                lines = open(input_folder + f).read().splitlines()
                for l in lines:
                	if l == "":
                		list_count = list_count + 1
                print(f + " has " + str(list_count) + " lists")
                list_count_list.append(list_count)
            except EnvironmentError as e: # parent of IOError, OSError *and* WindowsError where available
                print("Error" + str(error_num) + str(e))
                error_num = error_num + 1
                continue
            list_count = 0

        print("\n\nMean number of lists = " + str(sum(list_count_list)/len(list_count_list)))
        print("Median number of lists = " + str(statistics.median(list_count_list)))
        print("Biggest 5 lists length = " + str(self.Nmaxelements(list_count_list, 5)))
            # random_paragraph = random.choice(lines)

            # # use for sentence word count
            # random_sentences = sent_tokenize(random_paragraph)
            # for sentence in random_sentences:
            #     word_count.append(len(sentence.split()))
            #     with open(self.output_file, "a") as f:
            #         f.write(str(sentence) + "\n")
            # with open(self.output_file, "a") as f:
            #         f.write("\n")

        # plt.xlabel('Words per sentence')
        # plt.ylabel('frequency in sample')
        # plt.hist(word_count, self.num_samples)
        # plt.show()


if __name__ == '__main__':
    input_folder = "../scraper/output/"
    output_file = "sentence_sampler_out/"

    sampler = TextSampler(input_folder, output_file, 200)
    sampler.run()