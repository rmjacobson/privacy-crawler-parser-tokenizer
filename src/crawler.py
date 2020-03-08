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

import argparse, datetime, json, matplotlib, os, pandas as pd, re, signal, sys
from bs4 import BeautifulSoup
from multiprocessing import Pool, Value, cpu_count, current_process, Manager
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.utils import print_progress_bar, request, start_selenium, VerifyJsonExtension
from verification.verify import get_ground_truth, is_duplicate_policy, is_english, mkdir_clean, strip_text

PRIVACY_POLICY_KEYWORDS = ["privacy"]

class DomainLink():
    def __init__(self, link, sim_score, html_outfile, stripped_outfile, access_success, valid, duplicate):
        self.link = link
        self.sim_score = sim_score
        self.html_outfile = html_outfile
        self.stripped_outfile = stripped_outfile
        self.access_success = access_success
        self.valid = valid
        self.duplicate = duplicate

class CrawlReturn():
    def __init__(self, domain, access_success):
        self.domain = domain
        self.sim_avg = 0.0
        self.link_list = []
        self.access_success = access_success
    def add_link(self, link, sim_score, html_outfile, stripped_outfile, access_success, valid, duplicate):
        link = DomainLink(link, sim_score, html_outfile, stripped_outfile, access_success, valid, duplicate)
        self.link_list.append(link)
        self.sim_avg = self.sim_avg + ((sim_score-self.sim_avg)/len(self.link_list))

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
    if not is_english(dictionary, html_contents):
        return 0
    
    # Create the Document Term Matrix and pandas dataframe
    # https://www.machinelearningplus.com/nlp/cosine-similarity/
    documents = [ground_truth, html_contents]
    count_vectorizer = TfidfVectorizer()
    sparse_matrix = count_vectorizer.fit_transform(documents)
    doc_term_matrix = sparse_matrix.todense()
    df = pd.DataFrame(doc_term_matrix, 
            columns=count_vectorizer.get_feature_names(),
            index=["ground_truth", "corp"])

    # calculate cosine similarity of the ground truth and the policy
    # sim[0,1] is the value we actually care about
    sim_score = cosine_similarity(df, df)

    # return sim_score[0,1] >= cos_sim_threshold
    return sim_score[0,1]

def clean_link(link):
    """
    Many links will direct you to a specific subheading of the page, or
    reference some particular component on the page.  We don't want to
    consider these "different" URLs, so parse this out.

    In:     string representiaton of a URL link.
    Out:    "cleaned" version of the link parameter.
    """
    link = link.split("#", 1)[0]
    # link = link.split("?", 1)[0]
    return link

def find_policy_links(full_url, html):
    """
    Find all the links on the page.  Only returns links which contain some case
    permutation of the PRIVACY_POLICY_KEYWORDS.  Exact duplicate links removed
    before return, but similar links or links that lead to the same place will
    be dealt with later in the process.

    In:     full_url - A string representing the full name of the URL
            soup - BeautifulSoup4 object instantiated with the HTML of the URL
    Out:    list of all links on the page
    """
    soup = BeautifulSoup(html, "html.parser")
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
                        # links.append(final_link)
                        links.append(clean_link(final_link))
                        continue

                    # This link is incomplete. Complete it.
                    if final_link[0] != "/":
                        final_link = full_url + "/" + final_link
                    elif final_link[:2] == "//":
                        final_link = "http://" + final_link[2:]
                    else:
                        final_link = full_url + final_link
                    # links.append(final_link)
                    links.append(clean_link(final_link))
    links = list(dict.fromkeys(links))  # remove obvious duplicates
    return links

