# PulseCounter
Measure pulse based meters such as power and water flow meters on Raspberry Pi

Can read pulses from power meters and save a value for instantanious consumption and accumulated kWh. Saves current values to a file for reading by other applications (I use Zabbix for monitoring). Also posts to a URL, which can be used by emoncms or PVOutput.

# Usage
- sudo apt-get install python3 rpi.gpio
- git clone https://github.com/wilsonwaters/PulseCounter.git
- cd PulseCounter
- sudo cp pulseCounter.py /usr/local/bin/pulseCounter.py
- sudo chmod 755 /usr/local/bin/pulseCounter.py
- cp pulseCounter-init /etc/init.d/pulseCounter
- sudo chmod 755 /etc/init.d/pulseCounter
- sudo update-rc.d pulseCounter defaults
- sudo /etc/init.d/pulseCounter start

# Settings

By default, the script uses GPIO pin 17 (raspberry pi pin 11). The script enables the internal pull-down resistor, which means we expect a positive pulse.

Configuratble settings are editable in the script.
- isGPIOInturruptMode: true = Use inturrupts to trigger. Othewise use polling (I have found inturrupt mode to be unreliable, probably due to signal noise)
- pollingInterval: If using polling mode, set the inteval. This should be based off the minimum expected pulse time and halved 0.05 is a good value for 1 pulse per Wh i.e. 10 pulses per second = 36kWh. Double for Nyquist 20, interval = 0.05s
- URLPoster:interval: seconds between pushed updates to a URL
- PVOutputPoster:pvoutputAPIKey and pvoutputSystemId: Required for sending values to pvOutput 

# Output
By default the current count is saved to /tmp/pulseCounterCount. This value wrapps to zero at the end of every day. You can use zabbix or any other monitoring application to read this value. The last value saved on shutdown so you can continue the count where it left off.

# Electronics
You will need to get the pulses into your raspberry pi somehow! I made a simple transister switch circuit with an LDR "looking at" our power meter. The digital input is high when the LED is lit. It also has a potentiometer to adjust the sensitivity. There's plenty of example circuits on the 'net. If there's a demand I'll take some photos of my setup and the circuit diagram.

# Warning
Use at your own risk. "It works for me". This is very much an afternoon hackjob and is far from good code :) You will probaly need to get into some python code to make this work for you.
