"""A Naive Segmenter to be run on stripped HTML."""
import os
import nltk
import random
import spacy
from deepsegment import DeepSegment
from spacy.pipeline import Sentencizer
from nltk.tokenize import sent_tokenize


class NaiveSegmenter:
    """Leverage sentence tokenizer on HTML stripped text."""

    def __init__(self, dataset, segment_dir, txt_files=None):
        """Specify the files to be segmented.
        Param:  dataset - string to path of the dataset
                segment_dir - writes all the segmentation results here
                txt_files - specific files to specify to be run against
        Return: n/a
        """
        self.dataset = dataset
        self.segment_dir = segment_dir
        self.txt_files = txt_files if txt_files != None else os.listdir(dataset)
        if not os.path.exists(self.segment_dir): os.makedirs(self.segment_dir)
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt")

    def run(self):
        """Segment all the text files."""
        for fname in self.txt_files:
            fp = open(self.dataset + fname, "r")
            sentences = sent_tokenize(fp.read())
            fp.close()

            fp = open(self.segment_dir + fname, "w")
            fp.write("\n".join(str(line) for line in sentences))
            fp.close()

    def run_spacy(self):
        """ """
        nlp = spacy.load("en_core_web_sm")
        for fname in self.txt_files:
            fp = open(self.dataset + fname, "r")
            doc = nlp(fp.read())
            fp.close()

            fp = open(self.segment_dir + fname, "w")
            for span in doc.sents:
                fp.write(str(span) + "\n")
            fp.close()

    def run_deepsegment(self):
        """ """
        segmenter = DeepSegment('en')
        for fname in self.txt_files:
            fp = open(self.dataset + fname, "r")
            sentences = segmenter.segment_long(fp.read())
            fp.close()

            fp = open(self.segment_dir + fname, "w")
            fp.write("\n".join(str(line) for line in sentences))
            fp.close()

    def sample(self, x=100):
        """Obtain a sample of these segments.
        Param:  x - the number of segments to sample
        Return: a list of all samples
        """
        population = []
        sample = []
        sample_indices = []

        # Gather all segments
        for fname in self.txt_files:
            fp = open(self.segment_dir + fname, "r")
            population.extend(fp.read().split("\n"))
            fp.close()

        # Simple random sampling of segments
        while len(sample) < x:
            idx = random.randint(0, len(population)-1)
            if idx not in sample_indices:
                sample.append(population[idx]) 
                sample_indices.append(idx)

        return sample


if __name__ == "__main__":
    dataset = "../../data/policies/text_top10/"
    segment_dir = "../../data/policies/text_top10_segmented/"
    files = ["google_1.txt", "google_2.txt", "ebay_1.txt", "amazon_1.txt",
             "facebook_1.txt", "facebook_2.txt", "netflix_1.txt",
             "netflix_2.txt", "twitter_1.txt", "wikipedia_1.txt", "yahoo_1.txt",
             "yahoo_2.txt"]

    ns = NaiveSegmenter(dataset, segment_dir, files)

    # Run segmenter
    ns.run()
    # ns.run_deepsegment()
    # ns.run_spacy()

    # Sample
    # sample = ns.sample(x=100)
    # for s in sample:
    #     print(s)