def crawl(domain):
    """
    Primary function for the process pool.
    Crawl websites for links to privacy policies.  First check if
    the website can be reached at all, then find list of policy links
    on first page.  Then loop through links to see if the links are 
    valid policies.  Keep statistics in every subprocess for summary
    at end.

    In:     domain landing page string
    Out:    CrawlReturn obj containing links, statistics about links,
            output files, etc.
    """
    # first get the domain landing page via HTTPS
    full_url = domain if ("http" in domain) else "http://" + domain
    full_url = full_url if ("https://" in full_url) else full_url.replace("http://", "https://")
    domain_html = request(full_url, driver)
    if strip_text(domain_html) == "":
        failed_access_domain = CrawlReturn(domain, False)
        failed_access_domains.append(failed_access_domain)
        with index.get_lock():  # Update progress bar
            index.value += 1
            print_progress_bar(index.value, len(domain_list), prefix = "Crawling Progress:", suffix = "Complete", length = 50)
        return failed_access_domain

    # get links from domain landing page, return if none found
    links = find_policy_links(full_url, domain_html)
    if len(links) == 0:
        no_link_domain = CrawlReturn(domain, True)
        no_link_domains.append(no_link_domain)
        with index.get_lock():  # Update progress bar
            index.value += 1
            print_progress_bar(index.value, len(domain_list), prefix = "Crawling Progress:", suffix = "Complete", length = 50)
        return no_link_domain

    # go down the link rabbit hole to download the html and verify that they are policies
    retobj = CrawlReturn(domain, True)
    domain_successful_links = []
    domain_failed_links = []
    depth_count = 0
    output_count = 0
    for link in links:
        link_html = request(link, driver)
        link_contents = strip_text(link_html)
        
        # checl whether we could even see this policy
        if link_contents == "":
            domain_failed_links.append(link)
            retobj.add_link(link, 0.0, "N/A", "N/A", False, False, False)
            continue    # policy is empty, skip this whole thing
        
        # add links on this page to the list to be visited if they are new
        if depth_count < max_crawler_depth:
            depth_count += 1
            new_links = find_policy_links(full_url, link_html)
            for l in new_links:
                if l not in links:
                    links.append(l)
        
        # get similarity score, check against the score threshold to see if policy
        sim_score = verify(link_contents, ground_truth)
        is_policy = sim_score >= cos_sim_threshold

        # if this page is a policy, check duplicate then write out to file
        if is_policy:
            if is_duplicate_policy(link_contents, domain, policy_dict):
                retobj.add_link(link, 0.0, "N/A", "N/A", True, True, True)
                continue    # we've already seen this policy, skip
            domain_successful_links.append(link)
            output_count += 1
            html_outfile = html_outfolder + domain[:-4] + "_" + str(output_count) + ".html"
            with open(html_outfile, "a") as fp:
                fp.write(link_html)
            stripped_outfile = stripped_outfolder + domain[:-4] + "_" + str(output_count) + ".txt"
            with open(stripped_outfile, "a") as fp:
                fp.write(link_contents)
            retobj.add_link(link, sim_score, html_outfile, stripped_outfile, True, True, False)
        
        # this isn't a policy, so just add it to the stats and continue
        else:
            if is_duplicate_policy(link_contents, domain, policy_dict):
                retobj.add_link(link, 0.0, "N/A", "N/A", True, False, True)
                continue    # we've already seen this policy, skip
            domain_failed_links.append(link)
            retobj.add_link(link, sim_score, "N/A", "N/A", True, False, False)
    
    # check whether at least one link in the domain was successful
    successful_links.extend(domain_successful_links)
    failed_links.extend(domain_failed_links)
    if sum(link.valid == True for link in retobj.link_list) == 0:
        failed_link_domains.append(retobj)
    else:
        successful_domains.append(retobj)

    with index.get_lock():  # Update progress bar
        index.value += 1
        print_progress_bar(index.value, len(domain_list), prefix = "Crawling Progress:", suffix = "Complete", length = 50)
    return retobj

