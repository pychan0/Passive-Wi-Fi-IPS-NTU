from aiohttp import web
import socketio
import asyncio
import time, argparse
from wifiscan1_0125 import wifi_scan
import collections
import threading
from datetime import datetime
import asyncio
import aiofiles
import os
import copy
from aiocsv import AsyncWriter
from dateutil.parser import parse
from RouterInfo import RouterInfo
import pandas as pd
import csv
import paramiko
import tarfile

sio = socketio.AsyncServer(async_mode='aiohttp', engineio_logger=False, logger=False, ssl_verify=False)
app = web.Application()
sio.attach(app)

ssh_client=paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname="192.168.50.148", port=22, username="DESKTOP-12ND109/user", password="xxxxxxxxxx")
ftp_client=ssh_client.open_sftp()


source_dir = "/home/pi/Testing/"

sid_dict = {}
WIFI_channel_queue = collections.deque(maxlen=1)
RSSI_DATA = {}
Position_DATA = {'X':None, 'Y':None, 'Z': None, 'W': None}


WHITE_list = set(["94:C9:60:19:45:91","94:C9:60:19:57:93","94:C9:60:19:43:75",
                  "94:C9:60:19:12:56","94:C9:60:19:07:14","94:C9:60:19:91:53",])
blackList = set(['B8:27:EB:78:BB:33', 'B8:27:EB:F0:96:53', 'B8:27:EB:1C:19:34', 'B8:27:EB:56:D1:02', 'B8:27:EB:E2:7C:53', 'DC:A6:32:8E:23:43',
                '00:11:32:E3:39:11', '50:EB:F6:00:03:01', 'B8:27:EB:83:29:79', 'B8:27:EB:25:34:21', 'B8:27:EB:D1:E3:34', 'B8:27:EB:9F:76:29', 
                'B8:27:EB:74:15:23', 'B8:27:EB:85:11:14', 'B8:27:EB:C2:06:75', 'B8:27:EB:0F:92:62', '12:11:32:E3:3A:63', '5A:91:9D:6D:67:50'])

BW16_AP_list = set(['94:C9:60:19:46:73', '94:C9:60:19:83:12', '94:C9:60:19:85:35', '94:C9:60:19:12:63', '94:C9:60:19:90:84'])


@sio.event
async def connect(sid, environ):
    device_id = environ.get('HTTP_DEVICE_ID', None) or sid
    print('[INFO] RPI{} is connected'.format(device_id))
    sid_dict[sid] = device_id
    print(sid_dict)

@sio.on('Position')
async def Posistion(sid, data):
    X = data['X']
    Y = data['Y']
    Z = data['Z']
    W = data['W']
    Position_DATA['X']=X
    Position_DATA['Y']=Y
    Position_DATA['Z']=Z
    Position_DATA['W']=W
    

    print('[INFO] Robot Send X: %f, Y:%f, Z:%f, W:%f' % (X,Y,Z,W))
    while True:
        if RSSI_DATA.get(CHANNEL_BW16_ROBOT) is not None:
            print('[INFO] %d samples in this RP.' %len(RSSI_DATA[CHANNEL_BW16_ROBOT]))
            if len(RSSI_DATA[CHANNEL_BW16_ROBOT]) >= opt.rp_samples:
                await asyncio.sleep(opt.RSSI_time_delay)
                break
        
        await asyncio.sleep(2)
    Position_DATA['X']= None
    Position_DATA['Y']= None
    Position_DATA['Z']= None
    Position_DATA['W']= None
    while len(sid_dict) < opt.monitors + 1:
      print('[Error] Number of Monitors are not correct. Only %d which is less than %d'%(len(sid_dict), opt.monitors))
      await asyncio.sleep(0.5)
    await Show_RSSI_Data()
    await sio.emit("Position", {"Status":"ok"})


