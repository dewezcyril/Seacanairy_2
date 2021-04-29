from datetime import datetime
import time
import os.path
import yaml
import logging
import sys
import threading

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
sleep = 0.2  # number of seconds to sleep between each channel reading


# has to be more than 0.2 (seconds)


def getADCreading(adc_address, adc_channel):
    """
    Get the tensions measured by the ADC
    :param adc_address: I²C address of the slave (bytes/hexadecimal)
    :param adc_channel: Wiring where to read the tension
    :return: tension (volts)
    """

    attempts = 0


    while attempts < 4:

        try:
            bus.write_byte(adc_address, adc_channel)
            # print("Reading tension...                                         ", end='\r')
            time.sleep(sleep)
            reading = bus.read_i2c_block_data(adc_address, adc_channel, lange)
            # ----------- Start conversion for the Channel Data ----------
            valor = ((((reading[0] & 0x3F)) << 16)) + ((reading[1] << 8)) + (((reading[2] & 0xE0)))
            # add a debug function
            # debug(print("Valor is 0x%x" % valor))

            # ----------- End of conversion of the Channel ----------
            volts = round(valor * vref / max_reading, 7)
            # Rounding to 7 decimals because ADC accuracy is 3.9 microvolt
            # print("Reading tension...", volts, "V", end='\r')

            if (reading[0] & 0b11000000) == 0b11000000:
                logger.error(
                    "Input voltage is either open or more than " + str(vref) + "Volts.")
                logger.warning("The reading may not be correct. Value read is " + str(volts) + " mV")

            # time.sleep(sleep)  # be sure to have some time laps between two I2C reading/writing # i2c don't care!
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
        tempv = round(ch0_mult * volts, 5)
        logger.debug("Tension from temperature sensor (AFE board) is " + str(tempv) + " mV")
        time.sleep(sleep)

        temp_to_return = {
            "temperature raw": tempv,
        }
    else:
        logger.critical("Failed to read temperature")
        temp_to_return = {
            "temperature raw": "error",
        }

    return temp_to_return


def get_NO2():
    """
    Measure NO2 from the Alphasense 4-AFE Board via ADC
    :return: List[NO2 main (volts), NO2 auxiliary (volts)]
    """
    volts = getADCreading(address, channel1)
    if volts is not False:
        NO2v_main = round(ch0_mult * volts, 5)
        logger.debug("Tension from NO2 sensor (main) is " + str(NO2v_main) + " mV")
        time.sleep(sleep)
        NO2v_aux = round(ch0_mult * getADCreading(address, channel2), 5)
        logger.debug("Tension from NO2 sensor (aux) is " + str(NO2v_aux) + " mV")
        time.sleep(sleep)

        # ppb = ((calibration['NO2']['WE']))

        NO2_to_return = {
            "NO2 main": NO2v_main,
            "NO2 aux": NO2v_aux,
        }
    else:
        logger.critical("Failed to read NO2 sensor")
        NO2_to_return = {
            "NO2 main": "error",
            "NO2 aux": "error",
        }

    return NO2_to_return


def get_OX():
    """
    Measure Ox from the Alphasense 4-AFE Board via ADC
    :return: List[Ox main (Volts), Ox Auxiliary (Volts)]
    """
    volts = getADCreading(address, channel3)
    if volts is not False:
        Oxv_main = round(ch0_mult * volts, 5)
        logger.debug("Tension from Ox sensor (main) is " + str(Oxv_main) + " mV")
        time.sleep(sleep)
        Oxv_aux = round(ch0_mult * getADCreading(address, channel4), 5)
        logger.debug("Tension from Ox sensor (aux) is " + str(Oxv_aux) + " mV")
        time.sleep(sleep)

        OX_to_return = {
            "OX main": Oxv_main,
            "OX aux": Oxv_aux,
        }

    else:
        logger.critical("Failed to read OX")
        OX_to_return = {
            "OX main": "error",
            "OX aux": "error",
        }

    return OX_to_return


def get_SO2():
    """
    Measure SO2 from the Alphasense 4-AFE Board via ADC
    :return:
    """
    volts = getADCreading(address, channel5)
    if volts is not False:
        SO2v_main = round(ch0_mult * volts, 5)
        logger.debug("Tension from SO2 sensor (main) is " + str(SO2v_main) + " mV")
        time.sleep(sleep)
        SO2v_aux = round(ch0_mult * getADCreading(address, channel6), 5)
        logger.debug("Tension from SO2 sensor (aux) is " + str(SO2v_aux) + " mV")
        time.sleep(sleep)

        SO2_to_return = {
            "SO2 main": SO2v_main,
            "SO2 aux": SO2v_aux,
        }

    else:
        logger.critical("Failed to read SO2")

        SO2_to_return = {
            "SO2 main": "error",
            "SO2 aux": "error",
        }

    return SO2_to_return


def get_CO():
    """
    Measure CO from the Alphasense 4-AFE Board via ADC
    :return:
    """
    volts = getADCreading(address, channel7)
    if volts is not False:
        COv_main = round(ch0_mult * volts, 5)
        time.sleep(sleep)
        logger.debug("Tension from CO sensor (main) is " + str(COv_main) + " mV")
        COv_aux = round(ch0_mult * getADCreading(address, channel8), 5)
        logger.debug("Tension from CO sensor (aux) is " + str(COv_aux) + " mV")
        time.sleep(sleep)

        CO2_to_return = {
            "CO main": COv_main,
            "CO aux": COv_aux,
        }
    else:
        logger.critical("Failed to read CO")

        CO2_to_return = {
            "CO main": "error",
            "CO aux": "error",
        }

    return CO2_to_return


