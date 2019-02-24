#!/usr/bin/env python3

# for APIs GET request
import requests
import json

# to get the current date and time
import datetime

# for invoking the popup notifications
import subprocess

# for the delay
import time

# threading
import _thread

# to handle the incoming signals to this process
import signal

# for keyboard keystrokes detection
from pynput import keyboard

# house keeping to stop CLI warnings
import gi
gi.require_version('Notify', '0.7')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')

# for the app indicator in ubuntu menu bar
from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator

from gi.repository import Notify as notify

# to allow only one instance of the program
from tendo import singleton


# resume detection
import dbus      # for dbus communication (obviously)
from gi.repository import GObject as gobject
from dbus.mainloop.glib import DBusGMainLoop # integration into the main loop

##### CONSTANTS #####
ls = []

prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']

# paths must be absolute to work at startup
# path for notification and app thumbnails
path = 	'/home/omarcartera/Desktop/prayforme/src/'

image_path = path + 'egg.svg'

# path for the notification sound
notification_path = path + '/notification.wav'

# notification messages formats
next_prayer_msg = 'Next: {0} {1} {2}'
adhan_msg       = 'Time to Adhan: {0}'
prayer_time_msg = 'Time for {0} {1} {2}'
#####################


##### GLOBALS #####
# image for app indicator icon and notification
indicator = ''
item_mute = ''

muted = False

# to make only one thread alive
threads_toggle = 0
###################

# app indicator settings
def gtk_main():
	global indicator

	APPINDICATOR_ID = 'myappindicator'

	indicator = appindicator.Indicator.new(APPINDICATOR_ID, image_path, appindicator.IndicatorCategory.SYSTEM_SERVICES)
	indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
	indicator.set_menu(build_menu())

	notify.init(APPINDICATOR_ID)

	gtk.main()


# bulding the menu items
def build_menu():
	global item_mute

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

	# mute/unmute the notifications until next prayer
	item_mute = gtk.MenuItem('Mute')
	item_mute.connect('activate', mute)
	menu.append(item_mute)

	menu.show_all()

	return menu


# alternative way to CTRL + C to terminate the process
def quit(source):
	exit()


# mute/unmute the notifications until next prayer
def mute(source = None):
	global item_mute, muted

	if muted:
		image_path = path + 'egg.svg'
		label = 'Mute'

	else:
		image_path = path + 'mute.png'
		label = 'Unmute'

	# updating the app/notification thumbnail and menu tab label
	indicator.set_icon(image_path)
	item_mute.set_label(label)

	muted = not muted


# pops a notification to tell the remaining time
def what_is_next(source = 0):
	# get the prayers timing sheet
	# also here you need the absolute path
	with open(path + 'prayers.json', 'r') as prayers_file:
		data = json.load(prayers_file)

	times = data['times']
	actual_date = data['actual_date']
	today = data['today']

	# to get the current time
	now_in_minutes = get_now_in_minutes()

	# add the current time to the prayers timing list
	times.append(now_in_minutes)

	# sorting will puth the current_time entry just before the next prayer
	times.sort()
		
	# get the remaining time to the next prayer
	delta = get_delta_time(now_in_minutes, times)
	
	# name of next prayer
	next_prayer = get_next_prayer(times, now_in_minutes)
	
	if muted:
		image_path = path + 'mute.png'

	else:
		image_path = path + 'egg.svg'

	# invoke notification
	## should be through a function
	subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', next_prayer_msg.format(next_prayer, today, actual_date), adhan_msg.format(min_to_time(delta))])


