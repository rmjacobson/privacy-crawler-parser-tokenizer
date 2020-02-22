#!/usr/bin/python3

"""
Privacy Policy Project
Web Crawler
Takes in list of Amazon Alexa Top N sites, visits them and tries to
discover the link to and download the Privacy Policy HTML page for
that site.  Also attempts to visit links contained within the policies
to discover relevant linked content.  Outputs directory of HTML docs
containing privacy policies and a txt file containing an audit trail
of links visited and decisions about those policies.
"""

import argparse, json, os, pandas as pd, re, requests, signal, sys
import matplotlib
from multiprocessing import Pool, Lock, Value, cpu_count, current_process
# import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
sys.path.insert(0, '/Users/Ryan/Desktop/privacy_proj/Deep-NER/src/utils/')
from utils import isEnglish, print_progress_bar, request

# Instantiate Chrome Driver
# options = Options()
# options.headless = True
# driver = webdriver.Chrome(options=options)
PRIVACY_POLICY_KEYWORDS = ['privacy']

class VerifyJsonExtension(argparse.Action):
    """
    Checks the input domain list file that it is actually a file with
    the .json extension.  Doesn't check to see if the file contains
    json content, but was the best we could do for the time being.
    https://stackoverflow.com/a/15203955
    """
    def __call__(self,parser,namespace,fname,option_string=None):
        if fname.endswith(".json"):
            setattr(namespace,self.dest,fname)
        else:
            parser.error("File doesn't end with '.json'")

class CrawlReturn():
    def __init__(self, domain, access_success):
        self.domain = domain
        self.sim_avg = 0.0
        self.link_list = []
        self.access_success = access_success
    def add_link(self, link, sim_score, html_outfile, stripped_outfile, access_success):
        link_tuple = (link, sim_score, html_outfile, stripped_outfile, access_success)
        self.link_list.append(link_tuple)
        self.sim_avg = self.sim_avg + ((sim_score-self.sim_avg)/len(self.link_list))

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

def verify(html_contents, ground_truth):
    """
    This function will verify that the HTML we scraped is actually a privacy
    policy.  (For example, we need to reject HTML which turns out to be an
    article about privacy or a pointer to policies as opposed to a privacy policy.)
    We accomplish this by comparing against a ground truth.  We build our ground
    truth by constructing a bag of words from human-verified privacy policies.
    HTML which does not pass the verification process will be logged then
    deleted.

    In:     html_contents (aka stripped html text)
    Out:    cosine similarity score of ground truth and policy document
    """
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
    sim_score = cosine_similarity(df, df)

    # return sim_score[0,1] >= cos_sim_threshold
    return sim_score[0,1]

def find_policy_links(full_url, soup):
    """
    Find all the links on the page.  Only returns links which contain some case
    permutation of the PRIVACY_POLICY_KEYWORDS.  Exact duplicate links removed
    before return, but similar links or links that lead to the same place will
    be dealt with later in the process.

    In:     full_url - A string representing the full name of the URL
            soup - BeautifulSoup4 object instantiated with the HTML of the URL
    Out:    list of all links on the page
    """
    links = []
    for kw in PRIVACY_POLICY_KEYWORDS:
        all_links = soup.find_all("a")
        for link in all_links:
            if link.string and ("href" in link.attrs):
                if (kw in str(link.string).lower()) or (kw in str(link["href"]).lower()):
                    final_link = link["href"]

                    # Not a proper link
                    if "javascript" in final_link.lower(): continue
                    if len(final_link) < 3: continue

                    # This link is complete, add it to our list
                    if "http" in final_link:
                        links.append(final_link)
                        continue

                    # This link is incomplete. Complete it.
                    if final_link[0] != "/":
                        final_link = full_url + "/" + final_link
                    elif final_link[:2] == "//":
                        final_link = "http://" + final_link[2:]
                    else:
                        final_link = full_url + final_link
                    links.append(final_link)
    links = list(dict.fromkeys(links))  # remove obvious duplicates
    return links

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