async def Update_White_list():
    print("len sid dict in update white list", len(sid_dict))
    
    global WHITE_list_updated
    
    while True:
        try:
            ri = RouterInfo(opt.RouteIP, opt.RouterUsername, opt.RouterPasswrod)
            tmp_list = ri.get_online_clients()
            WHITE_list.update(tmp_list)
            WHITE_list_updated = set(tmp_list) - set(BLACK_list)
            print('[Info] Send White list to client. %d in White list.'% len(WHITE_list_updated))
            await sio.emit('Update_WHITE_list',  {'WHITE_list': list(WHITE_list_updated)},)
            print('[INFO] Dumping white list to server') 
            WHITE_list_df=pd.DataFrame(WHITE_list_updated)
            WHITE_list_df.to_csv('whitelist.csv', index=False)
            ftp_client=ssh_client.open_sftp()
            ftp_client.put('whitelist.csv','online_passive/Testing/' + '/' + 'whitelist.csv')
            print('[INFO] Successfully dumped white list to server')
            time.sleep(0.001)
            ftp_client.close()            
            await asyncio.sleep(opt.save_time)
        except:
            pass


@sio.on('RSSI_mesg')
async def RSSI_mesg(sid, data):
    try:
        RPI = sid_dict.get(sid)
        MAC = data[RPI][0]
        RSSI = data[RPI][1]
        Seq = data[RPI][2]
        channel = data[RPI][3]
        if channel not in RSSI_DATA:
            RSSI_DATA[channel] = {}

        if MAC not in RSSI_DATA[channel]: 
            RSSI_DATA[channel][MAC] = {}
            for check_count in range(opt.monitors):
                RSSI_DATA[channel][MAC]['RPI%s_RSSI'%check_count] = {'RSSI':0, 'TIME':None}
            RSSI_DATA[channel][MAC]['Position'] = {'X':Position_DATA['X'], 'Y':Position_DATA['Y'], 'Z':Position_DATA['Z'], 'W':Position_DATA['W'], "TIME":datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}
            RSSI_DATA[channel][MAC]['RPI%s_RSSI'%RPI]["RSSI"] = RSSI
            RSSI_DATA[channel][MAC]['RPI%s_RSSI'%RPI]["TIME"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        else:
            for check_count in range(opt.monitors):
                if RSSI_DATA[channel][MAC]['RPI%s_RSSI'%check_count]["TIME"] is None:
                    continue
                elif (parse(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')) - parse(RSSI_DATA[channel][MAC]['RPI%s_RSSI'%check_count]["TIME"])).total_seconds() > opt.RSSI_time_delay:
                    RSSI_DATA[channel][MAC+'_'+str(Seq)] = RSSI_DATA[channel].pop(MAC)
                    RSSI_DATA[channel][MAC] = {}
                    for check_count in range(opt.monitors):
                        RSSI_DATA[channel][MAC]['RPI%s_RSSI'%check_count] = {'RSSI':0, 'TIME':None}
                    RSSI_DATA[channel][MAC]['Position'] = {'X':Position_DATA['X'], 'Y':Position_DATA['Y'], 'Z':Position_DATA['Z'], 'W':Position_DATA['W'], "TIME":datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}
                    RSSI_DATA[channel][MAC]['RPI%s_RSSI'%RPI]["RSSI"] = RSSI
                    RSSI_DATA[channel][MAC]['RPI%s_RSSI'%RPI]["TIME"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                    break
            RSSI_DATA[channel][MAC]['RPI%s_RSSI'%RPI]["RSSI"] = RSSI
    except KeyError:
        return data



@sio.event
async def disconnect(sid):
    try:
        print('[INFO] RPI{} is disconnected'.format(sid_dict.get(sid)))
        print('online:%d' % len(sid_dict), sid_dict)
        del sid_dict[sid]
    except:
        pass

async def _Change_channel():
    if opt.EnableWhiteList:
        while True:
            channel = AP_CHANNEL
            print('[INFO] Channel %d' % channel)
            print('online:%d' % len(sid_dict), sid_dict)
            await sio.emit('_Change_channel',  {'channel': channel},)
            await asyncio.sleep(2.5)
    elif not opt.EnableWhiteList:
        while True:
            try:
                print("WIFI channel queue", WIFI_channel_queue[0])
                L = [1, 2, 7, 11, 48, 56, 60, 64, 100]
                print("L is", L)
            except IndexError:
                L = [1, 2, 6, 11, 48, 52, 56, 64, 100, 161]
            for channel in L:
                print('[INFO] Channel %d' % channel)
                print('online:%d' % len(sid_dict), sid_dict)
                await sio.emit('_Change_channel',  {'channel': channel},)
                await asyncio.sleep(2.5)

def _Scanwifi():
    while True:
        try:
            Channel, BSSID = wifi_scan()
            WIFI_channel_queue.append([CHANNEL_BW16_ROBOT])
        except:
            pass


async def Show_RSSI_Data():
    do_cycle_of_list = 3
    while True:
      print("len sid dict", len(sid_dict))
      print("opt monitors", opt.monitors)
      if len(sid_dict) >= opt.monitors:
          print('[INFO] Save file.')
          if do_cycle_of_list > 0 and opt.EnableBlackList:
              print('[INFO] Create BLACK_list.')
              await asyncio.sleep(2)
              save_tmp_RSSI_DATA = copy.deepcopy(RSSI_DATA)
              RSSI_DATA.clear()
              BLACK_list.update(save_tmp_RSSI_DATA.keys())
              do_cycle_of_list += -1
          save_tmp_RSSI_DATA = copy.deepcopy(RSSI_DATA)
          RSSI_DATA.clear()

          if opt.EnableWhiteList:
              L = [AP_CHANNEL]
          else:
              L = [1, 2, 7, 11, 48, 56, 60, 64, 100]
          for channel in L:
              filepath = 'Testing/Channel_%d.csv' % channel
              if os.path.exists(filepath):
                  async with aiofiles.open(filepath, mode="r", encoding="utf-8", newline="") as afp:
                      N_lines = len(await afp.readlines())
                  if N_lines >= 5000:
                      os.remove(filepath)
                      await asyncio.sleep(0.01)
     
              if not os.path.isfile(filepath):
                  async with aiofiles.open(filepath, mode="w", encoding="utf-8", newline="") as afp:
                      writer = AsyncWriter(afp,)
                      write_data = ['MAC_Seq']
                      for rpi in range(opt.monitors):
                          write_data.extend(['RPI%s_RSSI' %rpi, 'TIME'])
                      write_data.extend(['X', 'Y', 'Z', 'W', 'TIME'])
                      await writer.writerow(write_data)
              
              async with aiofiles.open(filepath, mode="a", encoding="utf-8", newline="") as afp:
                  writer = AsyncWriter(afp,)
                  if channel in save_tmp_RSSI_DATA:
                      print('[INFO] %d samples in this RP.' %len(save_tmp_RSSI_DATA[channel]))
                      for MAC_Seq, data in save_tmp_RSSI_DATA[channel].items():
                          write_data = [MAC_Seq]
                          for rpi in range(opt.monitors):
                              write_data.extend([save_tmp_RSSI_DATA[channel][MAC_Seq]['RPI%s_RSSI'%rpi]["RSSI"],save_tmp_RSSI_DATA[channel][MAC_Seq]['RPI%s_RSSI'%rpi]["TIME"]])
                          write_data.extend([save_tmp_RSSI_DATA[channel][MAC_Seq]['Position']['X'],
                                              save_tmp_RSSI_DATA[channel][MAC_Seq]['Position']['Y'],
                                              save_tmp_RSSI_DATA[channel][MAC_Seq]['Position']['Z'],
                                              save_tmp_RSSI_DATA[channel][MAC_Seq]['Position']['W']])
                          await writer.writerow(write_data)
              
              print('[INFO] Dumping to server')
              try:
                  with tarfile.open("ch.tar.gz", "w:gz") as tar:
                    for fn in os.listdir(source_dir):
                      p = os.path.join(source_dir, fn)
                      tar.add(p, arcname=fn)  
                  await asyncio.sleep(0.002)
                  
                  ftp_client.put('ch.tar.gz','online_passive/Testing/' + '/' + 'ch.tar.gz')
                  print('[INFO] Successfully dumped to server')
                  await asyncio.sleep(opt.save_time)
              except:                      
                  pass

      else:
          print('[Error] Number of Monitors are not correct. Only %d which is less than %d'%(len(sid_dict), opt.monitors))
          RSSI_DATA.clear()
          await asyncio.sleep(opt.short_save_time)


async def main():
    outer_loop = True
    loop = True
    while loop:
        try:
            print('[INFO] Server Start')
            runner = web.AppRunner(app)
            await runner.setup()
            await web.TCPSite(runner, host=opt.ServeSocketIP, port=opt.ServeSocketPort).start()
            tasks = [asyncio.create_task(Show_RSSI_Data()),
                     asyncio.create_task(_Change_channel()),
                    asyncio.create_task(Update_White_list())]

            await sio.sleep(0.01)
            await asyncio.wait(tasks)

        except KeyboardInterrupt:
            print("[Warning] Key Interupt.")
            loop = False
        except socketio.exceptions.ConnectionError as e:
            print("[Warning] Cloud websocket unreachable",e)
            await sio.sleep(1)
            loop = False
        except Exception as e:   
            loop = True
            print("[Warning] Unknown error from cloud websocket",e)
            for task in tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    print("Cancel task")
            await sio.sleep(0.1)

if __name__ == '__main__':

    AP_CHANNEL = 48
    CHANNEL_BW16_ROBOT = 48
    
    if os.path.exists("/home/pi/ch.tar.gz"):
        os.remove("/home/pi/ch.tar.gz")
    if os.path.exists("/home/pi/whitelist.csv"):
        os.remove("/home/pi/whitelist.csv")
    if os.path.exists(f"/home/pi/Testing/Channel_{AP_CHANNEL}.csv"):
        os.remove(f"/home/pi/Testing/Channel_{AP_CHANNEL}.csv")          
    

    parser = argparse.ArgumentParser()
    parser.add_argument("--save_time", type=int, default=0.4, help="Duration time per saving cycle.")          
    parser.add_argument("--short_save_time", type=int, default=0.3, help="Check duration time per saving cycle.")    
    parser.add_argument("--rp_samples", type=int, default=5, help="Number of collections in recieving points.") 
    parser.add_argument("--monitors", type=int, default=20, help="Number of monitors.")                           
    parser.add_argument("--ServeSocketIP", type=str, default='192.168.50.121', help="Server websocket IP.")       
    parser.add_argument("--ServeSocketPort", type=int, default=5000, help="Server websocket port.")               
    parser.add_argument("--RouteIP", type=str, default="192.168.50.1", help="Server websocket port.")              
    parser.add_argument("--RouterUsername", type=str, default="admin", help="Server websocket port.")             
    parser.add_argument("--RouterPasswrod", type=str, default="xxxxxxxxxxxxx", help="Server websocket port.")      
    parser.add_argument("--RSSI_time_delay", type=float, default=1, help="Time delay for the same MAC.")          
    parser.add_argument("--EnableWhiteList", type=bool, default=True, help="Enable white list.")               
    parser.add_argument("--EnableBlackList", type=bool, default=False, help="Enable black list.")
    parser.add_argument("--EnablePositionFilter", type=bool, default=False, help="Enable Position Filter.(only in collecting mode)")

    opt = parser.parse_args()
    print(opt)
    asyncio.run(main())
