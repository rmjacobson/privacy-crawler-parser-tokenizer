# Downloading the dataset
```
$ curl https://thomasvn.s3.amazonaws.com/privacy_policies_html.zip --output privacy_policies_html.zip
$ curl https://thomasvn.s3.amazonaws.com/privacy_policies_text.zip --output privacy_policies_text.zip
$ unzip privacy_policies_html.zip
$ unzip privacy_policies_text.zip
$ mv privacy_policies_html html
$ mv privacy_policies_text text
```

# About the dataset
In this directory, you will find the following subdirectories:
- `links`: This directory contains lists of the most popular websites
as ranked by Alexa Top Sites.
- `html`: html of the scraped privacy policies
- `text`: stripped text of the scraped privacy policies