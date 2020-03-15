"""
Privacy Policy Project
verify.py
Checks every file in list of given webpages is actually a privacy
policy.  Checks wether the text is majority english, then does 
cosine similarity from ground truth using TfidfVectorizer.
Currently seems like ~60% is the cutoff.
"""

import argparse, datetime, matplotlib, os, pandas as pd, re, signal
from multiprocessing import Pool, Value, cpu_count, Manager
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup, Comment, NavigableString
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.utils import mkdir_clean, print_progress_bar, request

def load_dictionary(dictionary):
    dictionaryFile = open(dictionary)
    ENGLISH_WORDS = {}
    for word in dictionaryFile.read().split("\n"):
        ENGLISH_WORDS[word] = None
        dictionaryFile.close()
    return ENGLISH_WORDS

def get_english_count(dictionary, html_contents):
    ENGLISH_WORDS = load_dictionary(dictionary)
    html_contents = html_contents.upper()
    html_contents = remove_nonletters(html_contents)
    possibleWords = html_contents.split()
    if possibleWords == []:
        return 0.0 # no words at all, so return 0.0
    matches = 0
    for word in possibleWords:
        if word in ENGLISH_WORDS:
            matches += 1
    return float(matches) / len(possibleWords)

def remove_nonletters(html_contents):
    UPPERLETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    LETTERS_AND_SPACE = UPPERLETTERS + UPPERLETTERS.lower() + " \t\n"
    lettersOnly = []
    for symbol in html_contents:
        if symbol in LETTERS_AND_SPACE:
            lettersOnly.append(symbol)
    return "".join(lettersOnly)

def is_english(dictionary, html_contents, wordPercentage=50, charPercentage=85):
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
    wordsMatch = get_english_count(dictionary, html_contents) * 100 >= wordPercentage
    numLetters = len(remove_nonletters(html_contents))
    if len(html_contents) == 0:
        html_contentsLettersPercentage = 0
    else:
        html_contentsLettersPercentage = float(numLetters) / len(html_contents) * 100
    lettersMatch = html_contentsLettersPercentage >= charPercentage
    return wordsMatch and lettersMatch

def remove_bad_tags(soup):
    """
    Removes script and style elements from the soup to ensure we don't
    look at these when we don't need to.

    In:     BeatifulSoup tree object.
    Out:    cleaned version of that BeatifulSoup tree object.
    """
    bad_tags = ["style", "script", "noscript", "head", "title", "meta", 
                "[document]", "img", "iframe", "header", "footer", "nav"]
    for tag in soup(bad_tags):
        tag.decompose()
    return soup

def strip_text(html):
    """
    This function takes in a html document represented as a string and
    removes all tags known to be irrelevant to the policy text, then
    returns all the visible text elements in a single string.

    In:     string containing html document bytes
    Out:    string containing text of visible policy text
    """
    if html == "":
        return ""   # return nothing if there is nothing
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        return ""   # if there's no soup, we don't care
    
    
    # Remove all script and style elements
    soup = remove_bad_tags(soup)

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

def get_ground_truth(ground_truth_html_dir):
    """
    This function builds one massive ground truth string containing
    the relevant text of all html documents in the ground truth
    corpus.  These policies have been reviewed by a human to verify
    they contain privacy policies.  The dataset has been expanded after
    various experiments showed policies on the edge of acceptable
    cosine similarity.

    In:     n/a, ground_truth_html_dir directory set in main
    Out:    string containing text of all ground truth policy html docs
    """
    ground_truth = ""
    for policy in os.listdir(ground_truth_html_dir):
        with open(ground_truth_html_dir + policy, "rb") as fp:
            html_contents = fp.read()
        html_contents = remove_company_names(strip_text(html_contents), policy[:-5]) + " "
        ground_truth += html_contents
    return ground_truth