def apply_calibration(dictionary):
    dictionary.update({
        'NO2 ppm': "-",
        'OX ppm': "-",
        'SO2 ppm': "-",
        'CO ppm': "-",
        'temperature': "-"
    })
    return dictionary


def getdata():
    """
    Get all available data from the 4-AFE Alphasense Board (one instant reading)
    :return: Dictionary{'NO2 ppm', NO2 main', 'NO2 aux', 'OX ppm', 'OX main', 'OX aux',
                'SO2 ppm', 'SO2 main', 'SO2 aux', 'CO ppm', 'CO main', 'CO aux',
                'temperature', 'temperature raw'}
    """

    data = {}

    data.update(get_NO2())
    data.update(get_OX())
    data.update(get_SO2())
    data.update(get_CO())
    data.update(get_temp())
    data = apply_calibration(data)
    print("\t\tppm\t|\tmain (mV)\t\t|\taux (mV)")
    print("NO2:\t", data["NO2 ppm"],"\t|\t", data["NO2 main"], "\t|\t", data["NO2 aux"])
    print("OX:\t", data["OX ppm"], "\t|\t", data["OX main"], "\t|\t", data["OX aux"])
    print("SO2:\t", data["SO2 ppm"], "\t|\t", data["SO2 main"], "\t|\t", data["SO2 aux"])
    print("CO:\t", data["CO ppm"], "\t|\t", data["CO main"], "\t|\t", data["CO aux"])
    print("Temperature:\t", data["temperature"], "\t|\t", data["temperature raw"])

    return data


def start_averaged_data(number_of_measurements, waiting=0):
    """
    Take some measurements, and make an average of them.
    :param number_of_measurements: number of measurement, around 2 seconds for each one
    :return: Dictionary{'NO2 main', 'NO2 aux', 'OX main', 'OX aux',
                'SO2 main', 'SO2 aux', 'CO main', 'CO aux',
                'temperature raw'}
    """

    time.sleep(waiting)  # for threading

    NO2_main = []
    NO2_aux = []
    
    OX_main = []
    OX_aux = []
    
    SO2_main = []
    SO2_aux = []
    
    CO_main = []
    CO_aux = []
    
    temperature_main = []
    
    for _ in range(number_of_measurements):
        NO2 = get_NO2()
        NO2_main += [NO2['NO2 main']]
        NO2_aux += [NO2['NO2 aux']]
        
        OX = get_OX()
        OX_main += [OX['OX main']]
        OX_aux += [OX['OX aux']]
        
        SO2 = get_SO2()
        SO2_main += [SO2['SO2 main']]
        SO2_aux += [SO2['SO2 aux']]
        
        CO = get_CO()
        CO_main += [CO['CO main']]
        CO_aux += [CO['CO aux']]

        temp = get_temp()
        temperature_main += [temp['temperature raw']]
    
    sum = 0
    
    for i in range(len(NO2_main)):
        sum += NO2_main[i]
    NO2_main = sum/len(NO2_main)

    sum = 0

    for i in range(len(NO2_aux)):
        sum += NO2_aux[i]
    NO2_aux = sum/len(NO2_aux)

    sum = 0

    for i in range(len(OX_main)):
        sum += OX_main[i]
    OX_main = sum/len(OX_main)

    sum = 0

    for i in range(len(OX_aux)):
        sum += OX_aux[i]
    OX_aux = sum/len(OX_aux)

    sum = 0

    for i in range(len(SO2_main)):
        sum += SO2_main[i]
    SO2_main = sum/len(SO2_main)

    sum = 0

    for i in range(len(SO2_aux)):
        sum += SO2_aux[i]
    SO2_aux = sum/len(SO2_aux)

    sum = 0

    for i in range(len(CO_main)):
        sum += CO_main[i]
    CO_main = sum/len(CO_main)

    sum = 0

    for i in range(len(CO_aux)):
        sum += CO_aux[i]
    CO_aux = sum/len(CO_aux)

    sum = 0

    for i in range(len(temperature_main)):
        sum += temperature_main[i]
    temperature = sum/len(temperature_main)

    global thread_data

    thread_data = {
        'NO2 main': NO2_main,
        'NO2 aux': NO2_aux,
        'OX main': OX_main,
        'OX aux': OX_aux,
        'SO2 main': SO2_main,
        'SO2 aux': SO2_aux,
        'CO main': CO_main,
        'CO aux': CO_aux,
        'temperature raw': temperature
    }

    return thread_data


def start_background_average_measurement(number_of_measurements, delay=0):
    print("Starting background AFE average reading...")
    x = threading.Thread(target=start_averaged_data, args=([number_of_measurements, delay]), daemon=True)
    x.start()


def get_averaged_data():
    global thread_data

    data = apply_calibration(thread_data)

    print("NO2:\t", data["NO2 ppm"],"\t|\t", data["NO2 main"], "\t|\t", data["NO2 aux"])
    print("OX:\t", data["OX ppm"], "\t|\t", data["OX main"], "\t|\t", data["OX aux"])
    print("SO2:\t", data["SO2 ppm"], "\t|\t", data["SO2 main"], "\t|\t", data["SO2 aux"])
    print("CO:\t", data["CO ppm"], "\t|\t", data["CO main"], "\t|\t", data["CO aux"])
    print("Temperature:\t", data["temperature"], "\t|\t", data["temperature raw"])

    return data


# open the file where the data will be stored
if __name__ == "__main__":
    # Execute an execution test if the script is executed from there
    while (True):
        start_background_average_measurement(3)
        time.sleep(20)
        get_averaged_data()
        print("WAITING...")
        time.sleep(5)
