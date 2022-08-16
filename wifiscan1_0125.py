import pywifi
import time
import csv
import numpy as np
import pandas as pd

rpi = 'rpi121'
timestamp = time.strftime("%m-%d-%Y-%I:%M:%S")



def ieee80211_freq_khz_to_channel(freq):

    ##/* TODO: just handle MHz for now */
    ##freq = KHZ_TO_MHZ(freq);

    ##/* see 802.11 17.3.8.3.2 and Annex J */
    if (freq == 2484):
        return int(14);
    elif (freq < 2484):
        return int((freq - 2407) / 5);
    elif (freq >= 4910 and freq <= 4980):
        return int((freq - 4000) / 5);
    elif (freq < 5925):
        return int((freq - 5000) / 5);
    elif (freq == 5935):
        return int(2);
    elif (freq <= 45000): ##/* DMG band lower limit */
        ##/* see 802.11ax D6.1 27.3.22.2 */
        return int((freq - 5950) / 5);
    elif (freq >= 58320 and freq <= 70200):
        return int((freq - 56160) / 2160);
    else:
        return int(0);

def wifi_scan():
    list_curtime = []
    list_bssid = []
    list_ssid = []
    list_channel = []

    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    iface.scan()
    time.sleep(0.5)
    results = iface.scan_results()
    curtime = time.strftime("%I:%M:%S")
    list_curtime.append(curtime)

    for i in results:
        if i.ssid == ('xxxxxxx') or i.ssid == ('xxxxxxx') or i.ssid == ('xxxxxxx') or i.ssid == ('xxxxxxx'):    ## Potential SSIDs
            channel = ieee80211_freq_khz_to_channel(i.freq)
            bssid = i.bssid
            ssid  = i.ssid
            list_bssid.append(bssid)
            list_ssid.append(ssid)
            list_channel.append(channel)

    L = sorted(set(list_channel))
    L_bssid = np.char.upper(list_bssid)
    print('AP Channels', L)

    return L, L_bssid


if __name__ == '__main__':
    while True:
        wifi_scan()
        time.sleep(5)
