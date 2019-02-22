#!/usr/bin/env python3


import requests
import subprocess
import time

url = 'https://github.com/omarcartera/prayforme/archive/master.zip'

r = requests.get(url, allow_redirects=True)

content_length = len(r.content)
content_type   = r.headers.get('content-type')
filename = url.rsplit('/', 1)[1]

print(content_length)
print(content_type)

with open(filename, 'wb') as file:
	file.write(r.content)