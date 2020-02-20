#!/usr/bin/python3

"""
Privacy Policy Project
verify.py
Checks every file in list of given webpages is actually a privacy
policy.  Checks wether the text is majority english, then does 
cosine similarity from ground truth using TfidfVectorizer.
Currently seems like ~60% is the cutoff.
"""

import os, re, signal, matplotlib
import pandas as pd
from multiprocessing import Pool, Lock, Value, cpu_count, current_process
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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

def loadDictionary():
    dictionaryFile = open('../utils/dictionary.txt')
    ENGLISH_WORDS = {}
    for word in dictionaryFile.read().split('\n'):
        ENGLISH_WORDS[word] = None
        dictionaryFile.close()
    return ENGLISH_WORDS

def getEnglishCount(html_contents):
    ENGLISH_WORDS = loadDictionary()
    html_contents = html_contents.upper()
    html_contents = removeNonLetters(html_contents)
    possibleWords = html_contents.split()
    if possibleWords == []:
        return 0.0 # no words at all, so return 0.0
    matches = 0
    for word in possibleWords:
        if word in ENGLISH_WORDS:
            matches += 1
    return float(matches) / len(possibleWords)

def removeNonLetters(html_contents):
    UPPERLETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    LETTERS_AND_SPACE = UPPERLETTERS + UPPERLETTERS.lower() + ' \t\n'
    lettersOnly = []
    for symbol in html_contents:
        if symbol in LETTERS_AND_SPACE:
            lettersOnly.append(symbol)
    return "".join(lettersOnly)

def isEnglish(html_contents, wordPercentage=50, charPercentage=85):
    """
    Some policies in the crawl won't be english-language because
    privacy policies are often written in multiple languages.  None
    of those should have a high similarity score, but this method of
    flagging foreign language documents is faster than the full cosine
    similarity score, so remove these first.  By default, 50% of the
    words in the document should be in the english dictionary, and 85%
    of the characters should be letters rather than numbers or symbols.

    In:     string representaiton of the text to be verified as english
    Out:    boolean of whether the text is mostly english
    """
    wordsMatch = getEnglishCount(html_contents) * 100 >= wordPercentage
    numLetters = len(removeNonLetters(html_contents))
    html_contentsLettersPercentage = float(numLetters) / len(html_contents) * 100
    lettersMatch = html_contentsLettersPercentage >= charPercentage
    return wordsMatch and lettersMatch

