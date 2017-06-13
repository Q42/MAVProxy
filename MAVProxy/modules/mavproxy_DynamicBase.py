#!/usr/bin/env python
'''
support for a GCS attached DynamicBase system
'''

import socket, errno
from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module

class DynamicBaseModule(mp_module.MPModule):
    def __init__(self, mpstate):
        super(DynamicBaseModule, self).__init__(mpstate, "DynamicBase", "DynamicBase injection support")
        self.connect_to_base("10.42.3.43", 9001)

    def connect_to_base(self, ip, port):
        try:
            self.base_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.base_conn.connect((ip, port))
        except:
            print "ERROR: could not connect to base"
        else:
            print "Connected to base to track its location"

    def idle_task(self):
        '''called in idle time'''
        self.get_base_location()

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
    return DynamicBaseModule(mpstate)