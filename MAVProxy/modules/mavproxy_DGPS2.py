#!/usr/bin/env python
'''
support for a GCS attached DGPS2 system
'''

import socket, errno
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class DGPS2Module(mp_module.MPModule):
    def __init__(self, mpstate):
        super(DGPS2Module, self).__init__(mpstate, "DGPS2", "DGPS2 injection support")
        #self.portip = '192.168.43.25'
        self.portip = '10.42.3.43'
        #self.portip = '192.168.42.1'
        self.portnum = 9000
        #self.portip = raw_input("Enter the IP Address of the of the GPS base\n")
        #self.portnum = raw_input("Enter the port number of the GPS Base\n")
        self.port = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.port.connect((self.portip, int(self.portnum)))
        mavutil.set_close_on_exec(self.port.fileno())
        self.port.setblocking(0)
        self.sequence = 0
        print("Listening for RTCM packets on UDP://%s:%s" % (self.portip, self.portnum))

        self.connect_to_base()

    def connect_to_base(self):
        try:
            self.base_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.base_conn.connect(("10.42.3.43", 9001))
        except:
            print "ERROR: could not connect to base"
        else:
            print "Connected to base to track its location"

    def idle_task(self):
        '''called in idle time'''
        self.get_base_location()
        try:
            data = self.port.recv(1024)
        except socket.error as e:
            if e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK ]:
                return
            raise
        if len(data) > 720:
            print("RTCM data too large: %u bytes" % len(data))
            return
        data_ptr = 0
        remain = len(data)
        fragment = 0
        try:

            while (remain > 0):
                if (remain >= 180):
                    send_len = 180
                else:
                    send_len = remain
                n = ((self.sequence % 32) << 3) + (fragment << 1) + int(len(data) <= 180)    
                bytes = bytearray(data[data_ptr:data_ptr+send_len].ljust(180, '\0'))
                # print n
                # print [ int(b) for b in bytes]
                self.master.mav.gps_rtcm_data_send(
                    n,
                    send_len,
                    bytes)
                if (remain == 180 and fragment != 3):
                    self.master.mav.gps_rtcm_data_send(
                        ((self.sequence % 32) << 3) + (fragment << 1) + 1,
                        0,
                        bytearray(['\0'] * 180))
                self.cmd_set_home(52.375273, 4.9282953) # 020

                # if (n % 2 == 0):
                #     self.cmd_set_home(52.375273, 4.9282953) # 020
                # else:
                #     self.cmd_set_home(52.069291,4.3213093) # 070

                print("RTCM data: %u seq   %u frag    %u len   %d total     %d\n" % (self.sequence % 32, fragment, send_len, len(data), ((self.sequence % 32) << 3) + (fragment << 1) + int(remain >= 180)))
                fragment += 1
                data_ptr += send_len
                remain   -= send_len

            self.sequence += 1

        except Exception,e:
            print "RTCM Failed:", e

    def get_base_location(self):
        try:
            # print "CHUNK"
            chunk = self.base_conn.recv(4096)
            lines = chunk.splitlines()
            for l in lines:
                # print l
                columns = l.split() # split on whitespace
                if not len(columns) == 15:
                    break # discard incomplete lines
                lat = columns[2]
                lon = columns[3]
                alt = columns[5]
                print "base location lat: %s, long: %s, alt: %s" % (lat, lon, alt)
                # TODO: dampen the input signal and send an update to the plane

        except:
            print "No base location"

    def updateHome(self, lat, lng):

        self.master.mav.command_long_send(
            self.settings.target_system,  # target_system
            mavutil.mavlink.MAV_COMP_ID_SYSTEM_CONTROL, # OR 0
            mavutil.mavlink.MAV_CMD_DO_SET_HOME, # command
            2, # empty
            0, # empty
            0, # empty
            lat, # lat
            lng, # long
            0,0,0) # alt

    def cmd_set_home(self, lat, lon):
        '''called when user selects "Set Home" on map'''
        alt = 0.1 # self.ElevationMap.GetElevation(lat, lon)
        print("Setting home to: ", lat, lon, alt)
        self.master.mav.command_long_send(
            self.settings.target_system, self.settings.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_HOME,
            1, # set position
            0, # param1
            0, # param2
            0, # param3
            0, # param4
            lat, # lat
            lon, # lon
            alt) # param7        

def init(mpstate):
    '''initialise module'''
    return DGPS2Module(mpstate)