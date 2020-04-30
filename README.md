# domoticz_tahoma_blind
Domoticz plugin writen in Python to support Velux roller shutters using Tahoma/Connexoon

To use this plugin you need to install the last stable release of Domoticz https://www.domoticz.com and to install the required python library.

The plugin currently support the following device types: roller Shutters, screens (interior/exterior), awning, pergolas, garage door, windows and blinds(postions only, no slats control).

This plugins use some from https://github.com/moroen/IKEA-Tradfri-plugin, thanks @moroen for the first free function.

## Installation

Python version 3.4 or higher required & Domoticz version 4.10717 or greater. To install:

Go in your Domoticz directory using a command line and open the plugins directory.

Run: git clone https://github.com/nonolk/domoticz_tahoma_blind.git

Restart Domoticz with sudo systemctl restart domoticz.

In the web UI, navigate to the Hardware page. In the hardware dropdown list there will be an entry called "Tahoma or conexoon IO blind plugin".
