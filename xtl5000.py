# XTL Controller class
# 
# Original work copyright (C) 2014 Paul Banks (http://paulbanks.org)
#
# Modified for use with XTL series SB9600/SBEP commands by W3AXL
#

import logging

from time import sleep
from binascii import hexlify, unhexlify, b2a_uu
import sb9600

logger = logging.getLogger(__name__)

# Addressable modules
MODULE_BCAST = 0
MODULE_RADIO = 1
MODULE_FRONTPANEL = 5

# SBEP module codes
sbep_modules = {
    'BCAST': 0x00,
    'RADIO': 0x01,
    'PANEL': 0x05
}

# Lamp mappings
lamps_map = {
    "L1": 0x0D, "L2RED": 0x0B, "L2GREEN": 0x0C, "L3": 0x01, "L4": 0x02, "L5":
    0x04, "L5B": 0x05, "L6": 0x10, "L7": 0x07, "L8": 0x11, "L9": 0x12, "L10":
    0x13, "L11": 0x0E, "L12": 0x0F, "L13": 0x14, "L14": 0x15, "L15": 0x16,
    "L16": 0x17, "L17": 0x18, "L18": 0x19,
}

# Lamp attributes
LAMP_OFF = 0
LAMP_ON = 1
LAMP_FLASH = 2

# Illumination addresses
ILLUM_MIC = 1  # TODO: A guess - I didn't have a mic attached to verify it!
ILLUM_DISPLAY = 2
ILLUM_BUTTONS = 3

# Control values
BUTTON_DOWN = 1
BUTTON_UP = 0


