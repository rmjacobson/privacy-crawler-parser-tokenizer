""" Amazon Uploader
    Uploads contents of output/ directory to amazon S3 bucket
"""

import boto3, os

# Print iterations progress
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
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

bucket_name = 'deep-ner-parsing'
input_folder = '/Users/Ryan/Desktop/privacy_proj/Deep-NER/src/scraper/output'

# Create an S3 client with session keys
session = boto3.Session(
    # aws_access_key_id='',
    # aws_secret_access_key='',
    region_name='us-east-1'
)
s3 = session.resource('s3')
bucket = s3.Bucket('deep-ner-parsing')

files = [f for f in os.listdir(input_folder)]
print("looking at " + str(len(files)) + " files")

paragraphs = [file for file in files if "paragraph" in file]
lists = [file for file in files if "list" in file]
headers = [file for file in files if "header" in file]
sequentials = [file for file in files if "sequential" in file]

print("Uploading " + str(len(paragraphs)) + " paragraphs")
for i, file in enumerate(paragraphs):
	bucket.upload_file('%s/%s' %(input_folder,file),'%s/%s' %('paragraphs',file))
	printProgressBar(i + 1, len(paragraphs), prefix = 'Progress:', suffix = 'Complete', length = 50)

print("Uploading " + str(len(lists)) + " lists")
for i, file in enumerate(lists):
	bucket.upload_file('%s/%s' %(input_folder,file),'%s/%s' %('lists',file))
	printProgressBar(i + 1, len(lists), prefix = 'Progress:', suffix = 'Complete', length = 50)

print("Uploading " + str(len(headers)) + " headers")
for i, file in enumerate(headers):
	bucket.upload_file('%s/%s' %(input_folder,file),'%s/%s' %('headers',file))
	printProgressBar(i + 1, len(headers), prefix = 'Progress:', suffix = 'Complete', length = 50)

print("Uploading " + str(len(sequentials)) + " sequentials")
for i, file in enumerate(sequentials):
	bucket.upload_file('%s/%s' %(input_folder,file),'%s/%s' %('sequentials',file))
	printProgressBar(i + 1, len(sequentials), prefix = 'Progress:', suffix = 'Complete', length = 50)
