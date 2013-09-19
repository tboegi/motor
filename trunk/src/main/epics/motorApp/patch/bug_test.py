#!/usr/bin/python
# Motor record bugs test script (test will fail if bug is fixed)
# For the communication with the database we use the Cachannel module, testing is done with the unittest module
from CaChannel import CaChannel
import unittest
import os
import sys
import time
import argparse

# We set the epics global variable so PVs are accessible from the script.
# Comment this out if the firewall is disabled (default is on)
#os.putenv('EPICS_CA_ADDR_LIST','127.0.0.1')

parser = argparse.ArgumentParser(description='Tests Motor record bugs')
parser.add_argument('--pmac', default='PMAC')
parser.add_argument('--motor', default='MTR1')
parser.add_argument('--deadband', default=30)
parser.add_argument('unittest_args', nargs='*')    
args = parser.parse_args()
sys.argv[1:] = args.unittest_args

class Test(unittest.TestCase):
    print 'After this tests are run please home the motor even if motor record reports that is homed.'
    print 'Also check all settings.'
# Default device and motor name
    device = args.pmac
    motor = args.motor
# wait deadband when the script moves the motor to a new location
    sleep_deadband = int(args.deadband)
    
    pv_spmg = CaChannel()
    pv_spmg.searchw(device+':'+motor+'_MV_MODE_CMD')
    
    pv_motor_resolution = CaChannel()
    pv_motor_resolution.searchw(device+':'+motor+'_.MRES')
    
    pv_set_position = CaChannel()
    pv_set_position.searchw(device+':'+motor+'_SP')
    
    pv_position = CaChannel()
    pv_position.searchw(device+':'+motor+'_.RBV')
    
    pv_low_limit = CaChannel()
    pv_low_limit.searchw(device+':'+motor+'_SP.DRVL')
    
    pv_high_limit = CaChannel()
    pv_high_limit.searchw(device+':'+motor+'_SP.DRVH')
    
    pv_velocity = CaChannel()
    pv_velocity.searchw(device+':'+motor+'_.VELO')
    
    pv_acceleration_time = CaChannel()
    pv_acceleration_time.searchw(device+':'+motor+'_.ACCL')
    
    pv_offset = CaChannel()
    pv_offset.searchw(device+':'+motor+'_.OFF')
    
    pv_direction = CaChannel()
    pv_direction.searchw(device+':'+motor+'_.DIR')
    
    pv_tweak_forward = CaChannel()
    pv_tweak_forward.searchw(device+':'+motor+'_TWF_.PROC')
    
    default_low_limit = pv_low_limit.getw()
    default_high_limit = pv_high_limit.getw()
    default_motor_resolution = pv_motor_resolution.getw()
    default_velocity = pv_velocity.getw()
    default_acceleration_time = pv_acceleration_time.getw()
    default_offset = pv_offset.getw()
 
# We read the motor resolution and check the number of decimal places (without trailing zeroes)
    places = len(str(pv_motor_resolution.getw()).split('.')[1].rstrip('0')) 
    
# Calculate the middle position    
    middle_position = round(default_high_limit - (default_high_limit - default_low_limit) / 2, places)
# Calculate tweak step
    step = round((default_high_limit - default_low_limit) / 4, places)
    
    def setUp(self):
        print 'set up'
        self.assertNotEqual(self.pv_low_limit.getw(), self.pv_high_limit.getw(), 'Software position limits are disabled')
        self.pv_set_position.putw(self.middle_position)
        time.sleep(1)
        self.pv_spmg.putw(1)
        time.sleep(abs(self.pv_position.getw() - self.middle_position) / self.default_velocity  + 40 * self.default_acceleration_time)
        self.assertAlmostEqual(self.pv_position.getw(), self.middle_position, self.places, 'The motor is not at the middle position (setUp)')
        time.sleep(1)
    
    def test_MR_bug1(self):
        print 'Testing if changing the MRES field also overwrites the motor position with the desired position.'
        self.pv_spmg.putw(0)
        self.pv_set_position.putw(self.default_high_limit)
        time.sleep(1)
        self.pv_motor_resolution.putw(self.default_motor_resolution)
        time.sleep(1)
        self.assertAlmostEqual(self.pv_position.getw(), self.default_high_limit, self.places, 'Changing MRES did not overwrite the motor position with the desired position.')
        self.pv_set_position.putw(self.middle_position)
        time.sleep(1)
        self.pv_motor_resolution.putw(self.default_motor_resolution)
        time.sleep(1)
        
    def test_MR_bug2(self):
        print 'Testing if changing the axis orientation and driving the motor overwrites the offset'
        if self.pv_direction.getw() == 0:
            self.pv_direction.putw(1)
        else:
            self.pv_direction.putw(0)
        time.sleep(1)
        self.pv_tweak_forward.putw(1)
        time.sleep(self.step / self.default_velocity + self.sleep_deadband * self.default_acceleration_time)
        if self.pv_direction.getw() == 0:
            self.pv_direction.putw(1)
        else:
            self.pv_direction.putw(0)
        time.sleep(1)
        self.assertNotEqual(self.pv_offset.getw(), self.default_offset, 'Changing the axis orientation and driving the motor did not overwrite the offset')
        self.pv_offset.putw(self.default_offset)
        
    def test_MR_bug3(self):
        print 'Testing if changing desired position when the motor is in Pause mode calculates new DVAL'
        print 'only if desired position is different than current position (should fail with CSL patched motor record).'
        self.pv_spmg.putw(0)
        time.sleep(1)
        self.pv_set_position.putw(self.default_high_limit)
        time.sleep(1)
        self.pv_set_position.putw(self.middle_position)
        time.sleep(1)
        self.pv_spmg.putw(1)
        time.sleep((self.default_high_limit - self.middle_position) / self.default_velocity + self.sleep_deadband * self.default_acceleration_time)
        self.assertNotEqual(self.pv_set_position.getw(), self.pv_position.getw(), 'Set position and motor position are the same')

if __name__ == '__main__':
    unittest.main() 