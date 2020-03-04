# Verification Module

This module contains support code for the Crawler to enable identifying
HTML documents that are _actually_ privacy policies as opposed to
documents that represent pages referencing the privacy policy or
similar defects of the crawlers search process.

Most verification capability is imported from this module to the
crawler.py script.  However, for the purpose of testing and further
development, this module is runnable as a standalone script.  By
passing in a cosine similarity threshold, a directory path for the
ground truth you want to test against, an english dictionary, and your
test dataset directory, you can review the cosine similarity scores for
every HTML document as well as a more curated list of documents that
are on the borderline of the threshold you specified.

## Example Run
An example run from the top-level directory with a cosine similarity
threshold of 0.6 is shown below.  Please note that due to the nature of
Python modules and the way modules are linked in this project, this
particular command _*must be run from the `src/` directory of this
repository*_.
```
python -m verification.verify 0.6 ../data/inputs/ground_truth_html/ ../data/inputs/dictionary.txt ../data/crawler_output/html/
```