def crawl(domain):
    full_url = domain if ("http" in domain) else "http://" + domain
    full_url = full_url if ("https://" in full_url) else full_url.replace("http://", "https://")
    # print("url = " + full_url)
    html = request(full_url)
    if html == "":
        print("got nothing for" + domain)
        # Update progress bar
        with index.get_lock():
            index.value += 1
            print_progress_bar(index.value, len(domain_list), prefix = 'Crawling Progress:', suffix = 'Complete', length = 50)
        return CrawlReturn(domain, False)
    
    # get links from the domain landing page
    # domain_soup = BeautifulSoup(markup=html, features='lxml')
    domain_soup = BeautifulSoup(html, "html.parser")
    links = find_policy_links(full_url, domain_soup)

    # go down the link rabbit hole to download the html and verrify that they are policies
    retobj = CrawlReturn(domain, True)
    for i, link in enumerate(links):
        link_html = request(link)
        link_contents = strip_text(link_html)
        if link_contents == "":
            retobj.add_link(link, 0.0, "N/A", "N/A", False)
            continue    # policy is empty, skip this whole thing
        sim_score = verify(link_contents, ground_truth)
        is_policy = sim_score >= cos_sim_threshold
        if is_policy:
            html_outfile = output_folder + domain + "_" + str(i) + ".html"
            with open(html_outfile, "a") as fp:
                fp.write(link_contents)
            stripped_outfile = output_folder + domain + "_" + str(i) + ".txt"
            with open(stripped_outfile, "a") as fp:
                fp.write(link_contents)
            retobj.add_link(link, sim_score, html_outfile, stripped_outfile, True)
        else:
            retobj.add_link(link, sim_score, "N/A", "N/A", True)

    # Update progress bar
    with index.get_lock():
        index.value += 1
        print_progress_bar(index.value, len(domain_list), prefix = 'Crawling Progress:', suffix = 'Complete', length = 50)

    return retobj

def produce_summary(all_links):
    """
    Produce string output for the summary file in the format of:
    domain.com
    => https://www.domain.com/path/to/policy.html

    In:     list CrawlerReturn objects containing links and statistics
    Out:    string representation to be written out to file.
    """
    successful_domains = sum(len(domain.link_list) != 0 for domain in all_links)
    access_fail_domains = sum(domain.access_success == False for domain in all_links)
    summary_string = "Summary of Crawler Output\n"
    summary_string += "Successful Domains = " + str(successful_domains) + "\n"
    summary_string += "No links found for " + str(len(all_links)-successful_domains) + "\n"
    summary_string += "Could not access " + str(access_fail_domains) + "\n"

    for domain in all_links:
        if len(domain.link_list) == 0:
            summary_string += (domain.domain + " -- NONE FOUND\n\n")
        else:
            sim_avg = str(round(domain.sim_avg, 2))
            summary_string += (domain.domain + " (avg sim = " + sim_avg + ")" + "\n")
            for link in domain.link_list:
                sim_score = str(round(link[1], 2))
                if link[4] == False:
                    summary_string += ("=> (Could not read link) " + link[0] + " -> " + link[2] + " & " + link[3] + "\n")
                else:
                    summary_string += ("=> (" + sim_score + ") " + link[0] + " -> " + link[2] + " & " + link[3] + "\n")
            summary_string += "\n"
    return summary_string


def start_process(i):
    """
    Set inter-process shared values to global so they can be accessed.
    Ignore SIGINT in child workers, will be handled to enable restart.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global index
    index = i

if __name__ == '__main__':
    argparse = argparse.ArgumentParser(description="Read in list of top sites.")
    argparse.add_argument(  "domain_list_file",
                            help="json file containing list of top N sites to visit.",
                            action=VerifyJsonExtension)
    argparse.add_argument(  "ground_truth_html_dir",
                            help="directory containing html files of verification ground truth vector.")
    argparse.add_argument(  "cos_sim_threshold",
                            type=float,
                            help="minimum cosine similarity between html contents and ground truth vector to be considered a policy.")
    argparse.add_argument(  "output_folder",
                            help="directory to dump output of crawler.")
    args = argparse.parse_args()
    domain_list_file = args.domain_list_file
    ground_truth_html_dir = args.ground_truth_html_dir
    cos_sim_threshold = args.cos_sim_threshold
    output_folder = args.output_folder

    # get domain list and verification ground truth
    with open(domain_list_file) as fp:
        domain_list = json.load(fp).values()
    ground_truth = get_ground_truth(ground_truth_html_dir)


    # start process pool
    index = Value('i',0)          # shared val, index of current crawled domain
    pool_size = cpu_count() * 2
    matplotlib.use('agg')   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    all_links = pool.map(crawl, domain_list)
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    print(produce_summary(all_links))
