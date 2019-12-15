#!/usr/bin/env python3
import RPi.GPIO as GPIO
from threading import Thread, Event
from urllib import request, parse
import time
import signal
import sys

killEventPulseCounter = Event()
killEventURLPoster = Event()

class PulseCounter(Thread):
    # If using polling mode, set the inteval. This should be based
    # off the minimum expected pulse time and halved
    # 0.05 is a good value for 1 pulse per Wh
    # - i.e. 10 pulses per second = 36kWh. Double for Nyquist 20, interval = 0.05s
    pollingInterval = 0.05

    # is we're using intuttupt mode
    isGPIOInturruptMode = False

    # current pulse count
    count = 0

    # last state for polling mode
    lastState = 0

    def getCount(self):
        return self.count

    def __init__(self, isGPIOInturruptMode):
        Thread.__init__(self)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN)
        self.isGPIOInturruptMode = isGPIOInturruptMode

    def run(self):
        if (self.isGPIOInturruptMode):
            self.runGPIOInturrupt()
        else:
            self.runGPIOPolling()
        GPIO.cleanup()

    def runGPIOPolling(self):
        while not killEventPulseCounter.isSet():
            state = GPIO.input(17)
            #print (state)
            if (state != self.lastState):
                self.lastState = state
                if (state == 1):
                    self.count += 1
                    print ("inc {}".format(self.count))
            killEventPulseCounter.wait(self.pollingInterval)
        print ("thread exiting")

    def runGPIOInturrupt(self):
        #GPIO.add_event_detect(17, GPIO.RISING, callback=self.gpioInturrupt, bouncetime=(int)(self.pollingInterval*1000))
        GPIO.add_event_detect(17, GPIO.RISING, callback=self.gpioInturrupt, bouncetime=300)
        while not killEventPulseCounter.isSet():
            killEventPulseCounter.wait(self.pollingInterval)
        print ("thread 2 exiting")

    def gpioInturrupt(self, channel):
        self.count += 1
        print("inturrupt {}".format(self.count))


class URLPoster(Thread):
    # interval in seconds to wait between sending values to the given URL
    interval = 60

    #URL to post to
    url = "http://pi10.alintech.com.au/emoncms/input/post"

    # class with a getCount() function
    counter = None

    def __init__(self, counter):
        Thread.__init__(self)
        self.counter = counter

    def run(self):
        while not killEventURLPoster.isSet():
            if (self.counter is not None):
                count = self.counter.getCount()
                self.postCount(count)
                print("posting {}".format(count))
            killEventURLPoster.wait(self.interval)
        print ("thread 2 exiting")

    def postCount(self, count):
        data = "node=meter&data={{pulsecount:{}}}&apikey=1bf5407b6ffff3de68b37e80808425ed".format(count).encode("ascii")
        req = request.Request(self.url, data)
        resp = request.urlopen(req)

def main():
    polling = True
    pollingCounter = PulseCounter(polling)
    pollingCounter.start();
    urlPoster = URLPoster(pollingCounter)
    urlPoster.start();

    print ("pausing")
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
    print ("stopping threads")
    killEventPulseCounter.set()
    killEventURLPoster.set()
    print ("joining threads")

    try:
        pollingCounter.join(1);
        print ("thread exited")
    except:
        print ("exception")

    print ("exiting")


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')

main()

