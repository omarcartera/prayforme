#!/usr/bin/env python3

"""I think this is docstring"""


########## IMPORTS ##########
# handle terminating the aplay process when the program exits
import atexit

# for the delay
import time

# for invoking the popup notifications
import subprocess

# to handle the incoming signals to this process
import signal

# to get the current date and time
import datetime

# for APIs GET request
import json
import requests

# sleep/resume detection .. dbus interfacing
import dbus

# to allow only one instance of the program
from tendo import singleton

# GObject
from gi.repository import GObject

# house keeping to stop CLI warnings
import gi
gi.require_version('Notify', '0.7')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')

# for the app indicator in ubuntu menu bar
from gi.repository import GObject as gobject, Gtk as gtk,\
AppIndicator3 as appindicator, Notify as notify

# to check for ubuntu version
import lsb_release

# integration into the mainloop
from dbus.mainloop.glib import DBusGMainLoop

# for keyboard keystrokes detection
from pynput import keyboard

# threading
import _thread
##########################################


########## CONSTANTS ##########

KEY_ENTER = 65293
prayNow = False
# KEY_SHIFT = 65505
# KEY_CTRL  = 65507
# KEY_CMD   = 65515
# KEY_SPACE = ' '

# list of prayers
PRAYERS = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']

# paths must be absolute to work at startup
# otherwise the app works from home directory and fails
# to find the required files.
ABS_PATH = '/home/hazem/Desktop/prayforme/src/'


if lsb_release.get_distro_information()['DESCRIPTION'] == 'Ubuntu 16.04':
    ## for ubuntu 16.04
    ICON_PATH = ABS_PATH + 'egg.svg'

else:
    ## for ubuntu 18.10 .. we need an automated check
    ICON_PATH = ABS_PATH + 'eggw.svg'

MUTE_ICON = ABS_PATH + 'mute.png'
NOT_MUTE_ICON = ABS_PATH + 'egg.svg'

# path for the notification sound
NOTIFICATION_PATH = ABS_PATH + 'notification.wav'
#path for adan sound
ADAN_PATH = ABS_PATH + 'adan.wav'

# notification messages formats
NEXT_PRAYER_MSG = '{0}, {1} {2}'
ADHAN_MSG = 'Time to Adhan: {0}'
PRAYER_TIME_MSG = 'Time for {0} {1} {2}'

##########################################


########## GLOBALS ##########

LS = []

# image for app indicator icon and notification
INDICATOR = ''
ITEM_MUTE = ''

MUTED = False

# to make only one thread alive
THREAD_ID = 0

##########################################

########## APP INDICATOR ##########

# app indicator settings
def gtk_main():
    global INDICATOR

    appindicator_id = 'myappindicator'

    INDICATOR = appindicator.Indicator.new(appindicator_id, ICON_PATH,\
        appindicator.IndicatorCategory.SYSTEM_SERVICES)
    INDICATOR.set_status(appindicator.IndicatorStatus.ACTIVE)
    INDICATOR.set_menu(build_menu())

    notify.init(appindicator_id)

    gtk.main()


# bulding the menu items
def build_menu():
    global ITEM_MUTE

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
    ITEM_MUTE = gtk.CheckMenuItem('Mute')
    ITEM_MUTE.set_draw_as_radio(True)
    ITEM_MUTE.connect('activate', mute)
    menu.append(ITEM_MUTE)

    menu.show_all()

    return menu


# alternative way to CTRL + C to terminate the process
def gui_quit(source=None, sth=None):
    PROCESS.terminate()
    exit()


# mute/unmute the notifications until next prayer
def mute(source=None):
    global ITEM_MUTE, MUTED
    PROCESS.terminate()
    if MUTED:
        # to match the correct icon path for this ubuntu version
        image_path = ICON_PATH
        label = 'Mute'

    else:
        image_path = MUTE_ICON
        label = 'Unmute'

    # updating the app/notification thumbnail and menu tab label
    INDICATOR.set_icon(image_path)
    ITEM_MUTE.set_label(label)

    MUTED = not MUTED

##########################################


########## PRAYERS LOGIC ##########

# pops a notification to tell the remaining time
def what_is_next(source=0):
    # get the prayers timing sheet
    # also here you need the absolute path
    data = json_interface(ctrl='r')

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

    if MUTED:
        image_path = MUTE_ICON

    else:
        image_path = NOT_MUTE_ICON

    # invoke notification
    mode = 'next_prayer'
    title = NEXT_PRAYER_MSG.format(next_prayer, today, actual_date)
    body = ADHAN_MSG.format(min_to_time(delta))

    show_notification(mode=mode, title=title, body=body)


# returns the name of the next prayer based on current
# time index in the timing list
def get_next_prayer(times, now_in_minutes):
    return PRAYERS[times.index(now_in_minutes) % 5]


