# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

##################################
## QTlab driver written by Ben S. & Sal Jua Bosman
## Steelelab-MED-TNW-TU Delft
## contact: b.h.schneider@tudelft.nl
## contact: saljuabosman@mac.com
##################################


from instrument import Instrument
import visa
import types
import logging
import numpy as np
import cmath as cm

import qt

##class pna_measurement():
##
##    def __init__(self,name,measurement_type,channel=None,diplay=None):
##        print 'hello'
##    

class PNA_N5221A(Instrument):
    '''
    This is a qtlab driver for the Agilent PNA_N5221A VNA.

    This driver by calling the function setup standard sets up a measurement (trace) S12, from 1GHz, to 10GHz, 2000sweeppoints &.1MHz bandwidth
    by changing the parameters one can change this default setting. On top of this one can also add secondary
    traces.

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'PNA_N5221A',
        address='',
        reset=<bool>,
        change_display=<bool>,
        change_autozero=<bool>)
    i.e. any_device= qt.instruments.create('any_device','universal_driver',address='USB0::0x1AB1::0x0588::DM3L125000570::INSTR')
                                                                             address='TCPIP::192.168.100.21::INSTR'
    '''

    def __init__(self, name, address):
        '''
        Initializes the any_device, and communicates with the wrapper.

        Input:
            name (string)           : name of the instrument
            address (string)        : GPIB address
            reset (bool)            : resets to default values
           
        Output:
            None
        '''
        # Initialize wrapper functions
        logging.info('Initializing instrument Agilent PNA_N5221A')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._visainstrument = visa.instrument(self._address)

        # Add parameters to wrapper

        self.add_parameter('start_frequency', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='Hz', minval=10e6, maxval=13500e6)
        self.add_parameter('stop_frequency', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='Hz', minval=10e6, maxval=13500e6)
        self.add_parameter('sweeppoints',
                           flags=Instrument.FLAG_GETSET,
                           units=' ', minval=1, maxval=25000,
                           type=types.FloatType)
        self.add_parameter('sweeptime',
                           flags=Instrument.FLAG_GET,
                           units='sec',
                           type=types.FloatType)
        self.add_parameter('resolution_bandwidth', type=types.FloatType,
                           flags=Instrument.FLAG_GETSET,
                           units='Hz')
        self.add_parameter('averages', type=types.IntType,
                           flags=Instrument.FLAG_GETSET,
                           units='',minval=0, maxval=32767)

        self.add_parameter('measurement_type', type=types.StringType, flags=Instrument.FLAG_GETSET, units='')
        

        # Add functions to wrapper
        self.add_function('abort')
        self.add_function('read')
        self.add_function('w')
        self.add_function('q')
        self.add_function('reset')
        self.add_function('get_all')
        self.add_function('setup')
        

        # Connect to measurement flow to detect start and stop of measurement
        qt.flow.connect('measurement-start', self._measurement_start_cb)
        qt.flow.connect('measurement-end', self._measurement_end_cb)

