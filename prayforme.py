# for APIs GET
import requests
import json

# to get the current date and time
import datetime

# for calling the popup notifications
import subprocess

# for the time delay
import time

# threading
import _thread

# to handle the incoming signals to this process
import signal

# for the app indicator n ubuntu main bar
from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator

from gi.repository import Notify as notify

# to make it responsive to CTRL + C signal
# put IGN instead of DFL to ignore the CTRL + C
signal.signal(signal.SIGINT, signal.SIG_DFL)

# image for app indicator icon and notification
image_path = '/home/omarcartera/Desktop/prayforme/eggs.svg'

# app indicator settings
def main():
	APPINDICATOR_ID = 'myappindicator'

	indicator = appindicator.Indicator.new(APPINDICATOR_ID, image_path, appindicator.IndicatorCategory.SYSTEM_SERVICES)
	indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
	indicator.set_menu(build_menu())

	notify.init(APPINDICATOR_ID)

	gtk.main()


def build_menu():
	# creating a menu in app indicator
	menu = gtk.Menu()

	# quit tab in the menu
	item_quit = gtk.MenuItem('Quit')
	item_quit.connect('activate', quit)
	menu.append(item_quit)

	# asking for the time remaining for the next prayer
	item_next = gtk.MenuItem('Next')
	item_next.connect('activate', what_is_next)
	menu.append(item_next)

	menu.show_all()
	return menu

# alternative way to terminate correctly
def quit(source):
	gtk.main_quit()

# should pop a notification to tell the remaining time
def what_is_next(source):
	print('Nothing till now')

# 
def print_delta(times, prayers, actually):
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
		
		if next_prayer == 'Isha':
			boxboxbox = True

		print(next_prayer)

		delta = times[(times.index(now_in_minutes) + 1) % 6] - times[times.index(now_in_minutes)]

		if delta < 0:
			delta = delta + 24 * 60

		print(delta)
		print(min_to_time(delta))

		if not_notified:
			if delta == 0:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'It is time for ' + next_prayer + ' ' + actually])
				print('We Can Pray ' + next_prayer + ' Now')
				polling_time = 60/6

				if boxboxbox == True:
					get_prayer_times(0)
					boxboxbox = False

			elif delta <= 120:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Next Prayer is ' + next_prayer + ' ' + actually, 'Time to Adhan: ' + min_to_time(delta)])
				print('Next Prayer is ' + next_prayer + '\nTime to Adhan: ' + min_to_time(delta))
				polling_time = (delta/3) * 60

			else:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Next Prayer is ' + next_prayer + ' ' + actually, 'Time to Adhan: ' + min_to_time(delta)])
				polling_time = (delta - 120) * 60

		time.sleep(polling_time)

# convert hh:mm to integer minutes
def time_to_min(time):
	return int(time[:2]) * 60 + int(time[3:])

# convert integer minutes to hh:mm
def min_to_time(min):
	return str(int(min/60)).zfill(2) + ':' + str(min%60).zfill(2)

# get your current location based on your public IP
def get_location_data():
	ip_info = (requests.get('http://ipinfo.io/json')).json()

	return ip_info['country'], ip_info['city']

# get prayer times for a complete month
def get_prayer_times(after_isha = 1):
	# to get the current time
	now = datetime.datetime.now()

	# initial implementation to get tomorrows prayers
	if now.hour > 19:
		after_isha = 0

	# ISO Alpha-2 country code and city name
	country, city = get_location_data()

	# to get prayer times based on your location
	url = 'http://api.aladhan.com/v1/calendarByCity'

	payload = {'country': country, 'city': city, 'month': now.month,
			   'year': str(now.year), 'method': 3, 'midnightMode': 0 }

	data = (requests.get(url, params=payload)).json()

	# actual date of these timings, for debugging
	actually = data['data'][now.day - after_isha]['date']['readable']

	prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
	times = []

	for i in range(5):
		times.append(str(data['data'][now.day - after_isha]['timings'][prayers[i]][:5]))
		times[i] = time_to_min(str(times[i]))

	# a thread to monitor the remaining time for the next prayer
	_thread.start_new_thread(print_delta, (times, prayers, str(actually),))


get_prayer_times()

# this blocks the main thread
main()