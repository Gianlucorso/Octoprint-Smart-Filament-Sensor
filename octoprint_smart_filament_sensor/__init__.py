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
        self.printer_init = False

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
        if(self.mode == 0):
            self._logger.info("Using Board Mode")
            GPIO.setmode(GPIO.BOARD)
        else:
            self._logger.info("Using BCM Mode")
            GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.sensor_pin, GPIO.IN)
        GPIO.add_event_detect(self.sensor_pin, GPIO.BOTH, callback=self._init_printer) #used to avoid triggering the smart filament sensor before printer has actually started printing

        if self.sensor_enabled == False:
            self._logger.info("Smart Filament Sensor has been disabled")

        self.sensor_tmtrig_thread = None

    def _init_printer(self, pPin):
        self.printer_init = True
        self._logger.debug("Printer is initialized")
        GPIO.remove_event_detect(self.sensor_pin) #no need to keep monitoring this pin

    def on_after_startup(self):
        self._logger.info("Smart Filament Sensor started (on startup)")
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

# Sensor methods
    def sensor_start(self):
        self._logger.debug("Smart Filament Sensor enabled: " + str(self.sensor_enabled))

        if self.sensor_enabled:

            if (self.mode == 0):
                self._logger.debug("GPIO mode: Board Mode")
            else:
                self._logger.debug("GPIO mode: BCM Mode")

            self._logger.debug("GPIO pin: " + str(self.sensor_pin))

            if self.sensor_tmtrig_thread == None: #start
                self._logger.debug("Timeout Threshold: " + str(self.sensor_timeout_threshold))

                # Start Timeout_Detection thread
                self.sensor_tmtrig_thread = TimeTrigger(
                    1, "TimeTriggerThread", self.sensor_pin,
                    self.sensor_timeout_threshold,
                    self._logger,
                    pCallback=self.printer_change_filament)
                self.sensor_tmtrig_thread.start()
                self._logger.info("Smart Filament Sensor has been started")
            else: #set
                self.sensor_tmtrig_thread.set()
                self._logger.info("Smart Filament Sensor has been restarted")

        self.code_sent = False

    def sensor_pause(self):
        if (self.sensor_enabled and self.sensor_tmtrig_thread != None):
            self.sensor_tmtrig_thread.release()
        self._logger.info("Smart Filament Sensor has been paused")

# Sensor callbacks
    # Send configured pause command to the printer to interrupt the print
    def printer_change_filament (self):
        # Check if stop signal was already sent
        if (not self.code_sent):
            self._logger.debug("Smart Filament Sensor has detected no movement")
            self._logger.info("Send PAUSE command: " + self.pause_command)
            self._printer.commands(self.pause_command)
            self.code_sent = True

# Events
    def on_event(self, event, payload):

        if event in (
            Events.PRINT_STARTED,
            Events.PRINT_RESUMED,
            Events.Z_CHANGE
        ):
            if self.printer_init:
                if self.sensor_tmtrig_thread == None:
                    self._logger.info("%s: Starting Smart Filament Sensor." % (event))
                else:
                    self._logger.info("%s: Restarting Smart Filament Sensor." % (event))
                self.sensor_start() #starting or restarting

        # Disable sensor
        elif event in (
            Events.PRINT_DONE,
            Events.PRINT_FAILED,
            Events.PRINT_CANCELLED,
            Events.ERROR
        ):
            self._logger.info("%s: Pausing and disabling Smart Filament Sensor." % (event))
            self.sensor_pause() #pausing
            self.sensor_enabled = False #disabling

        # Disable motion sensor if paused
        elif event is Events.PRINT_PAUSED:
            self._logger.info("%s: Pausing Smart Filament Sensor." % (event))
            self.sensor_pause() #pausing

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
