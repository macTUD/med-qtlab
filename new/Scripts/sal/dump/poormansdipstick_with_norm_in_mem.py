#prepare environment
import qt
import numpy
from numpy import pi, random, arange, size, array, sin, cos, diff, absolute,zeros, sign,ceil,sqrt,absolute
from time import time, sleep, localtime, strftime
execfile('metagen.py')

#Check and load instrument plugins
instlist = qt.instruments.get_instrument_names()
print "Available instruments: "+" ".join(instlist)

if 'rigol' not in instlist:
    rigol= qt.instruments.create('rigol','rigol_dm3058',address='USB0::0x1AB1::0x0588::DM3L125000570::INSTR')

if 'fsl' not in instlist:
    fsl= qt.instruments.create('fsl','RS_FSL',address='TCPIP::192.168.100.21::INSTR')

if 'med' not in instlist:
    med = qt.instruments.create('med','med')

#measurement information stored in manual in MED instrument
med.set_device('PM-1-A (poormans dipstick 1st level cabel A')
med.set_setup('poormans RF dipstick')
med.set_user('Sal')


print rigol.query('*IDN?')

# 'start measurement'
#def measure_temp_fsl(start_frequency, stop_frequency, runtime):

start_frequency= 10
stop_frequency= 18000
bandwidth = 0.07#MHz
max_runtime = 600 #sec
rf_power = 0
norm_runs = 100
exp_runs =100


#normalization routine
qt.mstart()
spyview_process(reset=True) #clear old meta-settings
filename = 'fsl_temp_sec_norm_in_mem'

print 'prepare datafile'
data = qt.Data(name=filename)
data.add_coordinate('Frequency (MHz)',size=fsl.get_sweeppoints())
data.add_coordinate('time [s]')
data.add_value('RF Power (dBm)')
data.add_value('Summed trace ')
#data.add_coordinate('temp [K]')
data.add_value('Temp (K)')
#data.add_value(rigol.get_function()[1:-1]+ ' ') #whatever rigol is set to
data.create_file()
data.copy_file('poormansdipstick_with_norm_in_mem.py')

print 'prepare FSL for normalization'
#required preperation stuff (FSL)
fsl.reset()
fsl.set_start_frequency(start_frequency)
fsl.set_stop_frequency(stop_frequency)
span=stop_frequency-start_frequency
fsl.set_resolution_bandwidth(bandwidth)
fsl.set_tracking(True)
fsl.set_source_power(rf_power)
#fsl.set_averages(normalization_averages) #set the number of normalization runs
fsl.get_all() #get all the settings and store it in the settingsfile

#time variable
x_time = 0
    
print 'prepare 2D plot'
plot=qt.Plot2D(data, name=filename, coorddim=0, valdim=2) #buggy
#plot3Dx = qt.Plot3D(data, name='x3d', coorddims=(0,1), valdim=2)

print 'Measure with Rigol: ' + rigol.get_function()[1:-1]
sleep(0.01)
#rigol.set_disp_off() #ben's preference
fsl.set_trace_continuous(False)    
tstart = time()


print 'Normalization:'
run_index=0
summed_trace =0
summed_trace = array(fsl.get_trace()) #first local_trace

while (x_time < max_runtime and run_index<norm_runs):
    x_time = time()- tstart
    y_temp = (float(rigol.value()[13:])-221.47)/0.23377+4.2 #temperature converted to [K] (cal by Vibhor)
    trace=fsl.get_trace() #FSL measurement

    summed_trace+=trace
    time_list = x_time*ones(len(trace))   #make list
    temp_list = y_temp*ones(len(trace))   #make list

    fstep=span/(len(trace)-1.0) #calc correct freq. step
    flist=np.arange(start_frequency,stop_frequency,fstep) #create freq. list
    data.new_block()
    data.add_data_point(flist,time_list,trace,list(numpy.array(summed_trace).reshape(-1,)),temp_list) #store data
    spyview_process(data,start_frequency,stop_frequency,x_time) 
    qt.msleep(0.01) #wait 10 usec so save etc

    run_index=run_index+1
    print run_index, x_time,y_temp 

print x_time,y_temp

#now all the traces are summed into local_trace, now the number of traces summed is run_index + 2 
normalization = summed_trace/(run_index+1)

data.close_file()
qt.mend()
#end of normalization routine

print 'end of normalization'

var = raw_input("Enter something to start experiment: ")
print "you entered ", var


#start measurement routine

print 'prepare FSL for experiment'
#required preperation stuff (FSL)
fsl.reset()
fsl.set_start_frequency(start_frequency)
fsl.set_stop_frequency(stop_frequency)
span=stop_frequency-start_frequency
fsl.set_resolution_bandwidth(bandwidth)
#fsl.set_averages(1) #set the number of normalization runs
fsl.set_source_power(0)
fsl.set_tracking(True)
fsl.get_all() #get all the settings and store it in the settingsfile

qt.mstart()
spyview_process(reset=True) #clear old meta-settings
filename = 'fsl_temp_sec_with_normalization'

print 'prepare datafile'
data = qt.Data(name=filename)
data.add_coordinate('Frequency [MHz]',size=fsl.get_sweeppoints())
data.add_coordinate('time [s]')
data.add_value('RF Power [dBm]')
data.add_value('normed RF Power [dBm]')
#data.add_coordinate('Temp [K]')
data.add_value('Temp [K]')
#data.add_value(rigol.get_function()[1:-1]+ ' ') #whatever rigol is set to
data.create_file()
data.copy_file('poormansdipstick_with_normalize.py')

#time variable
x_time = 0
    
print 'prepare 2D plot'
#plot3d=qt.Plot3D(data, name=filename, coorddim=(0,1), valdim=3) #creates bugs
plot=qt.Plot2D(data, name=filename, coorddim=0, valdim=3) #creates bugs

print 'Measure with Rigol: ' + rigol.get_function()[1:-1]
#rigol.set_disp_off()
fsl.set_trace_continuous(False)    
tstart = time()
sleep(0.1)
normed_trace = normalization

#reset some stuff
run_index=0
trace=0
print 'measurement loop:'
while (x_time < max_runtime and exp_runs>run_index):
    x_time = time()- tstart
    y_temp = (float(rigol.value()[13:])-221.47)/0.23377+4.2 #temperature converted to [K] (cal by Vibhor)
    trace=fsl.get_trace() #FSL measurement
    time_list = x_time*ones(len(trace))   #make list
    temp_list = y_temp*ones(len(trace))   #make list

    normed_trace = array(trace)-normalization
    data.new_block()
    
    data.add_data_point(flist, time_list, trace, normed_trace, temp_list) #store data
    spyview_process(data,start_frequency,stop_frequency,x_time) 
    qt.msleep(0.01) #wait 10 usec so save etc

    run_index+=1
    print run_index, x_time,y_temp

data.close_file()
qt.mend()

#end measurement routine


fsl.set_trace_continuous(True)
#rigol.set_disp_on()
