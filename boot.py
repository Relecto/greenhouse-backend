# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)

import network
import hw_info

def do_ap():
    ap = network.WLAN(network.AP_IF) 

    ap.config(essid=hw_info.NAME) 
    ap.config(max_clients=10) 
    ap.active(True) 

do_ap()
#do_connect()

print(hw_info.NAME)
