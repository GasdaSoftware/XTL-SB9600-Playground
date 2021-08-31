import logging
import os
from threading import Timer

logger = logging.getLogger(__name__)

class VirualHead:
    def __init__(self):
        self.last_notes = []
        self.last_notes_max = 100
        self.display_last_notes_max = 10
        self.text_zone = 'INITIALIZE    '
        self.text_channel = 'DISPLAY       '
        self.mute = True
        self.mute_display_chars = ('|', '-')
        self.unmute_display_chars = ('*', '=')
        self.refresh_display = True
        self.icons = dict()
        self.softkeys = []
        self.volume = None

    def set_volume(self, volume_val):
        if volume_val != self.volume:
            self.refresh_display = True
        self.volume = volume_val

    def get_volume_line(self):
        # Volume is 0 - 255
        # lets break it into 20 hashs
        total_hash = 20
        hash_amount = int(255 / total_hash)
        if hash_amount > total_hash:
            hash_amount = total_hash
        hash_ct = int(self.volume / hash_amount)
        vol_line = '#' * hash_ct
        vol_line += '-' * (total_hash - hash_ct)
        return f'[{vol_line}]'

    def set_icon(self, icon_id, icon_state):
        icon_id_str = str(icon_id)
        last_state = self.icons.get(icon_id_str)
        if last_state is not icon_state:
            self.refresh_display = True
        self.icons[icon_id_str] = icon_state
        

    def get_icon_bar(self):
        # Secure = 
        secure = '        '
        secure_var = self.icons.get('secure')
        if secure_var == 'on':
            secure = '[SECURE]'
        elif secure_var == 'blink':
            secure = '*SECURE*'

        # AES
        aes = '     '
        aes_var = self.icons.get('aes')
        if aes_var == 'on':
            aes = '[AES]'
        elif aes_var == 'blink':
            aes = '*AES*'

        # SCAN
        scan = '      '
        scan_var = self.icons.get('scan')
        if scan_var == 'on':
            scan = '[SCAN]'
        elif scan_var == 'blink':
            scan = '*SCAN*'

        # DIRECT
        direct = '     '
        direct_var = self.icons.get('direct')
        if direct_var == 'on':
            direct = '[DIR]'

        # MONITOR
        monitor = '     '
        monitor_var = self.icons.get('monitor')
        if monitor_var == 'on':
            monitor = '[MON]'
        return f'{monitor} {secure} {aes} {scan} {direct}'
        

    def set_softkeys(self,key_string):
        s_key_data = key_string.split('^')
        s_key_data.pop(0) # drop the first one
        self.softkeys.clear()
        for val in s_key_data:
            logger.info(f'Adding to soft key [{val}]')
            self.softkeys.append(f'[{val: <4}]')


    def get_softkey_bar(self):
        return ' '.join(self.softkeys)

    def  setup_display_refresh(self):
        self.thread = Timer(5.0, self.set_refresh_display)
        self.thread.start()
 
    def set_refresh_display(self):
        self.setup_display_refresh()

        self.refresh_display = True

    def set_text_zone(self, text):
        if self.text_zone != text:
            self.text_zone = text.rstrip()
            self.refresh_display = True

    def set_text_channel(self, text):
        if self.text_channel != text:
            self.text_channel = text.rstrip()
            self.refresh_display = True

    def set_mute(self):
            self.mute = True
            self.refresh_display = True

    def set_unmute(self):
            self.mute = False
            self.refresh_display = True

    def add_note(self,text):
        if len(self.last_notes) >= self.last_notes_max:
            self.last_notes.pop(0)
        self.last_notes.append(text)

    def display_channel(self):
        if not self.refresh_display:
            return
        self.refresh_display = False
        # clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')

        
        if self.mute:
            print("")
            print(self.get_icon_bar())
            print('+{}+'.format(self.mute_display_chars[1] * 32))
            print('| ZONE    : {:20} |'.format(self.text_zone))
            print('| CHANNEL : {:20} |'.format(self.text_channel))
            print('+{}+'.format(self.mute_display_chars[1] * 32))
        else:
            print("[BUSY]")
            print(self.get_icon_bar())
            print('*{}*'.format(self.unmute_display_chars[1] * 32))
            print('~ ZONE    : {:20} ~'.format(self.text_zone))
            print('~ CHANNEL : {:20} ~'.format(self.text_channel))
            print('*{}*'.format(self.unmute_display_chars[1] * 32))
        print(self.get_softkey_bar())
        if self.volume is not None:
            print('VOLUME :   ', self.get_volume_line())
        print('\n')
        