#!/usr/bin/env python3

import requests
import subprocess
import time


def exec_bash(cmd):
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
	output, error = process.communicate()



# url = 'https://github.com/omarcartera/prayforme/archive/master.zip'

# r = requests.get(url, allow_redirects=True)

# content_length = len(r.content)
# content_type   = r.headers.get('content-type')
# filename = url.rsplit('/', 1)[1]

# print(content_length)
# print(content_type)

# with open(filename, 'wb') as file:
# 	file.write(r.content)


# exec_bash('7z x master.zip')

# exec_bash('mv prayforme-master prayforme')

# exec_bash('rm master.zip')

import git

repo = git.Repo("/home/omarcartera/Desktop/prayforme")
tree = repo.tree()
for blob in tree:
    commit = repo.iter_commits(paths=blob.path, max_count=1).next()
    print(blob.path, commit.committed_date)