import RPi.GPIO as GPIO
import threading as THREADING
import time as TIME

class TimeTrigger(THREADING.Thread):

    _pin = -1
    _running = False
    _started = False
    _start_time = 0
    time_threshold = 0

    # Initialize FilamentMotionSensor
    def __init__(self, threadID, threadName, pPin, pTimeThreshold, pLogger, pCallback=None):
        THREADING.Thread.__init__(self)

        self.id = threadID
        self.name = threadName
        self.callback = pCallback
        self._logger = pLogger

        self._pin = pPin
        self._running = False
        self._started = False
        self._start_time = TIME.time()
        self.time_threshold = pTimeThreshold

    # Override run method of threading
    def run(self):
        if not self._started: #first time run method is called is by start method
            self._logger.debug("Time Trigger: start")
            self._started = True #thread has been started at least once (from official doc: if started more than once, then runtime error)
            self.set() #set trigger

        while self._running:
            elapsed_time = (TIME.time() - self._start_time)

            if (elapsed_time >= self.time_threshold):
                self.fire()

            TIME.sleep(0.250)
        #GPIO.remove_event_detect(self.used_pin)

    def fire(self):
        if(self.callback != None):
            self.callback()
        self._logger.debug("Time Trigger: fire");
        self.release()

    def release(self):
        self._running = False
        GPIO.remove_event_detect(self._pin)
        self._logger.debug("Time Trigger: release")

    def set(self):
        self._running = True
        GPIO.remove_event_detect(self._pin)
        GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._reset)
        self._logger.debug("Time Trigger: set")

    def isRunning(self):
        return self._running

    def hasStarted(self):
        return self._started

    # Eventhandler for GPIO filament sensor signal
    # The new state of the GPIO pin is read and determinated.
    # It is checked if motion is detected and printed to the console.
    def _reset(self, pPin):
        self._start_time = TIME.time()
        self._logger.debug("Time Trigger: reset at " + str(self._start_time))
