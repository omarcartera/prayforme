import requests
import json
import datetime

import os

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
import signal

# to make it responsive to CTRL +C
signal.signal(signal.SIGINT, signal.SIG_DFL)

# app indicator settings
def main():
	APPINDICATOR_ID = 'myappindicator'

	indicator = appindicator.Indicator.new(APPINDICATOR_ID, os.path.abspath('eggs.svg'), appindicator.IndicatorCategory.SYSTEM_SERVICES)
	indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
	indicator.set_menu(build_menu())
	gtk.main()

def build_menu():
    menu = gtk.Menu()
    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    return menu

def quit(source):
	gtk.main_quit()

# this enters an infinite loop
main()

# to get the current time
now = datetime.datetime.now()

payload = {'city': 'Bologna', 'country': 'IT', 'month': 1,
		   'year': '2019', 'method': 3, 'midnightMode': 0 }
response = requests.get('http://api.aladhan.com/v1/calendarByCity', params=payload)


data = response.json()

prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
times = [None] * 5

for i in range(5):
	times[i] = str(data['data'][now.day - 1]['timings'][prayers[i]][:5])
	times[i] = int(times[i][:2]) * 60 + int(times[i][3:])

print(times)

print(int(str(now)[11:13]) * 60 + int(str(now)[14:16]))