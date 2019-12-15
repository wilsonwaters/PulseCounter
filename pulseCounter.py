#!/usr/bin/env python3
import RPi.GPIO as GPIO
from threading import Thread, Event
from urllib import request, parse
from datetime import datetime
import time
import signal
import sys
import tempfile
import os

killEventPulseCounter = Event()
killEventURLPoster = Event()
killEventPvoutputPoster = Event()

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

    # pulse count at midnight today. Used to calculate daily energy
    countMidnight = 0

    # last state for polling mode
    lastState = 0

    # last time a state change was seen
    lastStateDate = None

    # How often to flush the current count to disk
    savePeriod = 600

    # last time state was saved
    lastSaveDate = None

    def getCount(self):
        return self.count

    def getCountToday(self):
        return self.count-self.countMidnight

    def __init__(self, isGPIOInturruptMode):
        Thread.__init__(self)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN)
        self.isGPIOInturruptMode = isGPIOInturruptMode
        self.recoverState()

    def run(self):
        #if (self.isGPIOInturruptMode):
        #    self.runGPIOInturrupt()
        #else:
        self.runGPIOPolling()
        GPIO.cleanup()

    def checkSaveState(self):
        if (self.lastSaveDate is None or (datetime.now()-self.lastSaveDate).total_seconds() > self.savePeriod):
            self.saveState()
            self.lastSaveDate = datetime.now()

    def saveState(self):
        print("saving state")
        try:
            with open(os.path.join(tempfile.gettempdir(), "pulseCounterCount"), 'w') as tempFile:
                tempFile.write(str(self.count))
            with open(os.path.join(tempfile.gettempdir(), "pulseCounterCountMidnight"), 'w') as tempFile:
                tempFile.write(str(self.countMidnight))
        except Exception as e:
            print("error saving state: "+str(e))

    def recoverState(self):
        print("recovering state")
        try:
            with open(os.path.join(tempfile.gettempdir(), "pulseCounterCount"), 'r') as tempFile:
                self.count = int(tempFile.read())
            with open(os.path.join(tempfile.gettempdir(), "pulseCounterCountMidnight"), 'r') as tempFile:
                self.countMidnight = int(tempFile.read())
            mtime = os.path.getmtime(os.path.join(tempfile.gettempdir(), "pulseCounterCountMidnight"))
            self.lastStateDate = datetime.fromtimestamp(mtime)
        except Exception as e:
            print("error recovering state: "+str(e))
            self.count = 0;
            self.countMidnight = 0;

    def runGPIOPolling(self):
        while not killEventPulseCounter.isSet():
            state = GPIO.input(17)
            #print (state)
            if (state != self.lastState):
                self.lastState = state
                if (state == 1):
                    self.count += 1
                    print ("inc {}".format(self.count))

                    # determine if midnight has passes and reset the counter
                    if (self.lastStateDate is None or datetime.now().day != self.lastStateDate.day):
                        self.countMidnight = self.count
                self.lastStateDate = datetime.now()
            killEventPulseCounter.wait(self.pollingInterval)
            self.checkSaveState()
        self.saveState()
        print ("thread PulseCounter exiting")

    def runGPIOInturrupt(self):
        #GPIO.add_event_detect(17, GPIO.RISING, callback=self.gpioInturrupt, bouncetime=(int)(self.pollingInterval*1000))
        GPIO.add_event_detect(17, GPIO.RISING, callback=self.gpioInturrupt, bouncetime=300)
        while not killEventPulseCounter.isSet():
            killEventPulseCounter.wait(self.pollingInterval)
            self.checkSaveState()
        self.saveState()
        print ("thread PulseCounter exiting")

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
        print ("thread URLPoster exiting")

    def postCount(self, count):
        data = "node=meter&data={{pulsecount:{}}}&apikey=xxxxxxxx".format(count).encode("ascii")
        req = request.Request(self.url, data)
        resp = request.urlopen(req)

class PVOutputPoster(Thread):
    # interval in seconds to wait between sending values to the given URL
    # PVOutput maximum interval time is 5 mins
    interval = 300

    # API key form the pvoutput settings page
    pvoutputAPIKey = "setme"
    pvoutputSystemId = 123456

    #URL to post to
    url = "https://pvoutput.org/service/r2/addstatus.jsp"

    # class with a getCount() function
    counter = None

    # counter and time at last event send
    lastCount = None
    lastTime = None

    def __init__(self, counter):
        Thread.__init__(self)
        self.counter = counter

    def run(self):
        while not killEventPvoutputPoster.isSet():
            if (self.counter is not None):
                count = self.counter.getCount()
                now = datetime.now()
                if (self.lastTime is not None):
                   secondsSinceLast = (now-self.lastTime).total_seconds()
                   # pulses are always 1 pulse per wh.
                   # There are 3600 seconds in an hour, so multiply numPulses by the proportion of the hour that has passed to work out average power over the  interval
                   averageWatts = (count-self.lastCount)*(3600/secondsSinceLast)
                   energy = self.counter.getCountToday()
                   self.postAddStatusAPI(now, energy, averageWatts)
                   print("posting {}".format(count))
                self.lastCount = count
                self.lastTime = now
            killEventPvoutputPoster.wait(self.interval)
        print ("thread PVOutputPoster exiting")

    def postAddStatusAPI(self, datetime, energyConsumption, powerConsumption):
        print ("powerConsumption {}".format(powerConsumption))
        data = "d={}&t={}&v3={}&v4={}".format(datetime.strftime("%Y%m%d"), datetime.strftime("%H:%M"), energyConsumption, powerConsumption).encode("ascii")
        print ("post {}".format(data))
        req = request.Request(self.url, data)
        req.add_header("X-Pvoutput-Apikey", self.pvoutputAPIKey)
        req.add_header("X-Pvoutput-SystemId", self.pvoutputSystemId)
        try:
            resp = request.urlopen(req)
        except Exception as e:
            print("error posting to PVOutput.org: "+str(e))

def main():
    polling = True
    pollingCounter = PulseCounter(polling)
    pollingCounter.start();
    urlPoster = URLPoster(pollingCounter)
    urlPoster.start();
    pvoutputPoster = PVOutputPoster(pollingCounter)
    pvoutputPoster.start();

    print ("pausing")
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
    print ("stopping threads")
    killEventPulseCounter.set()
    killEventURLPoster.set()
    killEventPvoutputPoster.set()
    print ("joining threads")

    try:
        pollingCounter.join(1);
        print ("threads exited")
    except:
        print ("exception")

    print ("exiting")


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')

main()
