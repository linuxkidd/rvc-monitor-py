#!/usr/bin/env python3

import argparse,array,can,json,os,queue,re,signal,threading,time
import ruamel.yaml as yaml

def signal_handler(signal, frame):
    global t
    print('')
    print('You pressed Ctrl+C!  Exiting...')
    print('')
    t.kill_received = True
    exit(0)

signal.signal(signal.SIGINT, signal_handler)

def on_mqtt_connect(client, userdata, flags, rc):
    if debug_level:
        print("MQTT Connected with code "+str(rc))
    client.subscribe([
        (mqttTopic + "/transmit/#", 0)
        ])

def on_mqtt_subscribe(client, userdata, mid, granted_qos):
    if debug_level:
        print("MQTT Sub: "+str(mid))

def on_mqtt_message(client, userdata, msg):
    topic=msg.topic[13:]
    if debug_level:
        print("Send CAN ID: "+topic+" Data: "+msg.payload.decode('ascii'))
    #can_tx(devIds[dev],[ commands[msg.payload.decode('ascii')] ])

# can_tx(canid, canmsg)
#    canid = numeric CAN ID, not string
#    canmsg = Array of numeric values to transmit
#           - Alternately, a string of two position hex values can be accepted
#
# Examples:
#   can_tx( 0x19FEDB99, [0x02, 0xFF, 0xC8, 0x03, 0xFF, 0x00, 0xFF, 0xFF] )
#   can_tx( 0x19FEDB99, '02FFC803FF00FFFF' )
#
def can_tx(canid,canmsg):
    if isinstance(canmsg, str):
        tmp = canmsg
        canmsg = [int(tmp[x:x+2],16) for x in range( 0, len(tmp), 2 )]
    msg = can.Message(arbitration_id=canid, data=canmsg, extended_id=True)
    try:
        bus.send(msg)
        if debug_level>0:
            print("Message sent on {}".format(bus.channel_info))
    except can.CanError:
        print("CAN Send Failed")

class CANWatcher(threading.Thread):
    def __init__(self):
      threading.Thread.__init__(self)
      # A flag to notify the thread that it should finish up and exit
      self.kill_received = False

    def run(self):
        while not self.kill_received:
            message = bus.recv()
            q.put(message)  # Put message into queue

def rvc_decode(mydgn,mydata):
    result = { 'dgn':mydgn, 'data':mydata, 'name':"UNKNOWN-"+mydgn }
    if mydgn not in spec:
        return result

    decoder = spec[mydgn]
    result['name'] = decoder['name']
    params = []
    try:
        params.extend(spec[decoder['alias']]['parameters'])
    except:
        pass

    try:
        params.extend(decoder['parameters'])
    except:
        pass

    param_count = 0
    for param in params:
        param['name'] = parameterize_string(param['name'])

        try:
            mybytes = get_bytes(mydata,param['byte'])
            myvalue = int(mybytes,16) # Get the decimal value of the hex bytes
        except:
            # If you get here, it's because the params had more bytes than the data packet.
            # Thus, skip the rest of the processing
            continue

        try:
            myvalue = get_bits(myvalue,param['bit'])
            if param['type'][:4] == 'uint':
                myvalue = int(myvalue,2)
        except:
            pass

        try:
            myvalue = convert_unit(myvalue,param['unit'],param['type'])
        except:
            pass

        result[param['name']] = myvalue

        try:
            if param['unit'].lower() == 'deg c':
                result[param['name']+' F'] = tempC2F(myvalue)
        except:
            pass

        try:
            mydef = 'undefined'
            mydef = param['values'][int(myvalue)]
            # int(myvalue) is a hack because the spec yaml interprets binary bits
            # as integers instead of binary strings.
            result[param['name'] + "_definition"] = mydef
        except:
            pass


        param_count += 1

    if param_count == 0:
        result['DECODER PENDING'] = 1

    return result

def get_bytes(mybytes,byterange):
    try:
        bset=byterange.split('-')
        sub_bytes = "".join(mybytes[i:i+2] for i in range(int(bset[1])*2, (int(bset[0])-1)*2, -2))
    except:
        sub_bytes = mybytes[ byterange * 2 : ( byterange + 1 ) * 2 ]

    return sub_bytes

def get_bits(mydata,bitrange):
    mybits="{0:08b}".format(mydata)
    try:
        bset=bitrange.split('-')
        sub_bits = mybits[ 7 - int(bset[1]) : 8 - int(bset[0]) ]
    except:
        sub_bits = mybits[ 7 - bitrange : bitrange + 1 ]

    return sub_bits

# Convert a string to something easier to use as a JSON parameter by
# converting spaces and slashes to underscores, and removing parentheses.
# e.g.: "Manufacturer Code (LSB) in/out" => "manufacturer_code_lsb_in_out"
def parameterize_string(string):
    return string.translate(string.maketrans(' /', '__', '()')).lower()

