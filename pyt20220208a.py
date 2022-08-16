import pandas as pd
import numpy as np
import csv
import json
import pickle
import os
import asyncio
import socketio
import argparse
import threading, time, sys
import datetime
import re

rpi = 'robot1'
statusRobot = 'ready'

with open("./Passive_Wifi/Variable/start.pkl", 'wb') as pfile:
    pickle.dump(statusRobot, pfile, protocol=2)
if os.path.exists("./Passive_Wifi/Variable/robot_pose.pkl"):
    os.remove("./Passive_Wifi/Variable/robot_pose.pkl")

sio = socketio.AsyncClient()
@sio.event
async def connect():
    print('[INFO] Connection Established.')

@sio.event
async def send_message():
    
    while True:
        if os.path.exists("./Passive_Wifi/Variable/fin_.pkl"):
            print('done')
        else:
            try:
                print('try')
                robot_pose = pickle.load(open("./Passive_Wifi/Variable/robot_pose.pkl","rb"), encoding='latin1')
                x = robot_pose[0]
                y = robot_pose[1]
                z = robot_pose[2]
                w = robot_pose[3]
                print('[INFO] Send ', robot_pose)
                await sio.emit('Position', {"X": x, "Y": y, "Z": z, "W": w})
                os.remove("./Passive_Wifi/Variable/robot_pose.pkl")
            except FileNotFoundError:
                pass
            
        await asyncio.sleep(0.1)

@sio.on("Position")
async def Position(data):
    status = data["Status"]
    print('status', status)
    if status == 'ok':
        statusRobot = 'ready'
        with open("./Passive_Wifi/Variable/start.pkl", 'wb') as pfile:
            pickle.dump(statusRobot, pfile, protocol=2)


async def main(device_id):
    event_loop = asyncio.get_event_loop()
    await sio.connect('http://192.168.50.121:5000', headers={'device_id':f'{device_id}'})
    await asyncio.create_task(send_message())
    await sio.wait()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--device_id", type=int, default=-1, help="RPi Number")
    opt = parser.parse_args()
    print(opt)
    asyncio.run(main(opt.device_id))