import RPi.GPIO as GPIO
import threading as THREADING
import time as TIME

class TimeTrigger(THREADING.Thread):

    _pin = -1
    _running = False
    _started = False
    _start_time = 0
    _time_threshold = 0

    # Initialize FilamentMotionSensor
    def __init__(self, threadID, threadName, pPin, pTimeThreshold, pLogger, pCallback=None):
        pLogger.debug("Time Trigger: initializing a new thread")
        THREADING.Thread.__init__(self)
        pLogger.debug("Time Trigger: new thread is ready")

        self.id = threadID
        self.name = threadName
        self.callback = pCallback
        self._logger = pLogger

        self._pin = pPin
        self._running = False
        self._started = False
        self._start_time = TIME.time()
        self._time_threshold = pTimeThreshold

        self._logger.debug("Time Trigger: init done")

    # Override run method of threading
    def run(self):
        if (not self._started): #first time run method is called is by start method
            self._logger.debug("Time Trigger: starting")
            self._started = True #thread has been started at least once (from official doc: if started more than once, then runtime error)
            self._set(self) #set trigger

        while self._started:

            if self._running:
                elapsed_time = (TIME.time() - self._start_time)

                if (elapsed_time > self._time_threshold):
                    self.fire(self)

            TIME.sleep(0.250)
        #GPIO.remove_event_detect(self.used_pin)

    def _set(self):
        self._logger.debug("Time Trigger: running is " + str(self._runningz))
        if (not self._running):
            self._running = True
            GPIO.remove_event_detect(self._pin) #remove any previous event on the monitored pin
            GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._reset_time)
            self._logger.debug("Time Trigger: set done")

    def _reset_time(self, pPin):
        self._start_time = TIME.time() #reset internal time
        self._logger.debug("Time Trigger: reset internal time at " + str(self._start_time))

    def fire(self):
        if(self.callback != None):
            self.callback()
        self._logger.debug("Time Trigger: fire done");
        self.release(self)

    def release(self):
        self._running = False
        GPIO.remove_event_detect(self._pin) #can be removed
        self._logger.debug("Time Trigger: release done")

    def reset(self):
        self._running = False #thus set will work
        self._set(self) #set again trigger
        self._reset_time(self, self._pin) #reset internal time
        self._logger.debug("Time Trigger: reset done")

    def isRunning(self):
        return self._running

    def hasStarted(self):
        return self._started