def produce_summary(all_links):
    """
    Produce string output for the summary file in the format of:
    domain.com (avg sim score = 0.XX)
    => (link message) https://www.domain.com/path/to/policy.html

    In:     list CrawlerReturn objects containing links and statistics
    Out:    string representation to be written out to file.
    """
    timestamp = "_{0:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
    summary_string = "Summary of Crawler Output (" + timestamp + ")\n"
    summary_string += "   # of Successful Domains = " + str(len(successful_domains)) + " (" + str(round(len(successful_domains)/len(domain_list)*100, 2)) + "%).\n"
    summary_string += "   Could not access " + str(len(failed_access_domains)) + " (" + str(round(len(failed_access_domains)/len(domain_list)*100, 2)) + "%) domains.\n"
    summary_string += "   No links found for " + str(len(no_link_domains)) + " (" + str(round(len(no_link_domains)/len(domain_list)*100, 2)) + "%) domains.\n"
    summary_string += "   No valid links found for " + str(len(failed_link_domains)) + " (" + str(round(len(failed_link_domains)/len(domain_list)*100, 2)) + "%) domains.\n"
    summary_string += "   # of successful links = " + str(len(successful_links)) + ".\n"
    summary_string += "   # of failed links = " + str(len(failed_links)) + ".\n"
    summary_string += "\n"
    
    for domain in all_links:
        if not domain.access_success:
            failed_access_domains.append(domain)
            continue;
        if not domain.access_success:
            summary_string += (domain.domain + " -- NO_ACCESS\n\n")
        if domain.access_success and len(domain.link_list) == 0:
            summary_string += (domain.domain + " -- NO_LINKS\n\n")
        else:
            sim_avg = str(round(domain.sim_avg, 2))
            summary_string += (domain.domain + " (avg sim = " + sim_avg + ")" + "\n")
            for link in domain.link_list:
                sim_score = str(round(link.sim_score, 2))
                if link.access_success == False:
                    summary_string += ("=> (NO_ACCESS) " + link.link + " -> ")
                elif link.duplicate == True:
                    summary_string += ("=> (DUPLICATE) " + link.link + " -> ")
                else:
                    summary_string += ("=> (" + sim_score + ") " + link.link + " -> ")
                summary_string += (link.html_outfile + " & " + link.stripped_outfile + "\n")
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
    argparse = argparse.ArgumentParser(description="Crawls provided domains to gather privacy policy html files.")
    argparse.add_argument(  "-n", "--num_domains",
                            type=int,
                            default=-1,
                            required=False,
                            help="number of domains to crawl.  If blank, set to entire input list.")
    argparse.add_argument(  "domain_list_file",
                            help="json file containing list of top N sites to visit.",
                            action=VerifyJsonExtension)
    argparse.add_argument(  "ground_truth_html_dir",
                            help="directory containing html files of verification ground truth vector.")
    argparse.add_argument(  "dictionary",
                            help="txt file containing english-language dictionary.")
    argparse.add_argument(  "cos_sim_threshold",
                            type=float,
                            help="minimum cosine similarity between html contents and ground truth vector to be considered a policy.")
    argparse.add_argument(  "max_crawler_depth",
                            type = int,
                            help="number of layers to repeat find_policy_links for each domain.")
    argparse.add_argument(  "html_outfolder",
                            help="directory to dump HTML output of crawler.")
    argparse.add_argument(  "stripped_outfolder",
                            help="directory to dump stripped text output of crawler.")
    args = argparse.parse_args()
    domain_list_file = args.domain_list_file
    ground_truth_html_dir = args.ground_truth_html_dir
    dictionary = args.dictionary
    cos_sim_threshold = args.cos_sim_threshold
    max_crawler_depth = args.max_crawler_depth
    # output_folder = args.output_folder
    html_outfolder = args.html_outfolder
    stripped_outfolder = args.stripped_outfolder
    mkdir_clean(html_outfolder)
    mkdir_clean(stripped_outfolder)
    summary_outfile = args.html_outfolder + "../summary.txt"
    # get domain list and verification ground truth
    with open(domain_list_file, "r") as fp:
        domain_list = list(json.load(fp).values())
    if args.num_domains != -1:
        domain_list = domain_list[:args.num_domains]
    ground_truth = get_ground_truth(ground_truth_html_dir)

    # set up shared resources for subprocesses
    index = Value("i",0)        # shared val, index of current crawled domain
    shared_manager = Manager()    # manages lists shared among child processes
    successful_links = shared_manager.list()       # links that contain valid policies
    failed_links = shared_manager.list()           # either couldn't parse or couldn't visit link
    successful_domains = shared_manager.list()     # at least one link in each domain is a valid policy
    no_link_domains = shared_manager.list()        # domains with no links
    failed_link_domains = shared_manager.list()    # domains with no valid links
    failed_access_domains = shared_manager.list()  # domains where the initial access failed
    policy_dict = shared_manager.dict()            # hashmap of all texts to quickly detect duplicates
    driver = start_selenium()

    # start process pool
    pool_size = cpu_count() * 2
    matplotlib.use("agg")   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    all_links = pool.map(crawl, domain_list)    # map keeps domain_list order
    pool.close()  # no more tasks
    pool.join()   # merge all child processes
    driver.close()  # close headless selenium browser

    # produce summary output files
    print("Generating summary information...")
    with open(summary_outfile, "w") as fp:
        fp.write(produce_summary(all_links))
    # might want to add more summary files later
    print("Done")
    # print(policy_dict)