# pop notifications of time remaining to the next prayer
def prayer_reminder(my_thread_id):
    global MUTED

    corrected = False

    while True:
        if THREAD_ID != my_thread_id:
            print('thread', my_thread_id, 'is off')
            break

        # get the prayers timing sheet and actual date of the prayer
        data = json_interface(ctrl='r')

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

            country, city = get_location_data()
            get_prayer_times(0, country, city)

            # to get the current time
            now_in_minutes = get_now_in_minutes()
            corrected = True

            # get the new prayers timing sheet
            data = json_interface(ctrl='r')


            times = data['times']
            actual_date = data['actual_date']


        elif next_prayer != 'Fajr' and corrected:
            corrected = False


        elif next_prayer == 'Dhuhr' and today == 'Fri':
            next_prayer = 'Jomaa'


        # needs to be placed in a more logical place
        if MUTED:
            polling_time = int((delta + 1.1) * 60)

            # process state: running --> sleep
            time.sleep(polling_time)

            # recover from mute coz the muted prayer has passed
            mute()


        else:
            # we can pray now
            if delta == 0:
                # invoke notification
                mode = 'prayer_time'
                title = PRAYER_TIME_MSG.format(next_prayer, today, actual_date)

                # wait 25 seconds between every notification
                polling_time = 25


            # anything less than 2 hours remaining
            elif delta <= 120:

                # invoke notification
                mode = 'next_prayer'
                title = NEXT_PRAYER_MSG.format(next_prayer, today, actual_date)
                body = ADHAN_MSG.format(min_to_time(delta))

                # repeat after (remaining time)/3 elapses
                polling_time = (delta/3.0) * 60


            # anything more than 2 hours remaining
            else:
                # invoke notification
                mode = 'next_prayer'
                title = NEXT_PRAYER_MSG.format(next_prayer, today, actual_date)
                body = ADHAN_MSG.format(min_to_time(delta))

                # sleep until it's 2 hours remaining
                polling_time = (delta - 120) * 60

            # invoke notification
            show_notification(mode=mode, title=title, body=body)

            # process state: running --> sleep
            time.sleep(polling_time)

##########################################


########## TIME THINGS ##########

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


# convert hh:mm to integer minutes
def time_to_min(time_):
    return int(time_[:2]) * 60 + int(time_[3:])


# convert integer minutes to hh:mm
def min_to_time(mins):
    return str(int((mins/60)%24)).zfill(2) + ':' + str(int(mins%60)).zfill(2)

##########################################


########## APIs ##########

# get your current location based on your public IP
def get_location_data():
    connected = False

    while not connected:
        try:
            ip_info = (requests.get('http://ipinfo.io/json')).json()

            country = ip_info['country']
            city = ip_info['city']

            connected = True

        except:
            print('*****************')
            print('*Reconnecting...*')
            print('*****************')

            time.sleep(2)

    return country, city


# get prayer times for a complete month
def get_prayer_times(fajr_correction, country, city):
    times = []

    # to get the current date and time
    now = datetime.datetime.now()

    # to get prayer times based on your location
    url = 'http://api.aladhan.com/v1/calendarByCity'

    payload = {'country': country, 'city': city, 'month': now.month,
               'year': str(now.year), 'method': 3, 'midnightMode': 0}

    connected = False

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
        times.append(str(response[now.day - fajr_correction]['timings'][PRAYERS[i]][:5]))
        times[i] = time_to_min(str(times[i]))

    # actual date of these timings, for research reasons
    actual_date = response[now.day - fajr_correction]['date']['readable']

    today = (now + datetime.timedelta(days=not fajr_correction)).strftime("%A")[:3]

    dic = {'times': times, 'actual_date': actual_date, 'today': today}

    # write down the timing sheet and actual date into a json
    json_interface('w', dic)

##########################################


########## JSON FILE ##########

# a single function to write/read from the json
def json_interface(ctrl='r', to_write=None):
    with open(ABS_PATH + 'prayers.json', ctrl) as prayers_file:
        if ctrl == 'w':
            json.dump(to_write, prayers_file)
            data = ''

        if ctrl == 'r':
            data = json.load(prayers_file)

        return data

##########################################


########## NOTIFICATIONS ##########

# to play notification sound
def play(mode = None):
    global PROCESS
    if mode == 'adan':
        p = subprocess.Popen(['aplay', ADAN_PATH])
        PROCESS = p
        p.wait() ; p.terminate()
    else:
        p = subprocess.Popen(['aplay', NOTIFICATION_PATH])
        p.wait() ; p.terminate()
        


# a unified function that shows the popup notification
def show_notification(mode=None, title=None, body=None):
    global MUTED
    # play notification sound in a temporary thread
    # because aplay command is blocking
    # to be synced with the popup notification
    if MUTED:
        image_path = MUTE_ICON

    else:
        image_path = NOT_MUTE_ICON
        if mode == 'prayer_time':
            _thread.start_new_thread(play, ('adan',))
        else:
            _thread.start_new_thread(play, ())
                


    if mode == 'next_prayer':
        subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', title, body])

    elif mode == 'prayer_time':
        subprocess.call(['notify-send', '-i', image_path, '-u', 'critical', title])

