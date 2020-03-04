# CMU INI MSIS Master's Project: Automated Privacy Policy Sentence Tokenization


## Running the Project
Please read the Virtual Environments section before trying to run this
project to save headaches.

The top-level scripts for this project's main components (crawler.py
and parser-tokenizer.py) can be run very simply, as shown in the two
examples below.
```
python crawler.py data/inputs/alexa.json data/inputs/ground_truth_html/ data/inputs/dictionary.txt 0.6 3 data/crawler_output/html/ data/crawler_output/stripped_text/

python parser-tokenizer.py data/crawler_output/html/ data/crawler_output/stripped_text/ data/parser_output/ data/tokenizer_output/
```
However, due to the limitations of Python's module importing rules,
some of the associated submodules must be run from inside the `src`
directory with the commands shown below.  Please read eachmodule's
README.md for more information.
```
python -m verification.verify 0.6 ../data/inputs/ground_truth_html/ ../data/inputs/dictionary.txt ../data/crawler_output/html/
```

# Virtual Environments
To set up your virtual environment, refer to
[this](https://docs.python-guide.org/dev/virtualenvs/#lower-level-virtualenv)
documentation.


To download all dependencies:
```
$ pip3 install -r requirements.txt
```


If you've downloaded any additional libraries, log those libraries to your
requirements.txt file by running the following:
```
$ pip freeze -l > requirements.txt
```

# Environment Notes
MacOS Catilina (10.15) and above have limited the user's default ability
to multithread.  If running these versions of the OS, need to add the
following line to ~/.bash_profile and reload the shell.
```
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```
Source: https://stackoverflow.com/questions/50168647/multiprocessing-causes-python-to-crash-and-gives-an-error-may-have-been-in-progr
