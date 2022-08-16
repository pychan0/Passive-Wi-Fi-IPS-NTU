import time
import numpy as np
import pandas as pd
import datetime
import csv
import re

def check_serial_legitimate(line_input):
    # Check the serial input legitimate. If the input is unlegal then return None
    # Format: CH:%d,Mac:%%:%%:%%:%%:%%:%%,RSSI:%d,Seq:%d
    # Input: Example:"CH:2,MAC:00:0B:86:71:54:20,RSSI:-65,Seq:3630"
    # Output
        # 1. Channel:
        # 2. MAC:
        # 3. RSSI:
        # 4. Seq:
    try:
        MAC, RSSI, Seq, channel = line_input.split(',')
    except Exception as e:
        return None, None, None, None,
    channel = int(channel)
    RSSI = int(RSSI)
    Seq = int(Seq)
    if 0 > channel or channel > 161:
        return None, None, None, None,
    if -1 < RSSI or RSSI < -100:
        return None, None, None, None,
    if not re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", MAC.lower()):
        return None, None, None, None,
    return MAC, RSSI, Seq, channel
