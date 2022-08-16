import asyncio
import socketio
import argparse
import threading, time, sys, serial
import numpy as np
import pandas as pd
import datetime
import csv
import re
from utils import check_serial_legitimate
from serial_asyncio import open_serial_connection


sio = socketio.AsyncClient()
WHITE_list = set(["94:C9:60:19:45:91","94:C9:60:19:57:93","94:C9:60:19:43:75",
                  "94:C9:60:19:12:56","94:C9:60:19:07:14","94:C9:60:19:91:53",])
blackList = ['B8:27:EB:78:BB:33', 'B8:27:EB:F0:96:53', 'B8:27:EB:1C:19:34', 'B8:27:EB:56:D1:02', 'B8:27:EB:E2:7C:53', 'DC:A6:32:8E:23:43',
                '00:11:32:E3:39:11', '50:EB:F6:00:03:01', 'B8:27:EB:83:29:79', 'B8:27:EB:25:34:21', 'B8:27:EB:D1:E3:34', 'B8:27:EB:9F:76:29', 
                'B8:27:EB:74:15:23', 'B8:27:EB:85:11:14', 'B8:27:EB:C2:06:75', 'B8:27:EB:0F:92:62', '12:11:32:E3:3A:63', '5A:91:9D:6D:67:50']

@sio.event
async def connect():
    print('[INFO] Connection Established')

@sio.event
async def send_message(data):
    def ack(data):
        pass
    print('[INFO] Send ', data)
    await sio.emit('RSSI_mesg', {opt.device_id: data})

@sio.event
async def disconnect():
    print('disconnected from server')

@sio.event
async def _Change_channel(data):
    print('[INFO] Change channel to %d.' % data['channel'])
    protocol.write((f"%d\n" %data['channel']).encode())

@sio.event
async def Update_WHITE_list(data):
    global WHITE_list
    print('[INFO] Recieve WHITE_list. %d in WHITE_list' % len(data['WHITE_list']))
    WHITE_list = set(data['WHITE_list'])

async def serial_read():
    print('[INFO] Create serial read task')
    while True:
        try:
            global transport
            global protocol
            transport, protocol = await open_serial_connection(url='/dev/ttyUSB0', baudrate=115200)

            protocol.write(f"2\n".encode())
            while True:
                line = await transport.readline()
                line = line.decode('utf-8').rstrip()
                MAC, RSSI, Seq, channel = check_serial_legitimate(line)
                if None not in (MAC, RSSI, Seq, channel) and MAC in WHITE_list and MAC not in blackList:
                    await send_message([MAC, RSSI, Seq, channel])
        except serial.SerialException as e:
            ##There is no new data from serial port
            pass

async def main(device_id):
    loop = True
    while loop:
      try:
        event_loop = asyncio.get_event_loop()
        await sio.connect('http://192.168.50.121:5000',  headers={'device_id':f'{device_id}'})
        serial_read_task = asyncio.create_task(serial_read())
        await sio.wait()
      except KeyboardInterrupt:
          print("[Warning] Key Interupt.")
          loop = False
          serial_read_task.cancel()
      except socketio.exceptions.ConnectionError as e:
          print("[Warning] Cloud websocket unreachable")
          await sio.sleep(0.1)
          serial_read_task.cancel()
      except Exception as e:   
          loop = True
          print("[Warning] Unknow error from cloud websocket")
          serial_read_task.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--device_id", type=int, default=0, help="RPi Number")
    opt = parser.parse_args()
    print(opt)
    asyncio.run(main(opt.device_id))