##########################################


########## KEYSTROKES DETECTION ##########

# initialize the keyboard monitoring thread
def listener_fn():
    with keyboard.Listener(on_press, on_release) as listener:
        listener.join()


# what to do when the buttons combination is pressed
def on_press(key):
    print('ADD: ', key)

    if str(key) in {'Key.ctrl', 'Key.space', 'Key.shift', 'Key.cmd'}:
        LS.append(str(key))

    if sorted(LS) == sorted(['Key.ctrl', 'Key.shift', 'Key.space']):
        what_is_next()

    if sorted(LS) == sorted(['Key.ctrl', 'Key.shift', 'Key.cmd']):
        mute()

    else:
        pass


# what to do when the buttons combination is released .. ahem
def on_release(key):
    print('REM: ', str(key))

    # I don't know why this returns from left shift?
    # but until they fix it, here is our little fix
    try:
        if str(key) == '<65032>':
            LS.remove('Key.shift')

        if str(key) in {'Key.ctrl', 'Key.space', 'Key.shift', 'Key.cmd'}:
            LS.remove(str(key))

    except Exception as e:
        print(e)


# sleep and resume detection
def resume_detection(sleeping):
    global THREAD_ID

    if not sleeping:
        if MUTED:
            mute()

        time.sleep(30)
        THREAD_ID += 1
        print('thread', THREAD_ID, 'is on')
        _thread.start_new_thread(prayer_reminder, (THREAD_ID,))

##########################################


########## GTK GUI ##########

# a gui window to ensure country and city from user
def call_gui():
    global LNDT_COUNTRY, LNDT_CITY, WINDOW

    builder = gtk.Builder()
    builder.add_from_file(ABS_PATH + "gui_design.glade")

    handlers = {
        "onButtonPress": on_button_pressed,
        "onDestroy"    : gui_quit
    }

    builder.connect_signals(handlers)

    # XML = builder.get_objects()

    WINDOW = builder.get_object("window1")
    LNDT_COUNTRY = builder.get_object("lndt_country")
    LNDT_CITY = builder.get_object("lndt_city")

    # btn_continue = builder.get_object("btn_continue")

    country, city = get_location_data()

    LNDT_COUNTRY.set_text(country)
    LNDT_CITY.set_text(city)

    # connect the enter keystroke to trigger button press
    LNDT_COUNTRY.connect("key-press-event", test)
    LNDT_CITY.connect("key-press-event", test)

    WINDOW.show_all()
    gtk.main()


# continue after pressing OK button
def cont(country, city):
    # put the prayer times in the json
    get_prayer_times(1, country, city)

    # a thread to monitor the remaining time for the next prayer
    _thread.start_new_thread(prayer_reminder, (THREAD_ID,))

    try:
        DBusGMainLoop(set_as_default=True)      # integrate into main loob
        bus = dbus.SystemBus()                  # connect to dbus system wide
        bus.add_signal_receiver(                # defince the signal to listen to
            resume_detection,                   # name of callback function
            'PrepareForSleep',                  # signal name
            'org.freedesktop.login1.Manager',   # interface
            'org.freedesktop.login1'            # bus name
        )

        loop = GLib.MainLoop()               # define mainloop
        loop.run()                              # run main loop

    except Exception:
        print('***', 'ERROR', '***')


# handler for pressing OK button
def on_button_pressed(sth1=None, sth2=None):
    ''' get the user country/city and proceed '''
    # to solve the unused argument problem
    del sth1, sth2

    country = LNDT_COUNTRY.get_text()
    city = LNDT_CITY.get_text()

    WINDOW.hide()

    # this blocks the main thread
    _thread.start_new_thread(gtk_main, ())
    cont(country, city)


# detecting keypress
def test(sth1, key):
    ''' detects the enter press to proceed with city choice '''
    # to solve the unused argument problem
    del sth1
    # 65293 is the key value of enter
    if key.keyval == KEY_ENTER:
        on_button_pressed()

##########################################


########## MAIN ##########
# main function, every good thing starts here
def main():
    ''' to make it responsive to CTRL + C signal
        put IGN instead of DFL to ignore the CTRL + C
        put a function name instead of the IGN/DFL
        signal.signal(signal.SIGINT, gui_quit)
    '''
    atexit.register(gui_quit)

    # start the thread to listen for keyboard presses
    _thread.start_new_thread(listener_fn, ())

    call_gui()

##########################################


########## PYTHON's MAIN ##########

if __name__ == '__main__':
    # to limit the program to only one active instance
    try:
        STH = singleton.SingleInstance()

    except:
        exit()

    main()

##########################################
##########################################
