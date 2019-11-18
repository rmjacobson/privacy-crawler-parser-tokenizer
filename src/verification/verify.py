#!/usr/bin/python3

"""
Privacy Policy Project
verify.py
Checks every file in list of given webpages (in form of scraped 
text files) is actually a privacy policy.  Checks wether the text
is majority english, does cosine similarity from ground truth.

"""


def verify():
    '''
    This function will verify that the HTML we scraped is actually a privacy
    policy.  (For example, we need to reject HTML which turns out to be an
    article about privacy as opposed to a privacy policy.)
    We accomplish this by comparing against a ground truth.  We build our ground
    truth by constructing a bag of words from human-verified privacy policies.
    HTML which does not pass the verification process will be logged then
    deleted.
    '''
    import os
    import re
    import pandas as pd
    from nltk.corpus import stopwords
    from nltk.stem.porter import PorterStemmer
    from nltk.tokenize import RegexpTokenizer
    from nltk.stem.wordnet import WordNetLemmatizer
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    DATA = '../../data/policies/text_redo'
    GROUND_TRUTH = './policies_ground_truth'
    TEST = './policies_test'
    SIMILARITY = 0.3
    not_a_privacy_policy = []

    UPPERLETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    LETTERS_AND_SPACE = UPPERLETTERS + UPPERLETTERS.lower() + ' \t\n'
    filler_sentences = "This is a sentence. This is a sentence. This is a sentence. This is a sentence. This is a sentence. This is a sentence."

    def loadDictionary(self):
         dictionaryFile = open('dictionary.txt')
         englishWords = {}
         for word in dictionaryFile.read().split('\n'):
             englishWords[word] = None
             dictionaryFile.close()
         return englishWords

    def getEnglishCount(self, message):
     message = message.upper()
     message = self.removeNonLetters(message)
     possibleWords = message.split()
     if possibleWords == []:
         return 0.0 # no words at all, so return 0.0
     matches = 0
     for word in possibleWords:
         if word in self.ENGLISH_WORDS:
             matches += 1
     return float(matches) / len(possibleWords)

    def removeNonLetters(self, message):
     lettersOnly = []
     for symbol in message:
         if symbol in self.LETTERS_AND_SPACE:
             lettersOnly.append(symbol)
     return ''.join(lettersOnly)

    def isEnglish(self, message, wordPercentage=20, letterPercentage=85):
     # By default, 20% of the words must exist in the dictionary file, and
     # 85% of all the characters in the message must be letters or spaces
     # (not punctuation or numbers).
     wordsMatch = self.getEnglishCount(message) * 100 >= wordPercentage
     numLetters = len(self.removeNonLetters(message))
     messageLettersPercentage = float(numLetters) / len(message) * 100
     lettersMatch = messageLettersPercentage >= letterPercentage
     return wordsMatch and lettersMatch

    def get_ground_truth_vector():
        '''
        This function obtains a vector containing the ground truth privacy
        policies.
        In:     n/a
        Out:    pandas dataframe of all privacy policy text in a single cell
        '''
        # GROUND_TRUTH = './policies_ground_truth'

        # Collect all the policies to a single string
        policy_paths = []
        policies = ''
        l = []
        for root, _, files in os.walk(GROUND_TRUTH):
            for name in files:
                policy_paths.append(os.path.join(root, name))
        for policy in policy_paths:
            if 'policy_links.txt' in policy: continue
            if '.DS_Store' in policy: continue
            f = open(policy, 'r')
            policies += (f.read() + ' ')
            f.close()
        l.append(policies)

        return(pd.DataFrame(l, columns=['ground_truth']))

    def clean_text(df, col_name):
        '''
        This function removes unnecessary characters and lemmatizes the corpus
        In:     df - pandas dataframe with privacy policy
                col_name - the desired column name of the output dataframe
        Out:    pandas dataframe of cleaned privacy policy
        '''
        corpus = []
        stop_words = set(stopwords.words('english'))
        for i in range(0, len(df.index)):
            # Removal of unnecessary characters
            text = re.sub('[^a-zA-Z]', ' ', df[col_name][i])  # Remove punctuations
            text = text.lower()  # Convert to lowercase
            text = re.sub('&lt;/?.*?&gt;',' &lt;&gt; ', text)  # Remove <> tags
            text = re.sub('(\\d|\\W)+',' ',text)  # Remove special characters and digits
            text = text.split()  # Convert to list from string

            # Lemmatization
            lem = WordNetLemmatizer()  # Lemmatizer
            text = [lem.lemmatize(word) for word in text if not word in stop_words]
            text = ' '.join(text)
            corpus.append(text)

        # Place the corpus back into a dataframe
        return (pd.DataFrame(corpus, columns=[col_name]))

    def check_intersection(df_gt, df_corp):
        '''
        This function takes the cosine similarity between the documents to
        see if the candidate corpus is in alignment with our ground truth
        privacy policies.
        Ideas:
            - Get TF of ground truth. Expect at least half of those terms to
              show up in a privacy policy
            - Jaccard Similarity (medium article)
            - https://www.nltk.org/book/ch06.html (2.3)
        In:     df_gt - dataframe of ground truth
                df_corp - dataframe of corpus (candidate privacy policy)
        Out:    cosine similarity metric
        '''
        def get_vectors(*strs):
            text = [str(t) for t in strs]
            vectorizer = CountVectorizer(text)
            vectorizer.fit(text)
            return vectorizer.transform(text).toarray()

        def get_cosine_sim(*strs): 
            vectors = [t for t in get_vectors(*strs)]
            return cosine_similarity(vectors)

        sim = get_cosine_sim(df_gt.iat[0,0], df_corp.iat[0,0])
        return sim[0][1]


    # Place all policies into a dataframe (as a column vector) and preprocess
    df_gt = get_ground_truth_vector()
    df_gt = clean_text(df_gt, 'ground_truth')

    # Iterate through all privacy policies and check for intersectionality
    test_list = ['blizzard_1.txt','britishairways_1.txt','epicurious_1.txt','huffingtonpost_1.txt']
    for website in os.listdir(TEST):
        # if website == '.DS_Store': continue
        # for fname in os.listdir(DATA + '/' + str(website)):
        # for fname in os.listdir(GROUND_TRUTH):
        if website == '.DS_Store': continue
        corpus = []
        print(DATA + '/' + str(website))
        # print(GROUND_TRUTH + '/' + str(website) + '/' + str(website))
        f = open(DATA + '/' + str(website), 'r')
        # f = open(GROUND_TRUTH + '/' + str(website) + '/' + str(website), 'r')
        corpus.append(str(f.read()))
        f.close()

        df_corp = pd.DataFrame(corpus, columns=['corpus'])
        df_corp = clean_text(df_corp, 'corpus')
        cos_sim = check_intersection(df_gt, df_corp)
        print(website + " score = " + str(cos_sim))
        # if cos_sim < SIMILARITY:
        #     not_a_privacy_policy.append(DATA + '/' + str(website) + '/' + str(website) + '\t\t\t' + str(cos_sim))
        #     print(DATA + '/' + str(website) + '/' + str(website) + '\t\t\t' + str(cos_sim))

    # Write all non-privacy policies to a file
    # print(not_a_privacy_policy)
    # f = open('not_priv_policy.txt', 'w')
    # for line in not_a_privacy_policy:
    #     f.write(line + '\n')



if __name__ == '__main__':
    verify()
    # list_verified_policies()
    # remove_nonverified_policies()