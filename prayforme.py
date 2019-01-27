#!/usr/bin/env python3

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

# for hotkey detection
from pynput import keyboard

# to play sound files
import pygame

# for the app indicator n ubuntu main bar
from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator

from gi.repository import Notify as notify

# starting pygame
pygame.init()

# to make it responsive to CTRL + C signal
# put IGN instead of DFL to ignore the CTRL + C
signal.signal(signal.SIGINT, signal.SIG_DFL)

# image for app indicator icon and notification
image_path = '/home/omarcartera/Desktop/prayforme/egg.svg'

# a ton of hijo de putas global variables
next_prayer = ''
actual_date = ''
delta = ''
times = []
prayers = []

indicator = ''
item_mute = ''
item_5alas = ''

fajr_correction = 1

source = ''

salleet = False

# combinations of hotkeys to be detected
COMBINATIONS = [{keyboard.Key.shift, keyboard.Key.ctrl, keyboard.Key.space}]

# to initialize hot key thing
current = set()

# app indicator settings
def gtk_main():
	global indicator

	APPINDICATOR_ID = 'myappindicator'

	indicator = appindicator.Indicator.new(APPINDICATOR_ID, image_path, appindicator.IndicatorCategory.SYSTEM_SERVICES)
	indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
	indicator.set_menu(build_menu())

	notify.init(APPINDICATOR_ID)

	gtk.main()


def build_menu():
	global item_mute, item_5alas

	# creating a menu in app indicator
	menu = gtk.Menu()

	# quit tab in the menu
	item_quit = gtk.MenuItem('Quit')
	item_quit.connect('activate', quit)
	menu.append(item_quit)

	# asking for the time remaining for the next prayer
	item_next = gtk.MenuItem('Next Prayer?')
	item_next.connect('activate', what_is_next)
	menu.append(item_next)

	# mute/unmute the notifications
	item_mute = gtk.MenuItem('Mute')
	item_mute.connect('activate', mute)
	menu.append(item_mute)

	# mute/unmute the notifications
	item_5alas = gtk.MenuItem('Salleet 5alas')
	item_5alas.connect('activate', salleet_5alas)
	menu.append(item_5alas)

	menu.show_all()

	return menu


# alternative way to terminate correctly
def quit(source):
	gtk.main_quit()


def mute(source):
	global image_path, indicator, item_mute, item_5alas

	if image_path[-5] == 'g':
		image_path = '/home/omarcartera/Desktop/prayforme/mute.png'
		indicator.set_icon(image_path)
		item_mute.set_label('Unmute')

	else:
		image_path = '/home/omarcartera/Desktop/prayforme/egg.svg'
		indicator.set_icon(image_path)
		item_mute.set_label('Mute')


def salleet_5alas(source):
	global image_path, indicator, item_5alas, next_prayer, salleet

	if salleet == False:
		image_path = '/home/omarcartera/Desktop/prayforme/5alas.png'
		indicator.set_icon(image_path)
		item_5alas.set_label('Mashy')

		salleet = True

		pygame.mixer.Sound('congratulations.wav').play()
		subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Taqabbal Allah ya Alby ', 'There are no reminders until ' + next_prayer])

# should pop a notification to tell the remaining time
def what_is_next(source):
	global image_path, next_prayer, actual_date, times, prayers

	print(times)

	# to get the current time
	now_in_minutes = get_now_in_minutes()

	delta = get_delta(now_in_minutes)

	subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Next Prayer is ' + next_prayer + ' ' + actual_date, 'Time to Adhan: ' + min_to_time(delta)])
	print('Next Prayer is ' + next_prayer + ' ' + actual_date, 'Time to Adhan: ' + min_to_time(delta))


