"""Module to scrape HTML and strip text from a website."""
import os, threading
from bs4 import BeautifulSoup


class StripThread(threading.Thread):
    """A thread which strips all text from an HTML file."""

    def __init__(self, chunk, html_dir, text_dir, thread_num):
        """Initialize thread metadata.
        Params: chunk - portion of html_dir list
                html_dir - input file path to dir with all .html files
                text_dir - output file path to dir with all .txt files
                thread_num - thread identifier, mainly for debugging
        Return: n/a
        """
        threading.Thread.__init__(self)
        self.chunk = chunk
        self.html_dir = html_dir
        self.text_dir = text_dir
        self.thread_num = thread_num

    def run(self):
        """Strip all text from the HTML files in the assigned chunk."""
        rm_elements = ['script', 'noscript', 'meta', 'style', 'link', 'img',
                       'iframe', 'header', 'head', 'footer', 'nav']

        for fname in self.chunk:
            # print("Thread " + str(self.thread_num) + ": processing " + fname)


            # read html to BeautifulSoup Parser
            with open(self.html_dir + fname, "r") as fp:
                soup = BeautifulSoup(fp.read(), 'html.parser')

            # remove all script and style elements
            for script in soup(rm_elements):
                script.decompose()

            # use the below line if you want the text exactly as in browser
            txt = soup.get_text()
            # use the below line if you want the text to be space-separated
            # txt = soup.get_text(" ", strip=True)
            # use the below line to force the text to be completely stripped
            # txt = soup.get_text("", strip=True)

            # remove leading/trailing whitespace on each line
            txt = "".join((t.strip() for t in txt.split("\n")))

            # write stripped html to text file
            with open(self.text_dir + fname.split(".")[0] + ".txt", "w") as fp:
                fp.write(txt)

        # print("Thread " + str(self.thread_num) + ": finished")


class Scraper:
    """Launches many threads to strip text from HTML."""

    def __init__(self, num_chunks):
        """Initialize Scraper metadata.
        Params: num_chunks - number of threads used to process the html
                             (if num_chunks==1 it will process sequentially in
                             a single thread)
        Return: n/a
        """
        self.num_chunks = num_chunks

    def process_html(self, html_dir, text_dir):
        """Strip all text from the HTML files.
        Params: html_dir - input file path to dir with all .html files
                text_dir - output file path to dir with all .txt files
        Return: n/a
        """
        # chunk html list into n different lists to be processed by different threads
        html_list = (os.listdir(html_dir)[i::num_chunks] for i in range(num_chunks))
        thread_list = []
        thread_num = 0

        # start a new thread for every chunk
        for chunk in html_list:
            thread_list.append(StripThread(list(chunk), html_dir, text_dir, thread_num))
            thread_list[thread_num].start()
            thread_num = thread_num + 1

        # wait for every thread to finish before exiting
        map(lambda t: t.join(),thread_list)


if __name__ == "__main__":
    html_dir = "../../data/policies/html/"
    text_dir = "../../data/policies/text_redo/"

    # num_chunks specifies how many threads are used to process the html
    # set to 1 if want to process sequentially in single thread
    num_chunks = 2

    scraper = Scraper(num_chunks)
    scraper.process_html(html_dir, text_dir)
