import requests
import json
import datetime

import os
import time

import _thread

import signal

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator

from gi.repository import Notify as notify

# to make it responsive to CTRL + C
# put IGN instead of DFL to ignore the CTRL + C
signal.signal(signal.SIGINT, signal.SIG_DFL)

next_prayer = ''

# app indicator settings
def main():
	APPINDICATOR_ID = 'myappindicator'

	indicator = appindicator.Indicator.new(APPINDICATOR_ID, os.path.abspath('eggs.svg'), appindicator.IndicatorCategory.SYSTEM_SERVICES)
	indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
	indicator.set_menu(build_menu())

	notify.init(APPINDICATOR_ID)

	gtk.main()


def build_menu():
	global next_prayer

	menu = gtk.Menu()
	item_quit = gtk.MenuItem('Quit')
	item_quit.connect('activate', quit)
	menu.append(item_quit)

	item_next = gtk.MenuItem('Next')
	item_next.connect('activate', what_is_next)
	menu.append(item_next)

	menu.show_all()
	return menu


def quit(source):
	gtk.main_quit()


def what_is_next(source):
	print('Nothing till now')


def print_delta(times, prayers):
	time.sleep(1)

	not_notified = True
	polling_time = 5

	while True:
		try:
			times.remove(now_in_minutes)
		except:
			print('ERROR')

		# to get the current time
		now = datetime.datetime.now()

		now_in_minutes = time_to_min(str(now)[11:16])
		times.append(now_in_minutes)
		times.sort()

		print(times)
		print([min_to_time(x) for x in times])

		next_prayer = prayers[times.index(now_in_minutes)%5]
		
		print(next_prayer)

		delta = times[times.index(now_in_minutes) + 1] - times[times.index(now_in_minutes)]
		print(delta)

		if not_notified:
			if delta == 0:
				notify.Notification.new('It is time for ' + next_prayer, None).show()
				print('It is time for ' + next_prayer)
				polling_time = 60/6

			elif delta <= 5:
				notify.Notification.new('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta), None).show()
				print('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta))
				polling_time = 2.5 * 60

			elif delta <= 10:
				notify.Notification.new('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta), None).show()
				print('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta))
				polling_time = 5 * 60

			elif delta <= 30:
				notify.Notification.new('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta), None).show()
				print('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta))
				polling_time = 10 * 60

			elif delta <= 60:
				notify.Notification.new('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta), None).show()
				print('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta))
				polling_time = 15 * 60

			elif delta <= 120:
				notify.Notification.new('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta), None).show()
				print('Next Prayer is ' + next_prayer, 'Time to Adhan: ' + min_to_time(delta))
				polling_time = 30 * 60

			else:
				polling_time = (delta - 120) * 60

		time.sleep(polling_time)


def time_to_min(time):
	return int(time[:2]) * 60 + int(time[3:])


def min_to_time(min):
	return str(int(min/60)).zfill(2) + ':' + str(min%60).zfill(2)


def get_location_data():
	# to get your location automatically
	ip_info = (requests.get('http://ipinfo.io/json')).json()

	return ip_info['country'], ip_info['city']


def get_prayer_times():
	# to get the current time
	now = datetime.datetime.now()

	country, city = get_location_data()

	# to get prayer times based on your location
	url = 'http://api.aladhan.com/v1/calendarByCity'

	payload = {'country': country, 'city': city, 'month': now.month,
			   'year': str(now.year), 'method': 3, 'midnightMode': 0 }

	data = (requests.get(url, params=payload)).json()

	prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
	times = [None] * 5

	for i in range(5):
		times[i] = str(data['data'][now.day - 1]['timings'][prayers[i]][:5])
		times[i] = time_to_min(str(times[i]))

	_thread.start_new_thread(print_delta, (times, prayers))


get_prayer_times()

print('gone')
# this enters an infinite loop
main()