def strip_text(html):
    """
    This function takes in a html document represented as a string and
    removes all tags known to be irrelevant to the policy text.

    In:     string containing html document bytes
    Out:    string containing text of visible policy text
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove all script and style elements
    bad_tags = ["style", "script", "noscript", "head", "title", "meta", 
                "[document]", "img", "iframe", "header", "footer", "nav"]
    for ignored_tag in soup(bad_tags):
        ignored_tag.decompose()

    return " ".join([text for text in soup.stripped_strings])

def remove_company_names(html_contents, name):
    """
    All policies reference their own company/organization names and
    specific service names or collaborator names that only that
    particular organization mentiions in their policy.  If these
    names are referenced often enough, they can skew similarity
    scores.  TfidfVectorizer attempts to balance this out by
    comparing word frequency with document frequency, but this
    is still a good effort to expand upon.

    In:     string representation of the extracted html contents
    Out:    string representation without specific org names
    """
    html_contents = re.sub(name, " ", html_contents, flags=re.IGNORECASE)
    return html_contents

def get_ground_truth():
    """
    This function builds one massive ground truth string containing
    the relevant text of all html documents in the ground truth
    corpus.  These policies have been reviewed by a human to verify
    they contain privacy policies.  The dataset has been expanded after
    various experiments showed policies on the edge of acceptable
    cosine similarity.

    In:     n/a, ground_truth_html directory set in main
    Out:    string containing text of all ground truth policy html docs
    """
    ground_truth = ""
    for policy in os.listdir(ground_truth_html):
        with open(ground_truth_html + policy, "rb") as fp:
            html_contents = fp.read()
        html_contents = remove_company_names(strip_text(html_contents), policy[:-5]) + " "
        ground_truth += html_contents
    return ground_truth

def clean_text(text):
    """
    This function removes unnecessary characters and lemmatizes the corpus
    In:     l - list with privacy policy
            col_name - the desired column name of the output dataframe
    Out:    pandas dataframe of cleaned privacy policy
    """
    l2 = []
    stop_words = set(stopwords.words("english"))
    # for i in l:
    # Removal of unnecessary characters
    text = re.sub("[^a-zA-Z]", " ", text)  # Remove punctuations
    text = text.lower()  # Convert to lowercase
    text = re.sub("&lt;/?.*?&gt;"," &lt;&gt; ", text)  # Remove <> tags
    text = re.sub("(\\d|\\W)+"," ",text)  # Remove special characters and digits
    # text = text.split()  # Convert to list from string

    # Lemmatization
    # lem = WordNetLemmatizer()  # Lemmatizer
    # text = [lem.lemmatize(word) for word in text if not word in stop_words]
    # text = " ".join(text)
    # l2.append(text)

    # Place the l2 back into a dataframe
    return text

def verify(policy, ground_truth):
    """
    This function will verify that the HTML we scraped is actually a privacy
    policy.  (For example, we need to reject HTML which turns out to be an
    article about privacy or a pointer to policies as opposed to a privacy policy.)
    We accomplish this by comparing against a ground truth.  We build our ground
    truth by constructing a bag of words from human-verified privacy policies.
    HTML which does not pass the verification process will be logged then
    deleted.

    In:     policy filename
    Out:    cosine similarity score of ground truth and policy document
    """
    if policy == ".DS_Store":
        return 0
    
    with open(policies_html_dir + policy, "r") as fp:
        html_contents = fp.read()
    html_contents = remove_company_names(strip_text(html_contents), policy[:-5]) + " "
    
    # verify majority of the contents are english-language, discard if not
    if not isEnglish(html_contents):
        print(policy + " is not english")
        return 0
    
    # Create the Document Term Matrix and pandas dataframe
    # https://www.machinelearningplus.com/nlp/cosine-similarity/
    documents = [ground_truth, html_contents]
    count_vectorizer = TfidfVectorizer()
    sparse_matrix = count_vectorizer.fit_transform(documents)
    doc_term_matrix = sparse_matrix.todense()
    df = pd.DataFrame(doc_term_matrix, 
            columns=count_vectorizer.get_feature_names(),
            index=['ground_truth', 'corp'])

    # calculate cosine similarity of the ground truth and the policy
    # sim[0,1] is the value we actually care about
    sim = cosine_similarity(df, df)
    if sim[0,1] > 0.5 and sim[0,1] < 0.6:
        print(policy + " score = " + str(sim[0,1]))
    
    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(files), prefix = 'Parsing Progress:', suffix = 'Complete', length = 50)

    return sim[0,1]

def detect_duplicates():
    """
    Since the crawler does its work automatically, it is not immune
    to gathering duplicate policies (sometimes from different initial
    sources). This function will compare the current policy with the
    previously verified policies to see if it is a duplicate.

    NOTE: NEED TO FIGURE OUT HOW TO WRITE THIS.  HASH TABLE WOULD BE
    USEFUL IF WE COULD GUARANTEE THAT THE TEXT WOULD BE EXACTLY THE SAME...
    """

def start_process(i):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global index
    index = i

if __name__ == '__main__':
    ground_truth_html = "./ground_truth_html/"
    policies_html_dir = "../../data/policies/html/"
    test_set = "./test_set/"

    # get ground truth in one string
    ground_truth = get_ground_truth()
    files = [f for f in os.listdir(policies_html_dir) if os.path.isfile(os.path.join(policies_html_dir, f))]
    
    index = Value("i",0)          # shared val, index of current parsed file
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    sim_list = pool.starmap(verify, [(file, ground_truth) for file in files])
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    # plt.hist(sim_list, len(sim_list))
    # plt.title('Similarity Scores')
    # plt.show()

    fig = plt.figure(1, figsize=(9, 6))
    ax = fig.add_subplot(111)
    bp = ax.boxplot(sim_list)
    fig.savefig("boxplot.png", bbox_inches="tight")
        