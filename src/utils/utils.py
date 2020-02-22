import requests

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
    if len(html_contents) == 0:
        html_contentsLettersPercentage = 0
    else:
        html_contentsLettersPercentage = float(numLetters) / len(html_contents) * 100
    lettersMatch = html_contentsLettersPercentage >= charPercentage
    return wordsMatch and lettersMatch

def request(url):
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
        # if "forbes" in url:
            # print(r.content)
    except (exceptions) as e:
        print("REQUEST PROBLEM: " + e)
        return ""
    return r.text
