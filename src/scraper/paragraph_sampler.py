#!/usr/bin/python3

"""
Privacy Policy Project
Randomly take one paragraph from a random place in 200 different files.
"""

import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
import random, datetime
import pandas
import numpy as np
from collections import Counter
from nltk.tokenize import sent_tokenize


class TextSampler:
    """ Gather one random line from N random files. """

    def __init__(self, input_folder, output_file, num_samples):
        """ Specify the files parsed and compare with text equivalents. """
        super(TextSampler, self).__init__()

        self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
        self.input_folder = input_folder
        self.output_file = output_file + self.timestamp
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

    # use this version of run to count words in sentences from paragraphs
    def run(self):
        files = [f for f in listdir(self.input_folder) if isfile(join(self.input_folder, f))]
        # files[:] = [file for file in files if any(sub in file for sub in 'paragraph')]
        paragraph_files = [file for file in files if "paragraph" in file]

        print("Sampling from " + str(len(paragraph_files)) + "files.")

        samples = random.sample(paragraph_files, self.num_samples)
        error_num = 0
        word_count = []
        for f in samples:
            try:
                lines = open(input_folder + f).read().splitlines()
            except EnvironmentError as e: # parent of IOError, OSError *and* WindowsError where available
                print("Error" + str(error_num) + str(e))
                error_num = error_num + 1
                continue
            random_paragraph = random.choice(lines)

            # use for sentence word count
            # random_sentences = sent_tokenize(random_paragraph)
            # for sentence in random_sentences:
            #     word_count.append(len(sentence.split()))
            #     with open(self.output_file, "a") as f:
            #         f.write(str(sentence) + "\n")
            # with open(self.output_file, "a") as f:
            #         f.write("\n")

            # use for paragraph word count
            word_count.append(len(random_paragraph.split()))
            # if len(random_paragraph.split()) > 5:
            with open(self.output_file, "a") as f:
                f.write(random_paragraph + "\n" + "\n" + "\n")

        plt.xlabel('Words per paragraph')
        # plt.xlabel('Words per sentence')
        plt.ylabel('frequency in sample')
        plt.hist(word_count, self.num_samples)
        plt.show()
            


if __name__ == '__main__':
    input_folder = "output/"
    output_file = "random_paragraphs.txt"

    sampler = TextSampler(input_folder, output_file, 200)
    sampler.run()