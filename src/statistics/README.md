# Statistics Module

This module mainly contains support code for the Tokenizer to enable
sentence tokenization and classification, but also contains leftover
code used to gain understanding about how the parser would function
best.

All code relating to the Tokenizer is in the sentences.py file.  This
is the _*only*_ file that has been kept up-to-date as the project
structure has changed over the course of 2019-2020.  The remaining
files accomplish various tasks like getting the number of words in a
random selection of paragraphs, or counting the number of lists in a
random selection of files.  These files and this capability _*is not*_
kept up-to-date, and is not guaranteed to work by running the files
without modification.  This may be fixed at some point if work on the
Parser component resumes.

## Example Run of sentences.py
An example run with a sample size of 4 policies is shown below. Please
note that due to the nature of Python modules and the way modules are
linked in this project, this particular command _*must be run from the 
`src/` directory of this repository*_.
```
python -m statistics.sentences 4 ../data/inputs/rules.json ../data/parser_output/
```
## Example Run of lists.py
An example run with a sample size of 4 policies is shown below. Please
note that due to the nature of Python modules and the way modules are
linked in this project, this particular command _*must be run from the 
`src/` directory of this repository*_. Also note that the `-n` option
may be omitted from this command if you would like to set the sample
size to the entire Parser output.
```
python -m statistics.get_list_stats -n 4 ../data/parser_output/
```