# pop notifications of time remaining to the next prayer
def prayer_reminder(my_thread_toggle):
	global muted
	
	corrected = False

	while True:
		if threads_toggle != my_thread_toggle:
			print('thread', my_thread_toggle, 'is off')
			break

		# get the prayers timing sheet and actual date of the prayer
		with open(path + 'prayers.json', 'r') as prayers_file:
			data = json.load(prayers_file)

		times = data['times']
		actual_date = data['actual_date']
		today = data['today']

		# to get the current time
		now_in_minutes = get_now_in_minutes()

		# add the new current_time to the list
		times.append(now_in_minutes)

		# sorting will puth the current_time entry just before the next prayer
		times.sort()

		# get the time difference between now and next prayer
		delta = get_delta_time(now_in_minutes, times)
		
		# name of next prayer
		next_prayer = get_next_prayer(times, now_in_minutes)

		# an initail solution to Isha-Midnight-Fajr problem
		if next_prayer == 'Fajr' and not corrected:
			# get the timing sheet for tomorrow, coz we are now
			# before midnight and the next Fajr is tomorrow
			
			### not general ###
			get_prayer_times(0, 'IT', 'Bologna')

			# to get the current time
			now_in_minutes = get_now_in_minutes()
			corrected = True

			# get the new prayers timing sheet
			with open(path + 'prayers.json', 'r') as prayers_file:
				data = json.load(prayers_file)

				times = data['times']
				actual_date = data['actual_date']
		

		elif next_prayer != 'Fajr' and corrected:
			corrected = False

			
		elif next_prayer == 'Dhuhr' and today == 'Fri':
			next_prayer = 'Jomaa'


		# needs to be placed in a more logical place
		if muted:
			polling_time = delta * 60
			image_path = path + 'mute.png'

			# process state: running --> sleep
			time.sleep(polling_time)
			
			# recover from mute coz the muted prayer has passed
			mute()

		else:	
			# play notification sound in a temporary thread
			# because aplay command is blocking
			# to be synced with the popup notification
			_thread.start_new_thread(play, ())
			image_path = path + 'egg.svg'

			# we can pray now
			if delta == 0:
				for r in range(4):
					subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', prayer_time_msg.format(next_prayer, today, actual_date)])

					# renotify every 20 seconds for 5 times
					time.sleep(25)
					
				polling_time = 0
				
			# anything less than 2 hours remaining
			elif delta <= 120:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', next_prayer_msg.format(next_prayer, today, actual_date), adhan_msg.format(min_to_time(delta))])
				
				# repeat after (remaining time)/3 elapses
				polling_time = (delta/3.0) * 60

			# anything more than 2 hours remaining
			else:
				subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', next_prayer_msg.format(next_prayer, today, actual_date), adhan_msg.format(min_to_time(delta))])
				
				# sleep until it's 2 hours remaining
				polling_time = (delta - 120) * 60

			# process state: running --> sleep
			time.sleep(polling_time)

# get current time
def get_now_in_minutes():
	# to get the current time
	now = datetime.datetime.now()

	# to get the current time as integer minutes counted from 00:00
	now_in_minutes = time_to_min(str(now)[11:16])

	return now_in_minutes


# Delta Time: A term used to describe the time difference between
# two different laps or two different cars. For example, there is
# usually a negative delta between a driver's best practice lap time
# and his best qualifying lap time because he uses a low fuel load and new tyres.
def get_delta_time(now_in_minutes, times):
	# getting delta, times is a circular list
	delta = times[(times.index(now_in_minutes) + 1) % 6] - times[times.index(now_in_minutes)]

	# if now is after isha, before midnight and next prayer is Fajr --> negative delta
	if delta < 0:
		delta = delta + 24 * 60

	return delta


# returns the name of the next prayer based on current
# time index in the timing list
def get_next_prayer(times, now_in_minutes):
	return prayers[times.index(now_in_minutes) % 5]


# get your current location based on your public IP
def get_location_data():
	connected = False

	while not connected:
		try:
			ip_info = (requests.get('http://ipinfo.io/json')).json()
			connected = True

		except:
			print('*****************')
			print('*Reconnecting...*')
			print('*****************')

			time.sleep(2)

	country = ip_info['country']
	city = ip_info['city']

	return country, city


# get prayer times for a complete month
def get_prayer_times(fajr_correction, country, city):
	times = []
	connected = False

	# to get the current date and time
	now = datetime.datetime.now()

	# to get prayer times based on your location
	url = 'http://api.aladhan.com/v1/calendarByCity'

	payload = {'country': country, 'city': city, 'month': now.month,
			   'year': str(now.year), 'method': 3, 'midnightMode': 0 }

	while not connected:
		try:
			response = ((requests.get(url, params=payload)).json())['data']
			connected = True

		except:
			print('*****************')
			print('*Reconnecting...*')
			print('*****************')

			time.sleep(2)
		

	for i in range(5):
		# index of today = today - 1 .. that's how fajr correction works
		times.append(str(response[now.day - fajr_correction]['timings'][prayers[i]][:5]))
		times[i] = time_to_min(str(times[i]))



	# actual date of these timings, for research reasons
	actual_date = response[now.day - fajr_correction]['date']['readable']

	# needs fajr correction as well
	today = (now + datetime.timedelta(days=not(fajr_correction))).strftime("%A")[:3]

	dic = {'times': times, 'actual_date': actual_date, 'today': today}

	# write down the timing sheet and actual date into a json
	with open(path + 'prayers.json', 'w') as prayers_file:
		json.dump(dic, prayers_file)
	