def is_duplicate_policy(link_contents, domain, policy_dict):
    """
    Since the crawler does its work automatically, it is not immune
    to gathering duplicate policies (sometimes from different initial
    sources). This function will compare the current policy with the
    previously verified policies to see if it is a duplicate.
    """
    # digest = md5(link_contents.encode())
    # digest = digest.hexdigest()
    if link_contents in policy_dict:
        return True
    else:
        policy_dict[link_contents] = domain
        return False

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
    if not is_english(dictionary, html_contents):
        # print(policy + " is not english")
        return 0

    if is_duplicate_policy(html_contents, policy, policy_dict):
        # print("this is a duplicate policy")
        return -2
    
    # Create the Document Term Matrix and pandas dataframe
    # https://www.machinelearningplus.com/nlp/cosine-similarity/
    documents = [ground_truth, html_contents]
    vectorizer = TfidfVectorizer()
    sparse_matrix = vectorizer.fit_transform(documents)
    doc_term_matrix = sparse_matrix.todense()
    df = pd.DataFrame(doc_term_matrix, 
            columns=vectorizer.get_feature_names(),
            index=["ground_truth", "corp"])

    # calculate cosine similarity of the ground truth and the policy
    # sim[0,1] is the value we actually care about
    sim = cosine_similarity(df, df)
    
    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(files), prefix = "Verification Progress:", suffix = "Complete", length = 50)

    return sim[0,1]

def start_process(i):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global index
    index = i

if __name__ == '__main__':
    timestamp = "_{0:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
    argparse = argparse.ArgumentParser(description="Verify whether or not input HTML documents are privacy policies.")
    argparse.add_argument(  "cos_sim_threshold",
                            type=float,
                            help="minimum cosine similarity between html contents and ground truth vector to be considered a policy.")
    argparse.add_argument(  "ground_truth_html_dir",
                            help="directory containing html files of verification ground truth vector.")
    argparse.add_argument(  "dictionary",
                            help="txt file containing english-language dictionary.")
    argparse.add_argument(  "policies_html_dir",
                            help="directory containing html files to verify.")
    argparse.add_argument(  "-o", "--output_folder",
                            default="./verification_output" + timestamp + "/",
                            required=False,
                            help="directory to dump verification output.  Will be created if does not exist.")
    args = argparse.parse_args()
    cos_sim_threshold = args.cos_sim_threshold
    ground_truth_html_dir = args.ground_truth_html_dir
    dictionary = args.dictionary
    policies_html_dir = args.policies_html_dir
    output_folder = args.output_folder
    mkdir_clean(output_folder)

    # get ground truth in one string
    ground_truth = get_ground_truth(ground_truth_html_dir)
    files = [f for f in os.listdir(policies_html_dir) if os.path.isfile(os.path.join(policies_html_dir, f))]
    shared_manager = Manager()          # manages lists shared among child processes  
    policy_dict = shared_manager.dict() # hashmap of all texts to quickly detect duplicates
    
    index = Value("i",0)          # shared val, index of current parsed file
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    sim_list = pool.starmap(verify, [(file, ground_truth) for file in files])   # starmap keeps domain_list order
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    # Generate full similarity list & borderline similarity list
    print("Generating full similarity list & borderline similarity list...")
    files_sim_list = [(files[i], sim_list[i]) for i in range(0, len(files))]
    full_output_string = ""
    borderline_output_string = ""
    for file, score in files_sim_list:
        if score > (cos_sim_threshold - 0.05) and score < (cos_sim_threshold + 0.05):
            borderline_output_string += file + "score = " + str(round(score, 2)) + "\n"
        full_output_string += file + "score = " + str(round(score, 2)) + "\n"
    with open(output_folder + "borderline_scores.txt" ,"w") as fp:
        fp.write(borderline_output_string)
    with open(output_folder + "all_scores.txt" ,"w") as fp:
        fp.write(full_output_string)

    # Generate histogram and boxplot of verification
    # https://matplotlib.org/3.1.3/api/_as_gen/matplotlib.pyplot.subplot.html
    # https://matplotlib.org/3.1.1/tutorials/intermediate/tight_layout_guide.html
    print("Generating histogram and boxplot of verification...")
    fig = plt.figure()
    hist = fig.add_subplot(121)
    hist.set_title("Cosine Similarity Score Histogram")
    hist.set_xlabel("Cosine Similarity Score")
    hist.set_ylabel("Number of Policies per Score")
    hist.hist(sim_list, len(sim_list))
    box = fig.add_subplot(122)
    box.set_title("Cosine Similarity Score Boxplot")
    box.set_xlabel("")
    box.set_ylabel("Cosine Similarity Score")
    box.boxplot(sim_list)
    fig.tight_layout()
    fig.savefig(output_folder + "visualization.png")

    print("Done")
        