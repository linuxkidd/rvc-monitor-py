# rvc-monitor-py
RV-C Monitor - Python Edition

Monitor and decode [RV-C CAN-Bus protocol](http://www.rv-c.com/?q=node/75), and publish to MQTT

```
usage: rvc2mqtt.py [-h] [-b BROKER] [-d {0,1,2}] [-i INTERFACE] [-m {0,1,2}]
                   [-o {0,1}] [-s SPECFILE]

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
  -t TOPIC, --topic TOPIC
                        Set top-level MQTT topic (default: "RVC")
  -o {0,1}, --output {0,1}
                        Dump parsed data to stdout
  -s SPECFILE, --specfile SPECFILE
                        RVC Spec file
```