def tempC2F(degc):
    return round( ( degc * 9 / 5 ) + 32, 1 )

def convert_unit(myvalue,myunit,mytype):
    new_value = myvalue
    mu = myunit.lower()
    if mu == 'pct':
        if myvalue != 255:
            new_value = myvalue / 2

    elif mu == 'deg c':
        new_value = 'n/a'
        if mytype == 'uint8' and myvalue != ( 1 << 8 ) - 1:
            new_value = myvalue - 40
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( ( myvalue * 0.03125 ) - 273, 2 )

    elif mu == 'v':
        new_value = 'n/a'
        if mytype == 'uint8' and myvalue != ( 1 << 8 ) - 1:
            new_value = myvalue
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( myvalue * 0.05, 2 )

    elif mu == 'a':
        new_value = 'n/a'
        if mytype == 'uint8':
            new_value = myvalue
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( ( myvalue * 0.05 ) - 1600 , 2)
        elif mytype == 'uint32' and myvalue != ( 1 << 32 ) - 1:
            new_value = round( ( myvalue * 0.001 ) - 2000000 , 3)

    elif mu == 'hz':
        if mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( myvalue / 128 , 2)

    elif mu == 'sec':
        if mytype == 'uint8' and myvalue > 240 and myvalue < 251:
            new_value = ( ( myvalue - 240 ) + 4 ) * 60
        elif mytype == 'uint16':
            new_value = myvalue * 2

    elif mu == 'bitmap':
        new_value = "{0:b}".format(myvalue)

    return new_value

def main():
    retain=False
    if(mqttOut==2):
        retain=True

    def getLine():
        if q.empty():  # Check if there is a message in queue
            return

        message = q.get()
        if debug_level>0:
            print("{0:f} {1:X} ({2:X}) ".format(message.timestamp, message.arbitration_id, message.dlc),end='',flush=True)

        canID = "{0:b}".format(message.arbitration_id)
        prio  = int(canID[0:3],2)
        dgn   = "{0:05X}".format(int(canID[4:21],2))
        srcAD = "{0:02X}".format(int(canID[24:],2))

        if debug_level>0:
            print("DGN: {0:s}, Prio: {1:d}, srcAD: {2:s}, Data: {3:s}".format(
                dgn,prio,srcAD,", ".join("{0:02X}".format(x) for x in message.data)))

        myresult=rvc_decode(dgn,"".join("{0:02X}".format(x) for x in message.data))

        if screenOut>0:
            print(json.dumps(myresult))

        if mqttOut:
            topic = mqttTopic + "/" + myresult['name']
            try:
                topic += "/" + str(myresult['instance'])
            except:
                pass
            mqttc.publish(topic,json.dumps(myresult),retain=retain)

    def mainLoop():
        if mqttOut:
            mqttc.loop_start()
        while True:
            getLine()
            time.sleep(0.001)
        if mqttOut:
            mqttc.loop_stop()
    mainLoop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--broker", default = "localhost", help="MQTT Broker Host")
    parser.add_argument("-d", "--debug", default = 0, type=int, choices=[0, 1, 2], help="debug data")
    parser.add_argument("-i", "--interface", default = "can0", help="CAN interface to use")
    parser.add_argument("-m", "--mqtt", default = 0, type=int, choices=[0, 1, 2], help="Send to MQTT, 1=Publish, 2=Retain")
    parser.add_argument("-o", "--output", default = 0, type=int, choices=[0, 1], help="Dump parsed data to stdout")
    parser.add_argument("-s", "--specfile", default = "/etc/rvc/rvc-spec.yml", help="RVC Spec file")
    parser.add_argument("-t", "--topic", default = "RVC", help="MQTT topic prefix")
    args = parser.parse_args()

    debug_level = args.debug
    mqttOut = args.mqtt
    screenOut = args.output
    mqttTopic = args.topic

    if mqttOut:
        import paho.mqtt.client as mqtt
        broker_address=args.broker
        mqttc = mqtt.Client() #create new instance
        mqttc.on_connect = on_mqtt_connect
        mqttc.on_subscribe = on_mqtt_subscribe
        mqttc.on_message = on_mqtt_message

        try:
            print("Connecting to MQTT: {0:s}".format(broker_address))
            mqttc.connect(broker_address, port=1883) #connect to broker
        except:
            print("MQTT Broker Connection Failed")

    try:
        print("Connecting to CAN-Bus interface: {0:s}".format(args.interface))
        bus = can.interface.Bus(channel=args.interface, bustype='socketcan_native')
    except OSError:
        print('Cannot find interface.')
        exit()

    print("Loading RVC Spec file {}.".format(args.specfile))
    with open(args.specfile,'r') as specfile:
        try:
            spec=yaml.round_trip_load(specfile)
        except yaml.YAMLError as err:
            print(err)
            exit(1)

    print("Processing start...")

    q = queue.Queue()
    t = CANWatcher()	# Start CAN receive thread
    t.start()

    main()
