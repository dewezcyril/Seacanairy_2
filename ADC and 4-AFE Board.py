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

#logging
# logging
import logging
log_file = './log/4AFE_board.log'
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

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
sleep = 0.5 #number of seconds to sleep between each channel reading
# has to be more than 0.2 (seconds)


def getADCreading(adc_address,adc_channel):
    """
    Get the tensions measured by the ADC
    :param adc_address: I²C address of the slave (bytes/hexadecimal)
    :param adc_channel: Wiring where to read the tension
    :return: tension (volts)
    """
    bus.write_byte(adc_address, adc_channel)
    time.sleep(sleep)
    reading = bus.read_i2c_block_data(adc_address, adc_channel, lange)
#----------- Start conversion for the Channel Data ----------
    valor = ((((reading[0]&0x3F))<<16))+((reading[1]<<8))+(((reading[2]&0xE0)))
    #add a debug function
    #debug(print("Valor is 0x%x" % valor))

#----------- End of conversion of the Channel ----------
    volts = valor * vref / max_reading


    if( (reading[0]& 0b11000000) == 0b11000000):
        logging.warning("Input voltage to channel 0x%x is either open or more than %5.2f. "
               "The reading may not be correct. Value read in is %12.8f Volts." % ((adc_channel), vref, volts))


    return volts
#====================================================================================

time.sleep(sleep)

ch0_mult = 1000 #multiplication of the value given by the rpi

now = datetime.now()

def AFE_temp():
    """
    Measure temperature from the Alphasense 4-AFE Board via ADC
    :return: Temperature (volts)
    """
    Tempv = ch0_mult * getADCreading(address,channel0)
    logging.debug("Tension from temperature sensor (AFE board) is ", tempv, " volts")
    time.sleep(sleep)
    return Tempv

def AFE_NO2():
    """
    Measure NO2 from the Alphasense 4-AFE Board via ADC
    :return: List[NO2 main (volts), NO2 auxiliary (volts)]
    """
    NO2v_main = ch0_mult * getADCreading(address, channel1)
    logging.debug("Tension from NO2 sensor (main) is ", NO2v_main, " volts")
    time.sleep(sleep)
    NO2v_aux = ch0_mult*getADCreading(address, channel2)
    logging.debug("Tension from NO2 sensor (aux) is ", NO2v_aux, " volts")
    time.sleep(sleep)
    return [NO2v_main, NO2v_aux]


def AFE_Ox():
    """
    Measure Ox from the Alphasense 4-AFE Board via ADC
    :return: List[Ox main (Volts), Ox Auxiliary (Volts)]
    """
    Oxv_main = ch0_mult*getADCreading(address, channel3)
    logging.debug("Tension from Ox sensor (main) is ", Oxv_main, " volts")
    time.sleep(sleep)
    Oxv_aux = ch0_mult * getADCreading(address, channel4)
    logging.debug("Tension from Ox sensor (aux) is ", Oxv_aux, " volts")
    time.sleep(sleep)
    return [Oxv_main, Oxv_aux]


def ADC_SO2():
    """
    Measure SO2 from the Alphasense 4-AFE Board via ADC
    :return:
    """
    SO2v_main = ch0_mult * getADCreading(address, channel5)
    logging.debug("Tension from SO2 sensor (main) is ", SO2v_main, " volts")
    time.sleep(sleep)
    SO2v_aux = ch0_mult * getADCreading(address, channel6)
    logging.debug("Tension from SO2 sensor (aux) is ", SO2v_aux, " volts")
    time.sleep(sleep)
    return [SO2v_main, SO2v_aux]


def ADC_CO():
    """
    Measure CO from the Alphasense 4-AFE Board via ADC
    :return:
    """
    COv_main = ch0_mult * getADCreading(address, channel7)
    time.sleep(sleep)
    logging.debug("Tension from CO sensor (main) is ", COv_main, " volts")
    COv_aux = ch0_mult * getADCreading(address, channel8)
    logging.debug("Tension from CO sensor (aux) is ", COv_aux, " volts")
    time.sleep(sleep)
    return [COv_main, COv_aux]


# open the file where the data will be stored
while (True):
#    f = open("Tshirp.rtf", "a")
    ADC_reading()

    time.sleep(sleep)

#    sys.stdout.flush() #on exit or at interruption, without this, the data could be lost

    time.sleep(zeit)

