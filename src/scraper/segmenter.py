""" A Naive Segmenter to be run on stripped HTML. """
import os
import nltk
from nltk.tokenize import sent_tokenize


class NaiveSegmenter:
    """ Leverage sentence tokenizer on HTML stripped text. """

    def __init__(self, dataset, txt_files):
        """ Specify the files to be segmented.
        
        Param:  dataset - string to path of the dataset
                txt_files - list of files to use in the dataset
        Return: n/a
        """
        self.dataset = dataset
        self.txt_files = txt_files
        nltk.download("punkt")

    def run(self):
        """ Run the NaiveSegmenter.

        Param:  n/a
        Return: n/a
        """
        for fname in self.txt_files:
            fp = open(self.dataset + fname, "r")
            sentences = sent_tokenize(fp.read())
            fp.close()

            print("\n" + fname + ":")
            for s in sentences:
                print(s)


if __name__ == "__main__":
    dataset = "../../data/policies/text/"
    files = ["google_1.txt", "google_2.txt", "ebay_1.txt", "amazon_1.txt",
             "facebook_1.txt", "facebook_2.txt", "netflix_1.txt",
             "netflix_2.txt", "twitter_1.txt", "wikipedia_1.txt", "yahoo_1.txt",
             "yahoo_2.txt"]

    ns = NaiveSegmenter(dataset, files)
    ns.run()