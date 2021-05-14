# get the time
import time
from datetime import date, datetime

# Get the errors
import sys

# Create folders and files
import os

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg
# 'SMBus' is the general driver for i2c communication
# 'i2c_msg' allow to make i2c write followed by i2c read WITHOUT any STOP byte (see sensor documentation)

# logging
import logging

# yaml settings
import yaml

# progress bar during sampling
from progress.bar import IncrementalBar

# take measurement while doing something else
import threading

# I²C address of the CO2 device
air_address = 1
O2_address = 2
CO2_address = 3
N2O_address = 4
Ar_address = 5

# emplacement variable
bus = SMBus(1)  # make it easier to read/write to the sensor (bus.read or bus.write...)

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------
# Get current directory
current_working_directory = str(os.getcwd())

with open(current_working_directory + '/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()  # close the file after use

store_debug_messages = settings['Air flow sensor']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']


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

    logger = logging.getLogger('Flow meter')  # name of the logger
    # all further logging must be called by logger.'level' and not logging.'level'
    # if not, the logging will be displayed as 'ROOT' and NOT 'OPC-N3'
    return logger


if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    # Create a file to store the log if it doesn't exist
    log_file = current_working_directory + "/log/flow_meter-debugging.log"
    if not os.path.isfile(log_file):
        os.mknod(log_file)
    print("Flow meter DEBUG messages will be shown and stored in '" + str(log_file) + "'")
    logger = set_logger(message_level, log_file)
    # The following HANDLER must be activated ONLY if you run this code alone
    # Without the 'if __name__ == '__main__' condition, all the logging messages are displayed 3 TIMES
    # (once for the handler in CO2.py, once for the handler in OPCN3.py, and once for the handler in seacanairy.py)

    # define a Handler which writes INFO messages or higher to the sys.stderr/display (= the console)
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

else:  # if this file is considered as a library (if you execute seacanairy.py for example)
    # if the user asked to store all the messages in 'seacanairy_settings.yaml'
    if store_debug_messages:
        message_level = logging.DEBUG
    # if the user don't want to store everything
    else:
        message_level = logging.INFO
    # Create a file to store the log if it doesn't exist yet
    log_file = current_working_directory + "/" + project_name + "/" + project_name + "-log.log"
    logger = set_logger(message_level, log_file)
    # no need to add a handler, because there is already one in seacanairy.py


# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as ROOT and NOT 'CO2 sensor'

# --------------------------------------------------------


def loading_bar(name, delay):
    """
    Show a loading bar on the screen during a a certain amount of time
    Make the user understand the software is doing/waiting for something
    :param name: Text to be shown on the left of the loading bar
    :param length: Amount of time the system is waiting in seconds
    :return: nothing
    """
    bar = IncrementalBar(name, max=(2 * delay), suffix='%(elapsed)s/' + str(delay) + ' seconds')
    for i in range(2 * delay):
        time.sleep(0.5)
        bar.next()
    bar.finish()
    return


def digest(buf):
    """
    Calculate the CRC8 checksum (based on the CO2 documentation example)
    :param buf: List[bytes to digest]
    :return: checksum
    """
    # Translation of the C++ code given in the documentation
    crcVal = 0x00
    _from = 0  # the first item in a list is named 0
    _to = len(buf)  # if there are two items in the list, then len() return 1 --> range(0, 1) = 2 loops

    for i in range(_from, _to):
        curVal = buf[i]

        for j in range(0, 8):  # C++ stops when J is not < 8 --> same for python in range
            if ((crcVal ^ curVal) & 0x80) != 0:
                crcVal = (crcVal << 1) ^ 0x31

            else:
                crcVal = (crcVal << 1)

            curVal = (curVal << 1)  # this line is in the "for j" loop, not in the "for i" loop

    checksum = crcVal & 0xff  # keep only the 8 last bits

    return checksum


def check(checksum, data):
    """
    Check that the data transmitted are correct using the data and the given checksum
    :param checksum: Checksum given by the sensor (see sensor doc)
    :param data: List[bytes to be used in the checksum calculation (see sensor doc)]
    :return: True if the data are correct, False if not
    """
    calculation = digest(data)
    if calculation == checksum:
        logger.debug("CRC8 is correct, data are valid")
        return True
    else:
        logger.debug("CRC8 does not fit, data are wrong")
        logger.error("Checksum is wrong, sensor checksum is: " + str(checksum) +
                     ", seacanairy checksum is: " + str(calculation) +
                     ", data returned by the sensor is:" + str(data))
        if data[0] and data[1] == 0:
            logger.debug("Sensor returned 0 values, it is not ready, waiting a bit")
            print("Sensor not ready, waiting...", end='\r')
            time.sleep(3)
        return False


def check(checksum, data):
    """
    Check that the data transmitted are correct using the data and the given checksum
    :param checksum: Checksum given by the sensor (see sensor doc)
    :param data: List[bytes to be used in the checksum calculation (see sensor doc)]
    :return: True if the data are correct, False if not
    """
    calculation = digest(data)
    if calculation == checksum:
        logger.debug("CRC8 is correct, data are valid")
        return True
    else:
        logger.debug("CRC8 does not fit, data are wrong")
        logger.error("Checksum is wrong, sensor checksum is: " + str(checksum) +
                     ", seacanairy checksum is: " + str(calculation) +
                     ", data returned by the sensor is:" + str(data))
        if data[0] and data[1] == 0:
            logger.debug("Sensor returned 0 values, it is not ready, waiting a bit")
            print("Sensor not ready, waiting...", end='\r')
            time.sleep(3)
        return False


def get_data(print_data=True):
    """
    Get flow measurement from the Sensirion mass flow meter 4100
    :return: dictionary {"flow [sccm]", "flow [slm]", "flow [slh]}
    """
    logger.debug("Reading flow from Sensirion Mass Flow Meter Sensor")
    if print_data:
        print("Reading flow...", end='\r')

    to_return = {
        "flow [sccm]": "error",
        "flow [slm]": "error",
        "flow [slh]": "error"
    }

    attempts = 1

    while attempts <= 4:
        if attempts >= 3:
            logger.critical("i2c transmission failed 3 consecutive times, skipping this flow reading")
            return to_return
        try:
            answer = bus.read_i2c_block_data(air_address, 0xF1, 3)
            logger.debug("i2c succeeded, answer is: " + str(answer))
            if check(answer[2], answer[0:2]):
                break
        except:
            attempts += 1
            logger.error("i2c communication failed while reading flow (" + str(sys.exc_info()) + ")")

    if answer[0] == 255:
        flow_sccm = 0
        flow_slm = 0
        flow_slh = 0
    else:
        flow_sccm = (answer[0] << 8) + answer[1]
        flow_slm = flow_sccm / 1000
        flow_slh = round(flow_slm * 60, 2)

    if print_data:
        print("                                      ", end='\r')
        print(flow_sccm, "\tsccm [~= mL/min]")
        print(flow_slm, "\tslm [~= L/min]")
        print(flow_slh, "\tslh [~= L/h]")

    to_return.update({
        "flow [sccm]": flow_sccm,
        "flow [slm]": flow_slm,
        "flow [slh]": flow_slh
    })

    return to_return


def start_averaged_measurement(sampling_period, number_of_measurement_during_sampling_period, delay=0):
    global sccm
    global slm
    global slh
    sccm = []
    slm = []
    slh = []

    time.sleep(delay)
    loop = 0
    sleep = sampling_period / number_of_measurement_during_sampling_period
    while loop < number_of_measurement_during_sampling_period:
        reading = get_data(print_data=False)
        sccm.append(reading['flow [sccm]'])
        slm.append(reading['flow [slm]'])
        slh.append(reading['flow [slh]'])
        time.sleep(sleep)
        loop += 1


def get_averaged_measurement():

    to_return = {
        "average flow [sccm]": "error",
        "average flow [slm]": "error",
        "average flow [slh]": "error",
    }

    global sccm
    global slm
    global slh
    try:
        sum = 0
        for i in range(len(sccm)):
            sum += sccm[i]
        sccm = round(sum/len(sccm), 0)

        sum = 0
        for i in range(len(slm)):
            sum += slm[i]
        slm = round(sum/len(slm), 3)

        sum = 0
        for i in range(len(slh)):
            sum += slh[i]
        slh = round(sum/len(slh), 2)

    except:
        logger.error("Error occurred while computing average flow rate (" + str(sys.exc_info()) + ")")
        return to_return

    print("Average flow rate:")
    print(sccm, "\tsccm [~= mL/min]")
    print(slm, "\tslm [~= L/min]")
    print(slh, "\tslh [~= L/h]")

    to_return.update({
        "average flow [sccm]": sccm,
        "average flow [slm]": slm,
        "average flow [slh]": slh,
    })

    return to_return


if __name__ == "__main__":
    while True:
        get_data()
        time.sleep(1)