def prayer_reminder(times, prayers, actual_date):
	global delta, now, next_prayer, item_5alas, indicator, salleet, image_path

	time.sleep(1)

	polling_time = 5

	corrected = False

	while True:
		# to get the current time
		now_in_minutes = get_now_in_minutes()

		next_prayer = prayers[times.index(now_in_minutes) % 5]

		# an initail correction to Isha-Midnight-Fajr problem
		if next_prayer == 'Fajr' and not corrected:
			get_prayer_times(0)
			now_in_minutes = get_now_in_minutes()
			corrected = True

		else:
			corrected = False

		# get the time difference between now and next prayer
		delta = get_delta(now_in_minutes)

		if not salleet:
			# play notification sound
			pygame.mixer.Sound('notification.wav').play()

			if delta == 0:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'It is time for ' + next_prayer + ' ' + actual_date])
				print('We Can Pray ' + next_prayer + ' Now')
				polling_time = 60/6

			elif delta <= 120:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Next Prayer is ' + next_prayer + ' ' + actual_date, 'Time to Adhan: ' + min_to_time(delta)])
				print('Next Prayer is ' + next_prayer + '\nTime to Adhan: ' + min_to_time(delta))
				polling_time = (delta/3) * 60

			else:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', 'Next Prayer is ' + next_prayer + ' ' + actual_date, 'Time to Adhan: ' + min_to_time(delta)])
				polling_time = (delta - 120) * 60

		else:
			polling_time = delta - 9
			print(polling_time)

		time.sleep(polling_time)

		salleet = False
		item_5alas.set_label('Salleet 5alas')
		image_path = '/home/omarcartera/Desktop/prayforme/egg.png'
		indicator.set_icon(image_path)


# get current time
def get_now_in_minutes():
	global times

	# to get the current time
	now = datetime.datetime.now()

	now_in_minutes = time_to_min(str(now)[11:16])
	
	if len(times) > 5:
		try:
			if prayers.index(next_prayer) == 0:
				times.pop()

			else:
				times.remove(times[prayers.index(next_prayer)])

		except:
			print('Error')

	times.append(now_in_minutes)
	times.sort()

	return now_in_minutes


def get_delta(now_in_minutes):
	global times

	print('in delta', len(times))

	delta = times[(times.index(now_in_minutes) + 1) % 6] - times[times.index(now_in_minutes)]


	if delta < 0:
		delta = delta + 24 * 60

	return delta


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
def get_prayer_times(fajr_correction = 1):
	global actual_date, times, prayers

	# to get the current date and time
	now = datetime.datetime.now()

	# ISO Alpha-2 country code and city name
	country, city = get_location_data()

	# to get prayer times based on your location
	url = 'http://api.aladhan.com/v1/calendarByCity'

	payload = {'country': country, 'city': city, 'month': now.month,
			   'year': str(now.year), 'method': 3, 'midnightMode': 0 }

	response = (requests.get(url, params=payload)).json()

	prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']

	times = []

	print(len(times))

	for i in range(5):
		times.append(str(response['data'][now.day - fajr_correction]['timings'][prayers[i]][:5]))
		print(str(times[i]))
		times[i] = time_to_min(str(times[i]))

	print(len(times))

	# actual date of these timings, for debugging
	actual_date = response['data'][now.day - fajr_correction]['date']['readable']

	print('-' * 10)


def on_press(key):
	if any([key in COMBO for COMBO in COMBINATIONS]):
		current.add(key)

		if any(all(k in current for k in COMBO) for COMBO in COMBINATIONS):
			hotkey_execute()


def on_release(key):
	if any([key in COMBO for COMBO in COMBINATIONS]):
		current.remove(key)


def hotkey_execute():
	what_is_next(source)


def listener_fn():
	with keyboard.Listener(on_press = on_press, on_release = on_release) as listener:
		listener.join()


# wait 5 seconds after startup before starting
time.sleep(0)

_thread.start_new_thread(listener_fn, ())


# get the prayers timing sheet
get_prayer_times()

# a thread to monitor the remaining time for the next prayer
_thread.start_new_thread(prayer_reminder, (times, prayers, str(actual_date),))

# this blocks the main thread
source = gtk_main()