# to play notification sound
def play():
	subprocess.call(['aplay',  notification_path])


# convert hh:mm to integer minutes
def time_to_min(time):
	return int(time[:2]) * 60 + int(time[3:])


# convert integer minutes to hh:mm
def min_to_time(min):
	return str(int((min/60)%24)).zfill(2) + ':' + str(int(min%60)).zfill(2)


# what to do when the buttons combination is pressed
def on_press(key):
	if str(key) in {'Key.ctrl', 'Key.space', 'Key.shift', 'Key.cmd'}:
		ls.append(str(key))

	if sorted(ls) == sorted(['Key.ctrl', 'Key.shift', 'Key.space']):
		what_is_next()

	if sorted(ls) == sorted(['Key.ctrl', 'Key.shift', 'Key.cmd']):
		mute()


# what to do when the buttons combination is released .. ahem
def on_release(key):
	if str(key) in {'Key.ctrl', 'Key.space', 'Key.shift', 'Key.cmd'}:
		ls.remove(str(key))	


# initialize the keyboard monitoring thread
def listener_fn():
	with keyboard.Listener(on_press, on_release) as listener:
		listener.join()


def handle_sleep_callback(sleeping):
	global threads_toggle

	if not sleeping:
		time.sleep(5)
		threads_toggle += 1
		print('thread', threads_toggle, 'is on')
		_thread.start_new_thread(prayer_reminder, (threads_toggle,))


def onButtonPressed(button):
	print('begun')
	country = lndt_country.get_text()
	city = lndt_city.get_text()

	window.hide()
	print('leaving')
	# this blocks the main thread
	_thread.start_new_thread(gtk_main, ())
	cont(country, city)


def onDestroy(sth):
	print('BYYYYYE')
	exit()


def call_gui():
	global lndt_country, lndt_city, window

	builder = gtk.Builder()
	builder.add_from_file(path + "gui_design.glade")

	handlers = {
	    "onButtonPress": onButtonPressed,
	    "onDestroy"		 : onDestroy
	}

	builder.connect_signals(handlers)

	xml = builder.get_objects()
	print(xml)

	window = builder.get_object("window1")
	lndt_country = builder.get_object("lndt_country")
	lndt_city = builder.get_object("lndt_city")

	btn_continue = builder.get_object("btn_continue")

	country, city = get_location_data()

	lndt_country.set_text(country)
	lndt_city.set_text(city)

	window.show_all()
	gtk.main()


def cont(country, city):
	# put the prayer times in the json
	get_prayer_times(1, country, city)

	# a thread to monitor the remaining time for the next prayer
	_thread.start_new_thread(prayer_reminder, (threads_toggle,))
	
	try:
		DBusGMainLoop(set_as_default=True) # integrate into main loob
		bus = dbus.SystemBus()             # connect to dbus system wide
		bus.add_signal_receiver(           # defince the signal to listen to
			handle_sleep_callback,            # name of callback function
			'PrepareForSleep',                 # signal name
			'org.freedesktop.login1.Manager',   # interface
			'org.freedesktop.login1'            # bus name
		)

		loop = gobject.MainLoop()          # define mainloop
		loop.run()                         # run main loop
	
	except Exception as e:
		print('***', e, '***')


##### MAIN #####
def main():
	global xml
	# to make it responsive to CTRL + C signal
	# put IGN instead of DFL to ignore the CTRL + C
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	# start the thread to listen for keyboard presses
	_thread.start_new_thread(listener_fn, ())

	call_gui()


if __name__ == '__main__':
	# to limit the program to only one active instance
	try:
		me = singleton.SingleInstance()

	except:
		exit()

	# wait 60 seconds after startup before starting
	time.sleep(0)
	main()