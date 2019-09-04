# Downloading the dataset
```
$ curl https://thomasvn.s3.amazonaws.com/privacy_policies_dataset.zip --output privacy_policies_dataset.zip
$ curl https://thomasvn.s3.amazonaws.com/privacy_policies_dataset_clean.zip --output privacy_policies_dataset_clean.zip
$ unzip privacy_policies_dataset.zip
$ unzip privacy_policies_dataset_clean.zip
```

# About the dataset
In this directory, you will find the following subdirectories:
- `links`: This directory contains lists of the most popular websites
as ranked by Alexa Top Sites.
- `privacy_policies_dataset`: This directory contains subdirectories for each
site we scraped. `policies_html` will contain the raw HTML. `policies_text` will
contain the stripped text.
- `privacy_policies_dataset_clean`: This directory is similar to
`privacy_policies_dataset`, however we have removed all files which we do not
believe to be a privacy policy.
- `privacy_policies_ground_truth`: This directory contains human-verified
privacy policies. These will be used as a baseline for determining whether any
newly scraped policy is actually a privacy policy (as opposed to a news article
about privacy).
- `privacy_policy_links`: This directory contains links to all privacy policies
we scraped.