# --------------------------------------
#           functions
# --------------------------------------

    def setup(self,measurement_type='S12',start_frequency=1.5e9,stop_frequency=8.5e9, sweeppoints=2000,bandwidth=1e6):
        '''
        Standard function to call everytime to setup a measurement.
        for the measurement type one can select S11,S12,S21, S22, A, B, A/R1,2 ,
        AI1,2 , etc

        for more information see:
        #options can be found here: http://na.tm.agilent.com/pna/help/latest/Programming/GP-IB_Command_Finder/Calculate/Parameter.htm#cpd


        It starts to continuously sweep from here, when fetching data set continuously OFF
        '''
        self.set_measurement_type(measurement_type)         #first a new measurement should be defined before one can set other settings
        self.set_start_frequency(start_frequency)
        self.set_stop_frequency(stop_frequency)
        self.set_sweeppoints(sweeppoints)
        self.set_resolution_bandwidth(bandwidth)
        
        #return sweeppoints

    def sweep(self, continuous=False):
        '''Function runs a single or multiple sweeps'''
        #Turn continuous sweep off
        self._visainstrument.write("INITiate:CONTinuous OFF")
        if(continuous==True):
            self._visainstrument.write("INITiate:CONTinuous ON")
        self._visainstrument.write("INITiate:IMMediate;*wai")

    

    def fetch_data(self, channel=1, trace_number=1, polar=False):
        '''Reads the data from Channel 1 (default) and its first tracce,
        assumes ASCII, if IQ is False it returns R,\phi
        '''
        #now select correct channel and tracename
        #print "CALC" + str(channel) + ":PAR:SEL " + trace_name
        self._visainstrument.write("CALC" + str(channel) + ":PAR:SEL '" + self._get_trace_name(channel,trace_number) +"'")

        trace = self._visainstrument.ask("CALC" + str(channel) + ":DATA? SDATA")
        tr= map(float,trace.split(','))

        if(polar==False):
            return self.parse_trace(tr,complex_rep=False)
        else:
            trace = self.parse_trace(tr,complex_rep=True) #get list as complex numbers
            tr=[]
            for i in trace:
                tr.append(cm.polar(i))
            return tr

    def _get_trace_name(self,channel,trace_number):
        '''private function that retrieves the measurement name given a channel and trace_number (nth experiment in the channel)'''
  
        catalog = self.list_channel(channel)
        catalog=catalog.split(',')

        if(len(catalog)<=(trace_number-1)*2):
           print 'error trace doesnt exist'
           return None
        trace_name=catalog[(trace_number-1)*2]
        return trace_name

    def set_format(self, trace_format, channel=1, trace_number=1, auto_scale_Y=True):
        '''Sets the fromat of the Trace recorded
    
        options are: MLIN, MLOG, PHAS, UPH, IMAG, REAL, POL, SMIT, SADM, SWR, GDEL, KELV, FAHR, CELS
        '''

        #select the correct trace
        self._visainstrument.write("CALC" + str(channel) + ":PAR:SEL '" + self._get_trace_name(channel,trace_number) +"'")

        #sets the format
        self._visainstrument.write("CALC" + str(channel) + ":FORM " + trace_format)

        #display titles and stuff
        self._visainstrument.write("DISP:WIND1:TRAC:STAT ON")
        self._visainstrument.write("DISP:WIND1:TITL:STAT ON")
        #self._visainstrument.write("CALC1:FORM DBM")
        if(auto_scale_Y==True):
            self._visainstrument.write("DISP:WIND1:TRAC1:Y:SCAL:AUTO")
        
          
       
    def parse_trace(self,trace,complex_rep=False):

        tr=[]
        real=trace[::2]
        img=trace[1::2]
        if(complex_rep==False):
            tr.append(real)
            tr.append(img)
            return tr
        else:
            index=0
            for i in real:
                tr.append(complex(i,img[index]))
                index = index+1
            return tr
   
    def ID(self):
        return self._visainstrument.ask('*IDN?')

    def value(self):
        return self._visainstrument.ask('READ?')
    def read(self):
        self._visainstrument.read()
    def w(self,string):
        self._visainstrument.write(string)
    def q(self,string):
        return self._visainstrument.ask(string)
    def reset(self):
        self._visainstrument.write('SYST:FPReset')
        #Preset the analyzer

    def abort(self):
        self._visainstrument.write('ABORT')

    def get_all(self):
        self.get_sweeppoints()
        self.get_start_frequency()
        self.get_stop_frequency()
        self.get_averages()
        self.get_resolution_bandwidth()
        #self.get_resolution_bandwidth_auto()
        #self.get_filter_type()
        self.get_sweeptime()
        #self.get_tracking()
        #self.get_source_power()
        #self.get_trace_continuous()

    def data_ascii(self):
        self._visainstrument.write("format:data ascii")
    def data_32bit(self):
        self._visainstrument.write("FORM REAL,32")
    def data_64bit(self):
        self._visainstrument.write("FORM REAL,64")
    def data_s(self):
        '''
        Fetch command from RAM, to retrieve data from PNA returns 2 numbers per data point (I, Q) 
        '''

        #still to implement, check what format is currently used, and parse the data accordingly
        
        trace = self._visainstrument.ask("CALCulate:DATA? SDATA") # 'Corrected, Complex Meas
        return trace.split(',')
        
    def data_f(self):
        '''
        Fetch command from RAM, to retrieve data from PNA return 2 numbers per data point for Polar (r, \theta) and Smith
        chart format, returns one point for all other formats
        '''

        #still to implement, check what format is currently used, and parse the data accordingly
        
        trace= self._visainstrument.ask("CALCulate:DATA? FDATA") #'Formatted Meas
        return trace.split(',')
    
    def data_fmem(self):
        '''
        Fetch command from Memory, same like data_f
        '''
        return self._visainstrument.ask("CALCulate:DATA? FMEM") #'Formatted Memory

    def data_smem(self):
        '''
        Fetch command from Memory, same like data_s
        '''
        return self._visainstrument.ask("CALCulate:DATA? SMEM") #'Formatted Memory

    def set_averages_on(self):
        self._visainstrument.write('SENS:AVER 1')
    def set_averages_off(self):
        self._visainstrument.write('SENS:AVER 0')

    def cont_off(self):
        #Turn continuous sweep off
        self._visainstrument.write("INITiate:CONTinuous OFF")
        
    

    def convert_data(self,data):
        data = data.split(',')
        newdata=[]
        for i in data:
            newdata.append(float(i))
        return newdata
   
    def list_channel(self, channel=1):
        '''
        Returns a list of all measurements (traces) active on this channel.
        '''
        channel_list = self._visainstrument.ask("CALC" + str(channel) + ":PAR:CAT?")
        return channel_list[1:-1]

    def delete_channel(self, channel=1):
        '''
        Deletes all measurement definitions for specified channel
        '''
        return self._visainstrument.write("CALC" + str(channel) + ":PAR:DEL:ALL")

    def double_window(self,name1='MyMeas1',name2='MyMeas2'):
        '''
        This function sets the PNA to 2 windows and measures S21, first trace is put in
        the first window, second trace is put in the second window.
        '''

        #WINDOW 1 / EXPERIMENT 1
        #Create and turn on window/channel 1
        self._visainstrument.write("DISPlay:WINDow1:STATE ON")

        #Define a measurement name, parameter

        
        self._visainstrument.write('CALCulate1:PARameter:DEFine:EXT ' +"'" + name1 +"'" +',S21')

        #Associate ("FEED") the measurement name ('MyMeas') to WINDow (1)
        self._visainstrument.write('DISPlay:WINDow1:TRACe1:FEED ' +"'" + name1 + "'")

        #WINDOW 2 / EXPERIMENT 2
        #Create and turn on window/channel 2
        self._visainstrument.write("DISPlay:WINDow2:STATE ON")

        #Define a measurement name, parameter
        self._visainstrument.write('CALCulate2:PARameter:DEFine:EXT ' + "'" + name2 + "'" +' ,S21')

        #Associate ("FEED") the measurement name ('MyMeas') to WINDow (2)
        self._visainstrument.write('DISPlay:WINDow2:TRACe2:FEED ' +"'" + name2 + "'")

        #WINDOW 3 / EXPERIMENT 3
        #Create and turn on window/channel 3
        name3='cracy'
        
        self._visainstrument.write("DISPlay:WINDow3:STATE ON")

        #Define a measurement name, parameter
        self._visainstrument.write('CALCulate3:PARameter:DEFine:EXT ' + "'" + name3 + "'" +' ,S21')

        #Associate ("FEED") the measurement name ('MyMeas') to WINDow (2)
        self._visainstrument.write('DISPlay:WINDow3:TRACe2:FEED ' +"'" + name3 + "'")        
