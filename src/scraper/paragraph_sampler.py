#!/usr/bin/python3

"""
Privacy Policy Project
Randomly take one paragraph from a random place in 200 different files.
"""


from os import listdir
from os.path import isfile, join
import random, datetime


class TextSampler:
    """ Gather one random line from N random files. """

    def __init__(self, input_folder, output_file, num_samples):
        """ Specify the files parsed and compare with text equivalents. """
        super(TextSampler, self).__init__()

        self.timestamp = '_{0:%Y%m%d-%H%M%S}'.format(datetime.datetime.now())
        self.input_folder = input_folder
        self.output_file = output_file + self.timestamp
        self.num_samples = num_samples

    def run(self):
        files = [f for f in listdir(self.input_folder) if isfile(join(self.input_folder, f))]
        # for f in files:
        #     if "paragraphs" not in f:
        #         files.remove(f)

        approved = ['paragraph']

        files[:] = [file for file in files if any(sub in file for sub in approved)]

        print("Sampling from " + str(len(files)) + "files.")

        samples = random.sample(files, self.num_samples)
        error_num = 0
        for f in samples:
            try:
                lines = open(input_folder + f).read().splitlines()
            except EnvironmentError as e: # parent of IOError, OSError *and* WindowsError where available
                print("Error" + str(error_num) + str(e))
                error_num = error_num + 1
                continue
            random_paragraph = random.choice(lines)
            with open(self.output_file, "a") as f:
                f.write(random_paragraph + "\n" + "\n")
            


if __name__ == '__main__':
    input_folder = "output/"
    output_file = "random_paragraphs.txt"

    sampler = TextSampler(input_folder, output_file, 200)
    sampler.run()