import argparse, os, requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep

class VerifyJsonExtension(argparse.Action):
    """
    Checks the input file that it is actually a file with
    the .json extension.  Doesn't check to see if the file contains
    json content, but was the best we could do for the time being.
    https://stackoverflow.com/a/15203955
    """
    def __call__(self,parser,namespace,fname,option_string=None):
        file = os.path.isfile(fname)
        json = fname.endswith(".json")
        if file and json:
            setattr(namespace,self.dest,fname)
        else:
            parser.error("File doesn't end with '.json'")

def print_progress_bar (iteration, total, prefix = "", suffix = "", decimals = 1, length = 100, fill = "█", printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    https://stackoverflow.com/a/34325723
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
    bar = fill * filledLength + "-" * (length - filledLength)
    print("\r%s |%s| %s%% %s" % (prefix, bar, percent, suffix), end = printEnd)
    if iteration == total:  # Print New Line on Complete
        print()

def mkdir_clean(dir_path):
    """
    Given the name of the directory, create new fresh directories using this
    name. This may require deletion of all contents that previously existed in
    this directory, or creating a previously nonexistant directory.

    In:     dir_path - the name of the directory
    Out:    n/a
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    else:
        for f in os.listdir(dir_path):
            os.remove(os.path.join(dir_path, f))


def start_selenium():
    """
    Instatiate a selenium Chrome webdriver, return it.

    In:     n/a
    Out:    selenium headless webdriver
    """
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    return driver

def get_driver():
    """
    Instatiate a selenium Chrome webdriver, return it.

    In:     n/a
    Out:    selenium headless webdriver
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(chrome_options=options)
    return driver

def selenium_get(url):
    """
    requests library failed, so instantiate a full selenium web browser
    """
    ret = ""
    driver = get_driver()
    connection_attempts = 0
    while connection_attempts < 2:
        try:
            driver.get(base_url)
            if "privacy" in driver.page_source:
                ret = driver.page_source
            break
        except Exception as e:
            sleep(2)
            connection_attempts += 1
    driver.quit()
    if ret == "":
        print("\tselenium failed for " + url + " -> failed")
    return ret

# def request(url, driver):
def request(url):
    """
    Makes a simple HTTP request to the specified url and returns its
    contents. Note: the webdriver is started and closed in the file
    importing this function.

    In:     url - destination of http request
            driver - the web driver object used for headless browsers
            headless - boolean indicating whether we will use the headless
    Out:    content of the http request
    """
    exceptions = (requests.exceptions.ReadTimeout,
                  requests.exceptions.ConnectTimeout,
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
        requests_res = requests.get(url, headers=headers, timeout=(3,6))
        if not requests_res:
            print("requests failed for " + url + " -> trying selenium")
            return selenium_get(url)

            # selenium_res = ""
            # try:
            #     driver.get(url)
            #     selenium_res = driver.page_source
            # except Exception as e:
            #     return ""
            # return selenium_res
    except requests.exceptions.ConnectionError as e:
        if e.args[0].reason.errno == 61:
            print("REQUESTS connection refused for " + url + " -> trying selenium")
        if e.args[0].reason.errno == 60:
            print("REQUESTS connection timeout for " + url + " -> trying selenium")
        return selenium_get(url)
    except (exceptions) as e:
        print("REQUEST PROBLEM: " + str(e))
        return ""
    return requests_res.text