##        
##        #Set slow sweep so we can see
##        self._visainstrument.write("SENS1:SWE:TIME 2") 
##        self._visainstrument.write("SENS2:SWE:TIME 2")
##        #set number of points to 10
##        self._visainstrument.write("SENS1:SWE:POIN 2001")
##        self._visainstrument.write("SENS2:SWE:POIN 2001")
    def test_hold(self):
        #Put both channels in Hold
        self._visainstrument.write("SENS1:SWE:MODE HOLD")
        self._visainstrument.write("SENS2:SWE:MODE HOLD")

    def single_window(self,name1='MyMeas1', reset=False):
        '''
        This function sets the PNA to 1 window and measures S21
        '''
        if(reset):
            self.reset()
        
        self._visainstrument.write("DISPlay:WINDow1:STATE ON")
        #Create and turn on window/channel 1
        string = 'CALCulate1:PARameter:DEFine:EXT ' +"'"+ name1 + "'"+',S21'
        print string
        self._visainstrument.write(string)
        #Define a measurement name, parameter
        string = 'DISPlay:WINDow1:TRACe1:FEED ' +"'" + name1 + "'"
        print string
        self._visainstrument.write(string)

    def save_settings(self,settingsname):
        '''This function saves the current settings on the PNA harddrive (C:\bin\settingsname.sta)
        '''
        string = 'MMEM:STOR:STAT ' + "'" + settingsname + "'"
        self._visainstrument.write(string)
       

