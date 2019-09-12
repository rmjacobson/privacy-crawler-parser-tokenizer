"""Module to scrape HTML and strip text from a website."""
import os
from bs4 import BeautifulSoup


class Scraper:
    """ """

    def __init__(self):
        """ """

    def scrape(self, html_dir):
        """ """
    
    def strip_text(self, html_dir, text_dir):
        """Strip all text from the HTML files.
        
        Params: html_dir - input file path to dir with all .html files
                text_dir - output file path to dir with all .txt files
        Return: n/a
        """
        for fname in os.listdir(html_dir):
            # Read HTML to BeautifulSoup Parser
            fp = open(html_dir + fname, "r")
            soup = BeautifulSoup(markup=fp.read(), features="html.parser")
            fp.close()

            # Remove all script and style elements
            for script in soup(["script", "style", "link", "img", "iframe"]):
                script.decompose()

            # Write stripped HTML to text file
            txt = soup.get_text(" ", strip=True)
            fp = open(text_dir + fname.split(".")[0] + ".txt", "w")
            fp.write(txt)


if __name__ == "__main__":
    html_dir = "../../data/policies/html/"
    text_dir = "../../data/policies/text_space_separated/"

    scraper = Scraper()
    scraper.strip_text(html_dir, text_dir)