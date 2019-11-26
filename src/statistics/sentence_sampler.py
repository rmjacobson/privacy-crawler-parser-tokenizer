#!/usr/bin/python3

"""
Privacy Policy Project
Has 2 capabilities: histograms of rule occurrences in random files, 
    takes more general sample over random sentences from random files 
    that gets percentage of parsing rule hits and histogram of length
    of sentences.
Outputs:
    hist_figs.png - image of histograms for the 6 "negative" rules.
    gen_sample.png - image of rule percentages and sentence lengths.
    date-time.txt - text file containing sampled sentences.
    date-time-failed - text file containing only failed sentences.
"""

import matplotlib.pyplot as plt
from os import listdir
from os.path import isfile, join
import random, datetime
import pandas, re
import numpy as np
from collections import Counter
from nltk.tokenize import sent_tokenize

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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

class TextSampler:
    """ Sample one random line from N random files. 
        OR
        Sample every sentence from N random files.
    """

    def __init__(self, input_folder, output_folder, num_samples):
        super(TextSampler, self).__init__()
        self.timestamp = '{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.output_file = output_folder + self.timestamp + '.txt'
        self.output_file_failed = output_folder + self.timestamp + '-failed.txt'
        self.num_samples = num_samples
        self.pattern_prefix_noise = re.compile("^(?:[a-zA-Z0-9]|[-](?=[^-]*$)){1,3}$\:*")
        self.pattern_uppercase_first = re.compile("[A-Z]")
        self.num_file_tries = 0
        self.error_count = 0
        self.rule_vals = {
            "SHORT"     : 0,
            "LONG"      : 0,
            "START_CAP" : 0,
            "END_PER"   : 0,
            "PRE_NOISE" : 0,
            "HEAD_FRAG" : 0,
            "GOOD"      : 0
        }

    def get_all_sentences_from_file(self, file):
        try:
            lines = open(input_folder + file).read().splitlines()
        except EnvironmentError as e: # parent of IOError, OSError *and* WindowsError where available
            print("Error cannot read file: " + file + ": " + str(self.error_count) + str(e))
            self.error_count = self.error_count + 1
            return "file_error"
        
        random_paragraph = random.choice(lines)
        random_sentences = sent_tokenize(random_paragraph)
        sentences = []

        for line in lines:
            sentences.extend(sent_tokenize(line.strip()))

        return sentences

    def get_random_sentence_from_file(self, file):
        try:
            lines = open(input_folder + file).read().splitlines()
        except EnvironmentError as e: # parent of IOError, OSError *and* WindowsError where available
            print("Error cannot read file: " + file + ": " + str(self.error_count) + str(e))
            self.error_count = self.error_count + 1
            return "file_error"
        
        random_paragraph = random.choice(lines)
        random_sentences = sent_tokenize(random_paragraph)

        try:
            sentence = random.choice(random_sentences).strip()
        except IndexError as e:
            print("Error cannot get sentences from " + file + ": " + str(self.error_count) + " " + str(e))
            self.error_count = self.error_count + 1
            return "sentence_error"

        return sentence

    # > 50% words start with a capital letter, usually when things
    # that are usually in <hX> tags are part of <p> tags.
    def is_header_fragment(self, sentence):
        words = sentence.split()
        ncaps = 0
        for word in words:
            caps = [l for l in word if l.isupper()]
            if len(caps) > 0:
                ncaps = ncaps + 1
        if (ncaps / len(words)) > 0.5:
            return True
        else:
            return False

    def update_rule_count(self, key, file, sentence, writeout):
        self.rule_vals[key] = self.rule_vals[key] + 1
        if writeout:
            if key == "GOOD":
                with open(self.output_file, "a") as fp:
                    fp.write("[FILE: " + file + "]\n" + 
                             sentence + "\n\n") 
            else:
                with open(self.output_file_failed, "a") as fp:
                    fp.write("[FILE: " + file + "]\n" + 
                             "[" + key + " -- DISCARDED]\n" + 
                             sentence + "\n\n")

    def generate_rule_hist_figs(self, rule_dict_list):
        fig = plt.figure(figsize=(20,10))

        result = [d['SHORT'] for d in rule_dict_list]
        short_fig = fig.add_subplot(321)
        short_fig.set_xlabel('SHORT Rule Hits per Policy')
        short_fig.set_ylabel('Number of Policies in Sample')
        short_fig.hist(result, self.num_samples)

        result = [d['LONG'] for d in rule_dict_list]
        long_fig = fig.add_subplot(322)
        long_fig.set_xlabel('LONG Rule Hits per Policy')
        long_fig.set_ylabel('Number of Policies in Sample')
        long_fig.hist(result, self.num_samples)

        result = [d['START_CAP'] for d in rule_dict_list]
        start_fig = fig.add_subplot(323)
        start_fig.set_xlabel('START_CAP Rule Hits per Policy')
        start_fig.set_ylabel('Number of Policies in Sample')
        start_fig.hist(result, self.num_samples)

        result = [d['END_PER'] for d in rule_dict_list]
        end_fig = fig.add_subplot(324)
        end_fig.set_xlabel('END_PER Rule Hits per Policy')
        end_fig.set_ylabel('Number of Policies in Sample')
        end_fig.hist(result, self.num_samples)

        result = [d['PRE_NOISE'] for d in rule_dict_list]
        pre_fig = fig.add_subplot(325)
        pre_fig.set_xlabel('PRE_NOISE Rule Hits per Policy')
        pre_fig.set_ylabel('Number of Policies in Sample')
        pre_fig.hist(result, self.num_samples)

        result = [d['HEAD_FRAG'] for d in rule_dict_list]
        head_fig = fig.add_subplot(326)
        head_fig.set_xlabel('HEAD_FRAG Rule Hits per Policy')
        head_fig.set_ylabel('Number of Policies in Sample')
        head_fig.hist(result, self.num_samples)

        fig.tight_layout()
        fig.savefig(self.output_folder + 'hist_figs.png')

    def apply_rules(self, file, sentence, writeout):
        num_words = len(sentence.split())
        if num_words < 5:
            # probably due to things like addresses or header fragments
            self.update_rule_count("SHORT", file, sentence, writeout)
        elif num_words > 85:
            # probably a run-on sentence that hasn't been properly parsed
            self.update_rule_count("LONG", file, sentence, writeout)
        elif not self.pattern_uppercase_first.match(sentence):
            # probably due to improperly scraped fragment (like from a div)
            # might be able to go back to these and re-parse
            self.update_rule_count("START_CAP", file, sentence, writeout)
        elif not sentence.endswith('.'):
            # usually the beginning of a list (and ends with ':')
            self.update_rule_count("END_PER", file, sentence, writeout)
        elif self.pattern_prefix_noise.match(sentence):
            # things like "1. " or "A: " that are more like headings in an outline
            # might be able to go back to these and re-parse
            self.update_rule_count("PRE_NOISE", file, sentence, writeout)
        elif self.is_header_fragment(sentence):
            # > 50% words start with a capital letter, usually when things
            # that are usually in <hX> tags are part of <p> tags.
            self.update_rule_count("HEAD_FRAG", file, sentence, writeout)
        else:
            self.update_rule_count("GOOD", file, sentence, writeout)


    def get_rule_histograms(self, random_files):
        rule_dict_list = []

        for i, file in enumerate(random_files, start=0):
            sentences = self.get_all_sentences_from_file(file)
            self.rule_vals.update({rule:0 for rule in self.rule_vals})
            for sentence in sentences:
                self.apply_rules(file, sentence, False)

            rule_dict_list.append(self.rule_vals.copy())
            printProgressBar(i + 1, len(random_files), prefix = 'Rule Histograms Progress:', suffix = 'Complete', length = 50)

        self.generate_rule_hist_figs(rule_dict_list)

    def get_general_sample(self, random_files):
        word_count = []
        for i, file in enumerate(random_files, start=0):
            sentence = self.get_random_sentence_from_file(file)
            if "e_error" in sentence:
                continue
            num_words = len(sentence.split())
            word_count.append(num_words)
            self.apply_rules(file, sentence, True)
            printProgressBar(i + 1, len(random_files), prefix = 'General Sample Progress:', suffix = 'Complete', length = 50)

        fig = plt.figure(figsize=(20,10))

        rule_percentages = [value * 100. / self.num_samples for value in self.rule_vals.values()]
        percentages_fig = fig.add_subplot(121)
        percentages_fig.set_title('%Rule Hits in ' + str(self.num_samples - self.error_count) + ' Samples')
        percentages_fig.bar(list(self.rule_vals.keys()), rule_percentages, color='b')

        word_len_fig = fig.add_subplot(122)
        word_len_fig.set_xlabel('Words per sentence')
        word_len_fig.set_ylabel('Frequency in sample')
        word_len_fig.hist(word_count, self.num_samples)

        fig.tight_layout()
        fig.savefig(self.output_folder + 'gen_sample.png')

    # do either general sample or get histograms
    def run(self):
        files = [f for f in listdir(self.input_folder) if isfile(join(self.input_folder, f))]
        paragraph_files = [file for file in files if "paragraph" in file]
        random_files = random.sample(paragraph_files, self.num_samples)
        print("Sampling " +  str(self.num_samples) + " times from " + str(len(paragraph_files)) + "files.")

        self.error_count = 0
        self.get_rule_histograms(random_files)

        # self.error_count = 0
        # self.rule_vals.update({rule:0 for rule in self.rule_vals})
        # self.get_general_sample(random_files)


if __name__ == '__main__':
    input_folder = "../scraper/output/"
    output_folder = "sentence_sampler_out/"

    sampler = TextSampler(input_folder, output_folder, 1000)
    sampler.run()