class XTL:
    """XTL5000 Controller"""

    # O5 Button definitions
    button_map_o5 = {
        'ptt': 0x01,
        'hub': 0x06,
        'knob_vol': 0x02,
        'knob_chan': 0x04,
        'btn_light': 0x54,
        'btn_dp_lf': 0x80,
        'btn_home': 0x81,
        'btn_dp_rg': 0x82,
        'btn_key_1': 0x83,
        'btn_key_3': 0x84,
        'btn_key_5': 0x85,
        'btn_dp_up': 0x87,
        'btn_dp_dn': 0x88,
        'btn_key_2': 0x89,
        'btn_key_4': 0x8A,
        'btn_emgcy': 0x94
    }

    # O5 display icon definitions
    display_icons_o5 = {
        'monitor': 0x01,
        'secure': 0x02,
        'scan': 0x04,
        'direct': 0x07,
        'led_amber': 0x0f,
        'led_red': 0x10,
        'aes' : 0x55,
        'low_power': 0x56,
    }

    # O5 display subdevices
    display_subdev_o5 = {
        'text_zone': 0x00,
        'text_channel': 0x01,
        'text_softkeys': 0x02
    }

    def __init__(self, bus, head='O5'):
        self.bus = bus
        self.head = head
        self.inSBEP = False

    def processMsg(self,msg, vh):
        """Process SB9600/SBEP message and decode to human-readable text

        Args:
            msg (byte[]): string of bytes for message
        """

        # Decode by device address
        logger.debug("RAW RECVD<: {}".format(hexlify(msg, ' ')))
        # Handle SBEP first
        if self.inSBEP:
            # reset
            self.inSBEP = False
            # get important bits
            address = msg[0]
            subaddr = msg[1]
            length = msg[2]
            opcode = msg[4]         
            # Get data based on length
            data = msg[8:length+2]

            # Process message type

            # Display Address
            if address == 0x1f:
                # get display subdevice
                subdev = msg[6]
                subdevName = self.getDisplaySubDev(subdev)
                # print data payload
                subdevData = data.decode('ascii').rstrip('\x00')
                logger.info(f'RECVD<: Set {subdevName} to {subdevData}')
                vh.add_note("RECVD<: Set {} to {}".format(subdevName,subdevData))
                if subdevName == 'text_zone':
                    vh.set_text_zone(subdevData)
                elif subdevName == 'text_channel':
                    vh.set_text_channel(subdevData)
                elif subdevName == 'text_softkeys':
                    vh.set_softkeys(subdevData)
                # return
                return

            # Display icon update 
            elif address == 0xf4:
                # get icon
                icon = self.getDisplayIcon(msg[3])
                # get state
                if opcode == 0x00:
                    state = "off"
                elif opcode == 0x01:
                    state = "on"
                elif opcode == 0x02:
                    state = "on"
                elif opcode == 0xFE:
                    state = "blink"
                else:
                    state = str(opcode)
                vh.add_note("RECVD<: {} icon {}".format(icon, state))
                vh.set_icon(icon, state)
                logger.info(f'ICON {icon} {msg[3]} STATE {state} {opcode}')
                return

            # Fallback to printing raw message
            else:
                logger.info("RECVD<: SBEP decoded")
                logger.info("        Raw Msg: {}".format(hexlify(msg, ' ')))
                logger.info("        Address: {}, Subaddr: {}, Length: {}, Opcode: {}".format(hex(address), hex(subaddr), length, hex(opcode)))
                return

        # SB9600 parameters
        addr = msg[0]
        try:
            param1 = msg[1]
        except IndexError:
            param1 = ''  
        try:  
            param2 = msg[2]
        except IndexError:
            param2 = ''
        try:
            function = msg[3]
        except IndexError:
            function = ''

        # broadcast module
        if addr == 0x00:
            # SBEP command
            if function == 0x06:
                self.inSBEP = True
                # Get speed
                if param1 == 0x12:
                    speed = 9600
                else:
                    speed = param1
                # Get module name
                module = self.getSbepModule(param2)
                # print("RECVD<: Entering SBEP mode to {} at {} baud".format(module, speed))
                return

        # front panel module
        if addr == 0x05:
            # button / knob
            if function == 0x57:
                # lookup button
                btn = self.getButton(param1)
                if btn is not None and "knob" in btn:
                    if 'knob_vol' == btn:
                        vh.set_volume(param2)
                    logger.info("RECVD<: {} clicks: {}".format(btn,param2))
                    return
                else:
                    if param2 == 0x01:
                        logger.info("RECVD<: {} pressed".format(btn))
                        return
                    else:
                        logger.info("RECVD<: {} release".format(btn))
                        return
            # backlighting / illumination
            elif function == 0x58:
                # display BL
                if param1 == 0x02:
                    logger.info("RECVD<: Display BL set to {}".format(param2))
                    return
                elif param1 == 0x03:
                    logger.info("RECVD<: Button BL set to {}".format(param2))
                    return

        # radio module
        elif addr == 0x01:
            # audio device
            if function == 0x1D:
                if param2 == 0x01:
                    vh.add_note("RECVD<: Audio unmuted")
                    vh.set_unmute()
                    return
                elif param2 == 0x00:
                    vh.add_note("RECVD<: Audio muted")
                    vh.set_mute()
                    return
            # channel change cmd device?
            if function == 0x1f:
                logger.info("RECVD<: Goto CH {}".format(param2))
                return
            # channel change ack device?
            if function == 0x60:
                logger.info("RECVD<: CH change {} ACK".format(param2))
                return

        # default to just printing the message if we didn't do anything else
        logger.info("RECVD<: {}".format(hexlify(msg, ' ')))

    def getButton(self, code):
        """Lookup button by opcode

        Args:
            code (byte): button opcode

        Raises:
            ValueError: if control head invalid

        Returns:
            string: button name
        """
        if self.head == 'O5':
            for key, value in self.button_map_o5.items():
                if code == value:
                    return key
            return "{} (Unknown)".format(hex(code))
        else:
            raise ValueError("Invalid head specified")

    def getSbepModule(self, code):
        """Lookup SBEP module by hex code

        Args:
            code (byte): module code

        Returns:
            string: module name
        """
        for key, value in sbep_modules.items():
            if code == value:
                return key
        return "{} (Unknown)".format(hex(code))

    def getDisplaySubDev(self, code):
        """Lookup display subdevice by hex code

        Args:
            code (byte): module code

        Raises:
            ValueError: if control head invalid

        Returns:
            string: subdevice name
        """
        if self.head == 'O5':
            for key, value in self.display_subdev_o5.items():
                if code == value:
                    return key
            return "{} (Unknown)".format(hex(code))
        else:
            raise ValueError("Invalid head specified")

    def getDisplayIcon(self, code):
        """Lookup display icon by hex code

        Args:
            code (byte): icon code

        Raises:
            ValueError: if control head invalid

        Returns:
            string: icon name
        """
        if self.head == 'O5':
            for key, value in self.display_icons_o5.items():
                if code == value:
                    # print('DISP ICON', key)
                    return key
            return "{} (Unknown)".format(hex(code))
        else:
            raise ValueError("Invalid head specified")

    def CSQ(self):
        """Enter CSQ mode"""
        self.bus.sb9600_send(MODULE_RADIO, 0x02, 0, 0x40)

    def Reset(self):
        self.bus.sb9600_send(MODULE_BCAST, 0x00, 0x01, 0x08)

    def SBEP(self, module):
        """Enter SBEP mode"""
        self.bus.sb9600_send(MODULE_BCAST, 0x12, module, 0x06)
        self.bus.sbep_enter()

    def setChannel(self, channel):
        if channel in range(255):
            self.bus.sb9600_send(MODULE_RADIO, 0x00, channel, 0x1f)
            self.bus.sb9600_send(MODULE_RADIO, 0x01, channel, 0x60)
        else:
            raise ValueError("Channel index out of range")

    def sendButton(self, code, value):
        self.bus.sb9600_send(MODULE_FRONTPANEL, code, value, 0x57)

    def Display(self, text, offset=0):
        """Send text to display"""

        if len(text) > 14:
            raise ValueError("Text too long!")

        # Build display message
        #msg = bytes((0x80, 0x00, len(text), 0x00, offset))
        msg = bytes((0x80, len(text), len(text), 0x01, offset))
        msg += bytes(text, "ASCII")
        msg += b"\x00" * len(text)  # Character attributes

        # Send it
        self.SBEP(MODULE_FRONTPANEL)
        self.bus.sbep_send(0x01, msg)
        self.bus.sbep_leave()

    def Lamp(self, lamp, function):
        """Switch on/off/flash lamp"""
        # If lamp is not an integer, use it as key to look up lampID in map
        if not isinstance(lamp, int):
            lamp = lamps_map[lamp]
        self.SBEP(MODULE_FRONTPANEL)
        self.bus.sbep_send(0x21, bytes((0x01, lamp, function)))
        self.bus.sbep_leave()

    def Illumination(self, illum, level):
        """Change level of illumination"""
        self.bus.sb9600_send(MODULE_FRONTPANEL, illum, level, 0x58)

    def Control(self, controlid, value):
        """Indicate a control use"""
        self.bus.sb9600_send(MODULE_FRONTPANEL, controlid, value & 0xFF, 0x57)

    def ReadEEPROM(self, module, startaddr, endaddr, callback=None):
        """Read EEPROM data. Note: you'll need to reset the radio after this!"""
        self.CSQ()
        self.bus.wait_for_quiet()

        # Select device? (TODO: What is this?)
        # You'll need to reset the radio after this command
        self.bus.sb9600_send(MODULE_BCAST, module, 0x01, 0x08)

        # Must wait some time before entering SBEP mode
        sleep(0.5)
        self.SBEP(MODULE_RADIO)

        # Read the data
        eedata = b''
        chunklen = 0x40
        for addr in range(startaddr, endaddr, chunklen):
            msg = bytes(
                (chunklen, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF))
            self.bus.sbep_send(0x11, msg)
            op, data = self.bus.sbep_recv()
            if op == 0x80:  # Reply is EEPROM data
                addr_rx = data[0] << 16 | data[1] << 8 | data[2]
                if addr_rx != addr:
                    raise RuntimeError(
                        "Unexpected address in reply addr=0x%x" % addr_rx)
                if len(data[3:]) != chunklen:
                    raise RuntimeError("Unexpected data length!")
                eedata += data[3:]
            else:
                raise RuntimeError("Unexpected reply op=%d" % op)

            # Notify of progress
            if callback:
                callback(addr)

        # Done with SBEP mode
        self.bus.sbep_leave()

        return eedata

    def Audio(self, enable):
        enable = 1 if enable else 0
        self.bus.sb9600_send(MODULE_RADIO, 0x00, enable, 0x1D)

    def SetRXFrequency(self, frequency):
        """Set the receiver frequency"""
        ch = int((frequency*1E6 / 6250) - 60000)
        self.bus.sb9600_send(0x03, (ch >> 8) & 0xFF, ch & 0xFF, 0x3F)

    def SetTXFrequency(self, frequency):
        """Set the transmitter frequency"""
        ch = int((frequency*1E6 / 6250) - 60000)
        self.bus.sb9600_send(0x02, (ch >> 8) & 0xFF, ch & 0xFF, 0x3F)

    def printMsg(self, source, msg):
        print("{: >10} >>: {}".format(source, msg))
