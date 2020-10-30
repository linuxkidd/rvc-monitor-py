# rvc-monitor-py
RV-C Monitor - Python Edition

Enables two-way communication between an RV's CAN-Bus network and an MQTT message broker:

- Monitor and decode [RV-C CAN-Bus protocol](http://www.rv-c.com/?q=node/75), and
publish to MQTT as JSON data.
- Receive RV-C commands over MQTT from other applications and send them to the CAN-Bus.


```
usage: rvc2mqtt.py [-h] [-b BROKER] [-d {0,1,2}] [-i INTERFACE] [-m {0,1,2}]
                   [-o {0,1}] [-s SPECFILE] [-t TOPIC]

optional arguments:
  -h, --help            show this help message and exit
  -b BROKER, --broker BROKER
                        MQTT Broker Host
  -d {0,1,2}, --debug {0,1,2}
                        debug data
  -i INTERFACE, --interface INTERFACE
                        CAN interface to use
  -m {0,1,2}, --mqtt {0,1,2}
                        Send to MQTT, 1=Publish, 2=Retain
  -o {0,1}, --output {0,1}
                        Dump parsed data to stdout
  -s SPECFILE, --specfile SPECFILE
                        RVC Spec file
  -t TOPIC, --topic TOPIC
                        Set top-level MQTT topic (default: "RVC")
```

## Requirements

* A computer with a CAN-Bus interface. This will usually be a
Raspberry Pi 3B with a PiCAN2 board. Install the canbus utilities:
  ~~~
  sudo apt -y install can-utils
  ~~~
  Add the following to the end of /boot/config.txt to enable the canbus card:
  ~~~
  dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
  ~~~
* Python packages:
  ~~~
  pip3 install python-can paho-mqtt ruamel.yaml
  ~~~
* An MQTT message broker, such as Mosquitto.
  ~~~
  sudo apt -y install mosquitto
  ~~~