# --------------------------------------
#           parameters
# --------------------------------------

    def do_get_sweeppoints(self):
        return self._visainstrument.ask("SENSe1:SWEep:POIN?")
    def do_get_start_frequency(self): #in MHz
        return float(self._visainstrument.ask('SENS:FREQ:START?'))
    def do_get_stop_frequency(self): #in MHz
        return float(self._visainstrument.ask('SENS:FREQ:STOP?'))
    def do_get_sweeptime(self): #in MHz
        return float(self._visainstrument.ask('SENS1:SWE:TIME?'))
    def do_get_resolution_bandwidth(self):
        return float(self._visainstrument.ask('SENS:BWID?'))
    def do_get_averages(self):
        return float(self._visainstrument.ask('SENS:AVER:COUN?'))
    
    def do_set_sweeppoints(self,number):
        return self._visainstrument.write('SENSe1:SWEep:POINts %s' % (number))
    def do_set_start_frequency(self,number): #in MHz
        return self._visainstrument.write('SENS:FREQ:START %s' % (number)) 
    def do_set_stop_frequency(self,number): #in MHz
        return self._visainstrument.write('SENS:FREQ:STOP %s' % (number))
    def do_set_resolution_bandwidth(self,number):
        return self._visainstrument.write('SENS:BWID %s' % (number))
    def do_set_averages(self,number):
        return self._visainstrument.write('SENS:AVER:COUN %s' % (number))

    def do_set_measurement_type(self,measure_type):
        '''Sets the measurement type '''

        #delete all traces in channel 1
        self._visainstrument.write("CALC1:PAR:DEL:ALL")  #empty channel 1
      
        self._visainstrument.write("DISP:WIND1:STATE ON") #switches window1 on
        self._visainstrument.write("CALC1:PAR:DEF:EXT '1', " + measure_type)

        self._visainstrument.write("DISP:WIND1:TRACE1:FEED '1'") #connects the standard measurement setup to the display

    def do_get_measurement_type(self):
        channel1 = self.list_channel(1)

        if channel1=='"NO CATALOG"':
            return 'NO CATATALOG'
            
        channel1 = channel1.split(',')
        channel1 = channel1[1]
        channel1 = channel1[:-1]
        return channel1
             
             
             


# --------------------------------------
#           Internal Routines
# --------------------------------------
#
    def _measurement_start_cb(self, sender):
        '''
        Things to do at starting of measurement
        '''
#        #set correct commandset
#        self._visainstrument.write('cmdset agilent')
#        return self._visainstrument.write('*IDN?')
##        if self._change_display:
##            self.set_display(False)
##            #Switch off display to get stable timing
##        if self._change_autozero:
##            self.set_autozero(False)
##            #Switch off autozero to speed up measurement

    def _measurement_end_cb(self, sender):
        '''
        Things to do after the measurement
        '''
##        if self._change_display:
##            self.set_display(True)
##        if self._change_autozero:
##            self.set_autozero(True)
    
