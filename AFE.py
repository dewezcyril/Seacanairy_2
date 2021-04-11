from datetime import datetime
import time
import os.path
import yaml
import logging
import sys

# --------------------------------------------------
# I2C
# --------------------------------------------------
from smbus2 import SMBus
from sys import exit

# emplacement variable
bus = SMBus(1)

# attributed canals and associated emplacements variable
address = 0b1110110

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------

# Get current directory
current_working_directory = str(os.getcwd())

with open(current_working_directory + '/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

store_debug_messages = settings['AFE Board']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

# calibration = settings['AFE Board']['Calibration']


# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
# all the settings and other code for the logging
# logging = tak a trace of some messages in a file to be reviewed afterward (check for errors fe)


def set_logger(message_level, log_file):
    # set up logging to file
    logging.basicConfig(level=message_level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%d-%m %H:%M',
                        filename=log_file,
                        filemode='a')

    logger = logging.getLogger('AFE Board')  # name of the logger
    # all further logging must be called by logger.'level' and not logging.'level'
    # if not, the logging will be displayed as 'ROOT' and NOT 'OPC-N3'
    return logger


if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    # Create a file to store the log if it doesn't exist
    log_file = current_working_directory + "/log/Alphasense_board-debugging.log"
    if not os.path.isfile(log_file):
        os.mknod(log_file)
    print("Alphasense Board DEBUG messages will be shown and stored in '" + str(log_file) + "'")
    logger = set_logger(message_level, log_file)
    # define a Handler which writes INFO messages or higher to the sys.stderr/display
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

else:  # if this file is considered as a library (if you execute 'seacanairy.py' for example)
    # it will only print and store INFO messages and above in the corresponding log_file
    if store_debug_messages:
        message_level = logging.DEBUG
    else:
        message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/' + project_name + '-log.log'  # complete location needed on the RPI
    # no need to add a handler, because there is already one in seacanairy.py
    logger = set_logger(message_level, log_file)

# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as 'ROOT' and NOT 'GPS'

# --------------------------------------------------
# ADC channels
# --------------------------------------------------

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

# reference voltage of the ADC
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

lange = 0x06  # number of bytes to read in the block
zeit = 15  # number of seconds to sleep between each measurement
sleep = 0.5  # number of seconds to sleep between each channel reading


# has to be more than 0.2 (seconds)


def getADCreading(adc_address, adc_channel):
    """
    Get the tensions measured by the ADC
    :param adc_address: I²C address of the slave (bytes/hexadecimal)
    :param adc_channel: Wiring where to read the tension
    :return: tension (volts)
    """

    attempts = 0

    print("Reading tension...               ", end='\r')

    while attempts < 4:

        try:
            bus.write_byte(adc_address, adc_channel)
            time.sleep(sleep)
            reading = bus.read_i2c_block_data(adc_address, adc_channel, lange)
            # ----------- Start conversion for the Channel Data ----------
            valor = ((((reading[0] & 0x3F)) << 16)) + ((reading[1] << 8)) + (((reading[2] & 0xE0)))
            # add a debug function
            # debug(print("Valor is 0x%x" % valor))

            # ----------- End of conversion of the Channel ----------
            volts = valor * vref / max_reading
            print("Reading tension...", volts, "V", end='\r')

            if (reading[0] & 0b11000000) == 0b11000000:
                logger.error(
                    "Input voltage to channel " + str(adc_channel) + " is either open or more than " + str(vref) + "Volts."
                        " Value read is: " + str(reading[0]))
                logger.warning("The reading may not be correct. Value read is " + str(volts) + " mV")

            time.sleep(sleep)  # be sure to have some time laps between two I2C reading/writing
            return volts

        except:
            if attempts >= 3:
                logger.critical("i2c transmission failed 3 consecutive times(" + str(sys.exc_info())
                         + "), skipping i2c reading")
                return False  # indicate clearly that system has failed

            logger.error("Error in the i2c transmission (" + str(sys.exc_info())
                         + "), trying again... (" + str(attempts) + "/3)")
            attempts += 1  # increment of reading_trials
            time.sleep(1)  # if transmission fails, wait a bit to try again (sensor is maybe busy)

    return False

# ====================================================================================


ch0_mult = 1000  # multiplication of the value given by the rpi


def get_temp():
    """
    Measure temperature from the Alphasense 4-AFE Board via ADC
    Note that the sensor is not located in the gas hood.
    :return: Temperature (volts)
    """

    volts = getADCreading(address, channel0)
    if volts is not False:
        tempv = ch0_mult * volts
        logger.debug("Tension from temperature sensor (AFE board) is " + str(tempv) + " mV")
        time.sleep(sleep)

        temp_to_return = {
            "temperature raw": tempv,
            "temperature": "-"
        }
    else:
        logger.critical("Failed to read temperature")
        temp_to_return = {
            "temperature raw": "error",
            "temperature": "-"
        }

    return temp_to_return


def get_NO2():
    """
    Measure NO2 from the Alphasense 4-AFE Board via ADC
    :return: List[NO2 main (volts), NO2 auxiliary (volts)]
    """
    volts = getADCreading(address, channel1)
    if volts is not False:
        NO2v_main = ch0_mult * volts
        logger.debug("Tension from NO2 sensor (main) is " + str(NO2v_main) + " mV")
        time.sleep(sleep)
        NO2v_aux = ch0_mult * getADCreading(address, channel2)
        logger.debug("Tension from NO2 sensor (aux) is " + str(NO2v_aux) + " mV")
        time.sleep(sleep)

        # ppb = ((calibration['NO2']['WE']))

        NO2_to_return = {
            "NO2 main": NO2v_main,
            "NO2 aux": NO2v_aux,
            "NO2 ppm": "-"
        }
    else:
        logger.critical("Failed to read NO2 sensor")
        NO2_to_return = {
            "NO2 main": "error",
            "NO2 aux": "error",
            "NO2 ppm": "error"
        }

    return NO2_to_return


def get_OX():
    """
    Measure Ox from the Alphasense 4-AFE Board via ADC
    :return: List[Ox main (Volts), Ox Auxiliary (Volts)]
    """
    volts = getADCreading(address, channel3)
    if volts is not False:
        Oxv_main = ch0_mult * volts
        logger.debug("Tension from Ox sensor (main) is " + str(Oxv_main) + " mV")
        time.sleep(sleep)
        Oxv_aux = ch0_mult * getADCreading(address, channel4)
        logger.debug("Tension from Ox sensor (aux) is " + str(Oxv_aux) + " mV")
        time.sleep(sleep)

        OX_to_return = {
            "OX main": Oxv_main,
            "OX aux": Oxv_aux,
            "OX ppm": "-"
        }

    else:
        logger.critical("Failed to read OX")
        OX_to_return = {
            "OX main": "error",
            "OX aux": "error",
            "OX ppm": "error"
        }

    return OX_to_return


def get_SO2():
    """
    Measure SO2 from the Alphasense 4-AFE Board via ADC
    :return:
    """
    volts = getADCreading(address, channel5)
    if volts is not False:
        SO2v_main = ch0_mult * volts
        logger.debug("Tension from SO2 sensor (main) is " + str(SO2v_main) + " mV")
        time.sleep(sleep)
        SO2v_aux = ch0_mult * getADCreading(address, channel6)
        logger.debug("Tension from SO2 sensor (aux) is " + str(SO2v_aux) + " mV")
        time.sleep(sleep)

        SO2_to_return = {
            "SO2 main": SO2v_main,
            "SO2 aux": SO2v_aux,
            "SO2 ppm": "-"
        }

    else:
        logger.critical("Failed to read SO2")

        SO2_to_return = {
            "SO2 main": "error",
            "SO2 aux": "error",
            "SO2 ppm": "error"
        }

    return SO2_to_return


def get_CO():
    """
    Measure CO from the Alphasense 4-AFE Board via ADC
    :return:
    """
    volts = getADCreading(address, channel7)
    if volts is not False:
        COv_main = ch0_mult * volts
        time.sleep(sleep)
        logger.debug("Tension from CO sensor (main) is " + str(COv_main) + " mV")
        COv_aux = ch0_mult * getADCreading(address, channel8)
        logger.debug("Tension from CO sensor (aux) is " + str(COv_aux) + " mV")
        time.sleep(sleep)

        CO2_to_return = {
            "CO main": COv_main,
            "CO aux": COv_aux,
            "CO ppm": "-"
        }
    else:
        logger.critical("Failed to read CO")

        CO2_to_return = {
            "CO main": "error",
            "CO aux": "error",
            "CO ppm": "error"
        }

    return CO2_to_return


def getdata(average=None, interval=0.5):
    """
    Get all available data from the 4-AFE Alphasense Board
    :param average: number of measurement to take to make average
    :param interval: interval of time between those measurements
    :return: List[temperature, NO2, OX, SO2, CO]
    """

    to_return = {}

    if average is not None:
        temperature = []
        NO2 = []
        OX = []
        SO2 = []
        CO = []

        for _ in range(average):
            temperature.append(temp())
            NO2.append(NO2())
            OX.append(OX())
            SO2.append(SO2())
            CO.append(CO())
            time.sleep(interval)
        sum_temperature = 0
        sum_NO2 = 0
        sum_OX = 0
        sum_SO2 = 0
        sum_CO = 0
        for i in range(average):
            sum_temperature += temperature[i]
            sum_NO2 += NO2[i]
            sum_OX += OX[i]
            sum_SO2 = SO2[i]
            sum_CO = CO[i]

        temperature = sum_temperature / average
        NO2 = sum_NO2 / average
        OX = sum_OX / average
        SO2 = sum_SO2 / average
        CO = sum_CO / average
        return [temperature, NO2, OX, SO2, CO]

    elif average is None:
        print("\t\tppm\t|\tmain (mV)\t\t|\taux (mV)")
        NO2_data = get_NO2()
        print("                                                                      ", end='\r')
        print("NO2:\t", NO2_data["NO2 ppm"],"\t|\t", NO2_data["NO2 main"], "\t|\t", NO2_data["NO2 aux"])
        to_return.update(NO2_data)
        OX_data = get_OX()
        print("                                                                      ", end='\r')
        print("OX:\t", OX_data["OX ppm"], "\t|\t", OX_data["OX main"], "\t|\t", OX_data["OX aux"])
        to_return.update(OX_data)
        SO2_data = get_SO2()
        print("                                                                      ", end='\r')
        print("SO2:\t", SO2_data["SO2 ppm"], "\t|\t", SO2_data["SO2 main"], "\t|\t", SO2_data["SO2 aux"])
        to_return.update(SO2_data)
        CO_data = get_CO()
        print("                                                                      ", end='\r')
        print("CO:\t", CO_data["CO ppm"], "\t|\t", CO_data["CO main"], "\t|\t", CO_data["CO aux"])
        to_return.update(CO_data)
        temp = get_temp()
        print("                                                                      ", end='\r')
        print("Temperature:\t", temp["temperature"], "\t|\t", temp["temperature raw"])
        to_return.update(temp)

        return to_return

    else:
        raise TypeError("Check arguments of AFE.getdata()")


# open the file where the data will be stored
if __name__ == "__main__":
    # Execute an execution test if the script is executed from there
    while (True):
        data = getdata()
        print(data)
        print("WAITING...")
        time.sleep(10)
