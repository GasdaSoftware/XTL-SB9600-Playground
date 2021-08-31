#
#   This script listens for any SB9600/SBEP messages, and tries to decode them
#    
#   the xtl.processMsg() function is where the main handling of messages is done
#
import logging
import sb9600
import xtl5000
import time
from virt_head import VirualHead

logging.basicConfig(handlers=[logging.FileHandler(filename="./debug.txt", 
                                                 encoding='utf-8', mode='a+')],
                    format="%(asctime)s %(name)s:%(levelname)s:%(message)s", 
                    level=logging.INFO)
logger = logging

logger.info('Started')

bus = sb9600.Serial("COM12")
xtl = xtl5000.XTL(bus)

bus.ser.flush()

lastBusy = 0
xtl.Reset()
try:
    vh = VirualHead()
    in_sbep = False
    while True:
        # Decode serial message
        if bus.ser.in_waiting > 0:
            #print('======================')
            while bus.isBusy():
                # Collect mesages while SB900 BUSY line is set
                pass            
            msg_head = bus.read(5)
            # Check if SBEP
            #if msg_head[0] == 0x1f:
            #    in_sbep = True
            #    print('Still in SBEP')
            if in_sbep:
                in_sbep = False
                msg_len_orig = msg_head[2]
                msg_len = msg_len_orig - 2
                if msg_len < 0:
                    msg_len = msg_len_orig
                #print("Length {} buffer size {}".format(msg_len, bus.ser.in_waiting))
                msg_body = bus.read(msg_len)
                real_len = len(msg_body)
                # print("Asking for {}({}) got {}".format(msg_len, msg_len_orig,real_len ))
                if msg_len != real_len:
                    print('ERROR>>>>>>>>>')
                msg = msg_head + msg_body
                #print("SBEP   Raw Msg: {}".format(sb9600.hexlify(msg, ' ')))
                xtl.processMsg(msg, vh)
            elif msg_head[0] == 0x00 and msg_head[3] == 0x06:
                in_sbep = True
                #print("SBEP 1 Raw Msg: {}".format(sb9600.hexlify(msg_head, ' ')))
                xtl.processMsg(msg_head, vh)
            else:
                #print("       Raw Msg: {}".format(sb9600.hexlify(msg_head, ' ')))
                xtl.processMsg(msg_head, vh)
        # time.sleep(0.05)
        vh.display_channel()
except KeyboardInterrupt:
    try:
        vh.thread.cancel()
    except:
        pass
    exit(0)