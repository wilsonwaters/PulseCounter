# PulseCounter
Measure pulse based meters such as power and water flow meters on Raspberry Pi

Can read pulses from power meters and save a value for instantanious consumption and accumulated kWh. Saves current values to a file for reading by other applications (I use Zabbix for monitoring). Also posts to a URL, which can be used by emoncms or PVOutput.

# Usage
- Requires python3, RPi.GPIO
- copy pulseCounter.py to /usr/local/bin/pulseCounter.py
- set permissions to alow execute
- copy pulseCounter-init to /etc/init.d/
- configure systemv to run pulseCounter on startup

# Settings
Configuratble settings are editable in the script.
- isGPIOInturruptMode: true = Use inturrupts to trigger. Othewise use polling (I have found inturrupt mode to be unreliable, probably due to signal noise)
- pollingInterval: If using polling mode, set the inteval. This should be based off the minimum expected pulse time and halved 0.05 is a good value for 1 pulse per Wh i.e. 10 pulses per second = 36kWh. Double for Nyquist 20, interval = 0.05s
- URLPoster:interval: seconds between pushed updates to a URL
- PVOutputPoster:pvoutputAPIKey and pvoutputSystemId: Required for sending values to pvOutput 

