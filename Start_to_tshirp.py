#get the time
from datetime import date
from datetime import datetime
import time

#get the locations of the input on the rpi and ADC
import smbus
import sys
import subprocess

#ports location
from smbus import SMBus
from sys import exit

#emplacement variable
bus = SMBus(1)

#attributed canals and associated emplacements variable
address = 0b1110110

# Channel Address - Single channel use
# See LTC2497 data sheet, Table 3, Channel Selection.
# All channels are uncommented - comment out the channels you do not plan to use.

channel0 = 0xB0
channel1 = 0xB8
channel2 = 0xB1
channel3 = 0xB9
channel4 = 0xB2
channel5 = 0xBA
channel6 = 0xB3
channel7 = 0xBB
channel8 = 0xB4
channel9 = 0xBC
channel10 = 0xB5
channel11 = 0xBD
channel12 = 0xB6
channel13 = 0xBE
channel14 = 0xB7
channel15 = 0xBF

#reference voltage of the ADC
vref = 5

# To calculate the voltage, the number read in is 3 bytes. The first bit is ignored.
# Max reading is 2^23 or 8,388,608
max_reading = 8388608.0

# lange = number of bytes to read. A minimum of 3 bytes are read in.
# In this sample we read in 6 bytes, ignoring the last three bytes
# zeit = tells how frequently you want the readings to be read from the ADC.
# Define the time to sleep between the readings.
# tiempo = shows how frequently each channel is read in over the I2C bus.
# Best to use timepo between each successive readings.

lange = 0x06 #number of bytes to read in the block
zeit = 15     #number of seconds to sleep between each measurement
tiempo = 0.5 #number of seconds to sleep between each channel reading
# has to be more than 0.2 (seconds)


def getADCreading(adc_address,adc_channel):
    bus.write_byte(adc_address, adc_channel)
    time.sleep(tiempo)
    reading = bus.read_i2c_block_data(adc_address, adc_channel, lange)
#----------- Start conversion for the Channel Data ----------
    valor = ((((reading[0]&0x3F))<<16))+((reading[1]<<8))+(((reading[2]&0xE0)))
    #add a debug function
    #debug(print("Valor is 0x%x" % valor))

#----------- End of conversion of the Channel ----------
    volts = valor * vref / max_reading


    if( (reading[0]& 0b11000000) == 0b11000000):
        print ("*************")
        print ("Input voltage to channel 0x%x is either open or more than %5.2f. "
               "The reading may not be correct. Value read in is %12.8f Volts." % ((adc_channel), vref, volts))
        print ("*************")

    return volts
#====================================================================================

time.sleep(tiempo)

ch0_mult = 1000 #multiplication of the value given by the rpi

# open the file where the data will be stored
while (True):
    f = open("Tshirp.rtf", "a")


    Ch0Value = ch0_mult * getADCreading(address,channel0)
    f.write("T %f " % (Ch0Value))
    f.flush()
    print("Temp is %12.2f" % (Ch0Value))

    time.sleep(tiempo)

    Ch1Value = ch0_mult * getADCreading(address, channel1)
    f.write("NO2 %f " % (Ch1Value))
    f.flush()
    print("NO2 is %12.2f" % (Ch1Value))

    time.sleep(tiempo)

    now = datetime.now()
    Ch2Value = ch0_mult*getADCreading(address, channel2)
    f.write("NO2 %f " % (Ch2Value))
    f.flush()
    print("NO2 is %12.2f" % (Ch2Value))

    time.sleep(tiempo)

    Ch3Value = ch0_mult*getADCreading(address, channel3)
    f.write("OX %f " % (Ch3Value))
    f.flush()
    print("OX is %12.2f" % (Ch3Value))

    time.sleep(tiempo)

    Ch4Value = ch0_mult * getADCreading(address, channel4)
    f.write("OX %f %19.19s " % (Ch4Value, now))
    f.flush()
    print("OX at %19.19s is %12.2f" % (now, Ch4Value))

    time.sleep(tiempo)

    Ch5Value = ch0_mult * getADCreading(address, channel5)
    f.write("SO2 %f " % (Ch5Value))
    f.flush()
    print("SO2 is %12.2f" % (Ch5Value))

    time.sleep(tiempo)

    now = datetime.now()
    Ch6Value = ch0_mult * getADCreading(address, channel6)
    f.write("SO2 %f " % (Ch6Value))
    f.flush()
    print("SO2 is %12.2f" % (Ch6Value))

    time.sleep(tiempo)

    Ch7Value = ch0_mult * getADCreading(address, channel7)
    f.write("CO %f " % (Ch7Value))
    f.flush()
    print("CO is %12.2f" % (Ch7Value))

    time.sleep(tiempo)

    Ch8Value = ch0_mult * getADCreading(address, channel8)
    f.write("CO %f \n" % (Ch8Value))
    f.flush()
    print("CO is %12.2f \n" % (Ch8Value))

    time.sleep(tiempo)


    sys.stdout.flush() #on exit or at interruption, without this, the data could be lost

    time.sleep(zeit)


