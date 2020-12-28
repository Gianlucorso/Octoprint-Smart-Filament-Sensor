# coding=utf-8
from __future__ import absolute_import
import octoprint.plugin
from octoprint.events import Events
import RPi.GPIO as GPIO
from time import sleep
from flask import jsonify
import json
from octoprint_smart_filament_sensor.time_trigger import TimeTrigger

class SmartFilamentSensor(octoprint.plugin.StartupPlugin,
                          octoprint.plugin.EventHandlerPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.SettingsPlugin):

    def initialize(self):
        self._logger.info("Running RPi.GPIO version '{0}'".format(GPIO.VERSION))
        if GPIO.VERSION < "0.6":       # Need at least 0.6 for edge detection
            raise Exception("RPi.GPIO must be greater than 0.6")
        GPIO.setwarnings(False)        # Disable GPIO warnings

        self.code_sent = False
        self.count = 0 #ignored GPIO (raising or falling) edges
        self.count_threshold = 5 #number of GPIO (raising or falling) edges to be ignored
        self.printer_paused = False #becomes true whenever printer is paused (due to a filament change request)

#Properties

    @property
    def mode(self):
        return int(self._settings.get(["mode"]))

    @property
    def pause_command(self):
        return self._settings.get(["pause_command"])

    @property
    def sensor_pin(self):
        return int(self._settings.get(["sensor_pin"]))

    @property
    def sensor_enabled(self):
        return self._settings.get_boolean(["sensor_enabled"])

    @property
    def sensor_timeout_threshold(self):
        return int(self._settings.get(["sensor_timeout_threshold"]))


# Initialization methods
    def _setup_sensor(self):
        self._logger.info("Setting up Smart Filament Sensor")
        if(self.mode == 0):
            self._logger.info("Using Board Mode")
            GPIO.setmode(GPIO.BOARD)
        else:
            self._logger.info("Using BCM Mode")
            GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.sensor_pin, GPIO.IN)

        if self.sensor_enabled == False:
            self._logger.info("Smart Filament Sensor is disabled")

        self.sensor_tmtrig_thread = None
        self._logger.info("Smart Filament Sensor has been setted up")

    def on_after_startup(self):
        self._logger.debug("Startup")
        self._setup_sensor()

    def get_settings_defaults(self):
        return dict(
            mode = 0, #Board Mode
            pause_command = "M600", #Command sent after timeout threshold
            sensor_pin = 0, #Default pin is none
            sensor_enabled = True, #Sensor detection is enabled by default
            sensor_timeout_threshold = 45 #Maximum time which, after no filament motion, the pause is triggered
            )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._setup_sensor()

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

    def _printer_isPrinting(self):
        self._setup_sensor()
        GPIO.remove_event_detect(self.sensor_pin)
        GPIO.add_event_detect(self.sensor_pin, GPIO.BOTH, callback=self._count) #used to avoid triggering the smart filament sensor before printer has actually started printing
        self._logger.debug("Enabling initial counter")
        #GPIO.remove_event_detect(self.sensor_pin) #no need to keep monitoring this pin

    def _count(self, pPin):
        self.count += 1
        if self.count < self.count_threshold:
            self._logger.debug("Ignored %d GPIO edge(s)", self.count)
        else:
            self._logger.debug("Exceeding counting threshold: ignored %d GPIO edge(s)", self.count_threshold)
            GPIO.remove_event_detect(self.sensor_pin)
            self.sensor_start()

# Sensor methods
    def sensor_start(self):
        self._logger.debug("Smart Filament Sensor enabling flag is: " + str(self.sensor_enabled))

        if self.sensor_enabled:

            if (self.mode == 0):
                self._logger.debug("GPIO mode: Board Mode")
            else:
                self._logger.debug("GPIO mode: BCM Mode")

            self._logger.debug("GPIO pin: " + str(self.sensor_pin))

            self._logger.debug("Timeout Threshold: " + str(self.sensor_timeout_threshold))

            if self.sensor_tmtrig_thread == None:
                # Start Timeout_Detection thread
                self._logger.debug("Initializing Time Trigger")
                self.sensor_tmtrig_thread = TimeTrigger(1, "TimeTriggerThread", self.sensor_pin, self.sensor_timeout_threshold, self._logger, pCallback=self.printer_change_filament)
                self._logger.debug("Starting Time Trigger")
                self.sensor_tmtrig_thread.start()
                self._logger.info("Smart Filament Sensor has been started")

        self.code_sent = False

    def sensor_restart(self):
        if self.sensor_tmtrig_thread != None: #i.e. sensor_start has been already called
            if self.printer_paused: #if sensor has to be restarted and printer has been paused, then internal time of the Time Trigger must be resetted as well
                self.printer_paused = False
                self.sensor_tmtrig_thread.reset_timer()
            self.sensor_tmtrig_thread.set() #re-sets the time trigger
            self.code_sent = False
            self._logger.info("Smart Filament Sensor has been restarted")

    def sensor_pause(self):
        if self.sensor_tmtrig_thread != None:
            self.sensor_tmtrig_thread.release()
            self._logger.info("Smart Filament Sensor has been paused")

# Sensor callbacks
    # Send configured pause command to the printer to interrupt the print
    def printer_change_filament(self):
        # Check if stop signal was already sent
        if (not self.code_sent):
            self._logger.info("Smart Filament Sensor has detected no movement")
            self._logger.info("Send PAUSE command: " + self.pause_command)
            self._printer.commands(self.pause_command)
            self.code_sent = True

# Events
    def on_event(self, event, payload):

        if event is Events.PRINTER_STATE_CHANGED:
            if payload[u'state_string'] == 'Printing':
                self._logger.debug("%s: Printer has started printing" % (event))
                self._printer_isPrinting()

        elif event in (
            Events.PRINT_STARTED,
            Events.PRINT_RESUMED,
            Events.Z_CHANGE
        ):
            self._logger.info("%s: Resetting Smart Filament Sensor" % (event))
            self.sensor_restart() #starting or restarting


        # Disable sensor
        elif event in (
            Events.PRINT_DONE,
            Events.PRINT_FAILED,
            Events.PRINT_CANCELLED,
            Events.ERROR
        ):
            self._logger.info("%s: Pausing and disabling Smart Filament Sensor" % (event))
            self.sensor_pause() #pausing
            self.sensor_enabled = False #disabling

        # Disable motion sensor if paused
        elif event is Events.PRINT_PAUSED:
            self._logger.info("%s: Pausing Smart Filament Sensor" % (event))
            self.sensor_pause() #pausing
            self.printer_paused = True

# Plugin update methods
    def get_update_information(self):
        return dict(
            smartfilamentsensor = dict(
                displayName = "Smart Filament Sensor",
                displayVersion = self._plugin_version,

                # version check: github repository
                type = "github_release",
                user = "Gianlucorso",
                repo = "Octoprint-Smart-Filament-Sensor",
                current = self._plugin_version,

                # update method: pip
                pip = "https://github.com/Gianlucorso/Octoprint-Smart-Filament-Sensor/archive/master.zip"
            )
        )

__plugin_name__ = "Smart Filament Sensor"
__plugin_version__ = "1.0"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SmartFilamentSensor()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }



def __plugin_check__():
    try:
        import RPi.GPIO
    except ImportError:
        return False

    return True
