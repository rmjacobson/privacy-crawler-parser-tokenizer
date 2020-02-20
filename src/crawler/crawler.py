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

import argparse, json, requests, signal
# from os import path
from multiprocessing import Pool, Lock, Value, cpu_count, current_process
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Instantiate Chrome Driver
options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)
PRIVACY_POLICY_KEYWORDS = ['privacy']

def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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

def request(url, driver, headless=True):
    """
    Makes a simple HTTP request to the specified url, and returns its contents

    In:     url - destination of http request
            driver - the web driver object used for headless browsers
            headless - boolean indicating whether we will use the headless
    Out:    content of the http request
    """
    exceptions = (requests.exceptions.ReadTimeout,
                  requests.ConnectionError,
                  requests.ConnectTimeout,
                  ConnectionError,
                  ConnectionAbortedError,
                  ConnectionResetError)
    try:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:73.0) Gecko/20100101 Firefox/73.0"
        accept = "*/*"
        accept_language = "en-US,en;q=0.5"
        accept_encoding = "gzip, deflate"
        dnt = "1"
        up_insecure_reqs = "1"
        headers = {
            "User-Agent": user_agent,
            "Upgrade-Insecure-Requests": up_insecure_reqs,
            "DNT": dnt,"Accept": accept,
            "Accept-Language": accept_language,
            "Accept-Encoding": accept_encoding
        }
        r = requests.get(url, headers=headers)
    except (exceptions) as e:
        print("PROBLEM2")
        return ""
    return r.content

def find_policy_links(full_url, soup):
    """
    Find all the links on the page.  Only returns links which contain some case
    permutation of the PRIVACY_POLICY_KEYWORDS.

    TODO:
    - Remove all duplicates in this list

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
    return links

def crawl(domain):
    full_url = domain if ("http" in domain) else "http://" + domain
    full_url = full_url if ("https://" in full_url) else full_url.replace("http://", "https://")
    print("url = " + full_url)
    # html = request(full_url, driver, headless=options.headless)
    html = request(full_url, driver, headless=False)
    if html == "":
        print("got nothing for" + domain)
        return []
    # soup = BeautifulSoup(html, "html.parser")
    soup = BeautifulSoup(markup=html, features='lxml')
    links = find_policy_links(full_url, soup)
    links = list(dict.fromkeys(links))  # remove obvious duplicates
    # for link in links:
        # add log of link to final file output for this whole thing.
    links.insert(0, domain)
    return links

def produce_summary(all_links):
    summary_string = ""
    for link_list in all_links:
        if len(link_list) == 1:
            summary_string += (link_list[0] + " -- NONE FOUND\n\n")
        else:
            summary_string += (link_list[0] + "\n")
            for link in link_list[1:]:
                summary_string += ("=> " + link + "\n")
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
    args = argparse.parse_args()

    domain_list_file = args.domain_list_file
    # domain_list = []
    with open(domain_list_file) as fp:
        domain_list = json.load(fp).values()

    # print(domain_list)
    index = Value('i',0)          # shared val, index of current crawled domain
    pool_size = cpu_count() * 2
    # matplotlib.use('agg')   # don't know why this works, but allows matplotlib to execute in child procs
    pool = Pool(
        processes=pool_size,
        initializer=start_process,
        initargs=[index]
    )
    all_links = pool.map(crawl, domain_list)
    pool.close()  # no more tasks
    pool.join()   # merge all child processes

    print(produce_summary(all_links))
