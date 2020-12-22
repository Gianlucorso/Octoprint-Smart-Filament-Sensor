# Octoprint-Smart-Filament-Sensor

[OctoPrint](http://octoprint.org/) plugin that lets integrate `Smart Filament Sensors` like `BigTreeTechs SmartFilamentSensor` directly to `RaspberryPi GPIO` pins. This enables that this sensor can also be used on 3D Printers, that do not have a `E0-Stop` like e.g. `Creality 1.1.4` Mainboard of `Ender 3`.

This work has been based on the work of [maocypher](https://github.com/maocypher) available at the `GitHub` repository [Octoprint-Smart-Filament-Sensor](https://github.com/maocypher/Octoprint-Smart-Filament-Sensor (see his repository for more details).
Also this `README` file has been filled with parts of his file.

## Required sensor

To use this plugin a `Filament Sensor` is needed that sends a toogling digital signal (0-1-0...) during movement.

This plugin can use the `GPIO.BOARD` or `GPIO.BCM` numbering scheme.

## Features

* Configurable GPIO pins.
* Support movement detection sensors, e.g. `Smart-Filament-Sensor`.
* Detect if filament is not moving anymore (jammed or runout)
    * Detection based on timeout
    * Alternative pausing commands if M600 is not supported by the printer

## Installation

* Manually using this URL: https://github.com/maocypher/Octoprint-Smart-Filament-Sensor/archive/master.zip
  * Access web interface of `Octoprint`
  * Click on the tab `Plugin Manager`
  * Click on `See more`
  *

After installation a restart of Octoprint is recommended.

## Configuration
### GPIO Pin
* Choose any free `GPIO` pin you for data usage, but I would recommend to use `GPIO` pins without special functionalities like e.g. `I2C` and simila
* Run the sensor only on `3.3V`, because `GPIO` pins don't like `5V` for a long time

### Detection time
Currently it is necessary to configure a maximum time period after which, if no filament movement is detected, the pause of the printer is triggered. This time could depended on the print speed and the maximum print line length. For starting - until I figured out how to estimate the best detection time - you can run a test print, in which you measure your maximum time and set this value.
The default value 45 seconds was estimated on max. print speed 10mm/s, for faster prints it could be smaller.

### Octoprint - Firmware & Protocol
Since currently `GCode` command `M600` is used to interrupt the print, it is recommended to add `M600` to the setting `Pausing commands`.
There are also alternative pausing commands, like `M0, M1, M25, M226, M600, M601` available, for those whose printer don't support `M600`.

## GCode
### Start GCode
Since the sensor is activated with the first G0 or G1 command it is adviced to perform these commands after complete heatup of the printer.

E.g.
```
; Ender 3 Custom Start G-code
M140 S{material_bed_temperature_layer_0} ; Set Heat Bed temperature
M190 S{material_bed_temperature_layer_0} ; Wait for Heat Bed temperature
M104 S160; start warming extruder to 160
G28 ; Home all axes
G29 ; Auto bed-level (BL-Touch)
G92 E0 ; Reset Extruder
M104 S{material_print_temperature_layer_0} ; Set Extruder temperature
M109 S{material_print_temperature_layer_0} ; Wait for Extruder temperature
G1 X0.1 Y20 Z0.3 F5000.0 ; Move to start position
; G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed
G1 X0.4 Y200.0 Z0.3 F5000.0 ; Move to side a little
G1 X0.4 Y20 Z0.3 F1500.0 E30 ; Draw the second line
G92 E0 ; Reset Extruder
G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed
; End of custom start GCode
```

## Disclaimer
* I as author of this plugin am not responsible for any damages on your print or printer. As user you are responsible for a sensible usage of this plugin.
* Be cautious not to damage your Raspberry Pi, because of wrong voltage. I don't take any responsibility for wrong wiring.
