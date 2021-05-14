#! /home/pi/seacanairy_project/venv/bin/python3
"""
Library for the use of E+E Elektronik EE894 CO2 sensor via I²C communication
"""
# --------------------------------------------------------
# USEFUL VARIABLES
# --------------------------------------------------------

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

# I²C address of the CO2 device
CO2_address = 0x33  # i2c address by default, can be changed (see sensor doc)

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

store_debug_messages = settings['CO2 sensor']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

measurement_delay = settings['CO2 sensor']['Amount of time required for the sensor to take the measurement']

max_attempts = settings['CO2 sensor']['Number of reading attempts']

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

    logger = logging.getLogger('CO2 sensor')  # name of the logger
    # all further logging must be called by logger.'level' and not logging.'level'
    # if not, the logging will be displayed as 'ROOT' and NOT 'OPC-N3'
    return logger


if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    # Create a file to store the log if it doesn't exist
    log_file = current_working_directory + "/log/CO2-debugging.log"
    if not os.path.isfile(log_file):
        os.mknod(log_file)
    print("CO2 Sensor DEBUG messages will be shown and stored in '" + str(log_file) + "'")
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
    :param name: Text to be shown on the left of the loading bar (waiting, sampling…)
    :param length: Amount of time the system is waiting (seconds)
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
    :param buf: List of bytes to digest [bytes to digest]
    :return: checksum
    """
    # Translation of the C++ code given in the documentation
    crcVal = 0xff
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
    :param List of bytes transmitted by the sensor before the checksum (see sensor doc)
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
            logger.debug("Sensor returned 0 values, it is not ready, waiting a little bit")
            print("Sensor not ready, waiting...", end='\r')
            time.sleep(3)
        return False


def status(print_information=True):
    """
    Read the status byte of the CO2 sensor
    !! It will trigger a new measurement if the previous one is older than 10 seconds
    :param: print_information: Optional: False to hide the messages
    :return: True if last measurement is OK, False if NOK
    """
    logger.debug("Reading sensor status")
    try:
        with SMBus(1) as bus:
            # reading = read_from_custom_memory(0x71, 1)
            reading = bus.read_byte_data(CO2_address, 0x71)
        # see documentation for the following decryption
        CO2_status = reading & 0b00001000
        temperature_status = reading & 0b00000010
        humidity_status = reading & 0b00000001
        if print_information:  # if user/software indicate to print the information
            if CO2_status == 0:
                logger.debug("CO2 status is OK")
            else:
                logger.warning("CO2 status is NOK")
            if temperature_status == 0:
                logger.debug("Temperature status is OK")
            else:
                logger.warning("Temperature is NOK")
            if humidity_status == 0:
                logger.debug("Humidity status is OK")
            else:
                logger.warning("Humidity status is NOK")
        if CO2_status or humidity_status != 0:
            # Only CO2_status and humidity_status, because for no known reason temperature status is always NOK
            return False
        else:
            # Everything is OK
            return True
    except:
        logger.critical("Failed to read sensor status")
        return True  # try to go ahead in all cases


def getRHT():
    """
    Read the last Temperature and Relative Humidity measured, process the bytes, check checksum, convert in °C and %RH
    :return:  Dictionary with the following items {"RH", "temperature"}
    """
    logger.debug("Reading RH and Temperature from CO2 sensor")

    write = i2c_msg.write(CO2_address, [0xE0, 0x00])  # see documentation, example for reading t° and RH
    read = i2c_msg.read(CO2_address, 6)

    attempts = 0  # trial counter for the checksum and the validity of the data received
    reading_trials = 0  # trial counter for the i2c communication

    # In case there is a problem and it return nothing, return "error"
    data = {
        "relative humidity": "error",
        "temperature": "error"
    }

    # all the following code is in a loop so that if the checksum is wrong, it start a new measurement
    while attempts <= max_attempts:

        while reading_trials <= max_attempts:  # reading loop, will try again if the i2c communication fails
            try:  # SMBUS stop working in case of error, avoid the software to crash in case of i2c error
                with SMBus(1) as bus:
                    bus.i2c_rdwr(write, read)
                break  # break the loop if the try has not failed at the previous line, jump to the process of data

            except:  # what happens if the i2c fails
                if reading_trials == max_attempts:
                    logger.critical("i2c transmission failed "
                                    + str(max_attempts) + "consecutive times, skipping this RH and temperature reading")
                    return data  # indicate clearly that data are wrong

                logger.error("Error in the i2c transmission (" + str(sys.exc_info())
                             + "), trying again... (" + str(reading_trials + 1) + "/" + str(max_attempts) + ")")
                reading_trials += 1  # increment of reading_trials
                time.sleep(3)  # if transmission fails, wait a bit to try again (sensor is maybe busy)

        # process the data given by the sensor
        reading = list(read)
        # if the two checksums are correct...
        if check(reading[2], [reading[0], reading[1]]) and check(reading[5], [reading[3], reading[4]]):
            # reading << 8 = shift bytes 8 times to the left, say differently, add 8 times 0 on the right
            temperature = round(((reading[0] << 8) + reading[1]) / 100 - 273.15, 2)
            relative_humidity = ((reading[3] << 8) + reading[4]) / 100

            print("Temperature is:", temperature, "°C", end="")
            print("\t| Relative humidity is:", relative_humidity, "%RH")

            # Create a dictionnary containing all the data
            data = {
                "relative humidity": relative_humidity,
                "temperature": temperature
            }

            return data

        else:  # if one or both checksums are not corrects
            if attempts == max_attempts:
                logger.error("Data were wrong "
                             + str(max_attempts) + " consecutive times, skipping this RH and temperature reading")
                return data  # indicate on the SD card that data are wrong

            else:
                attempts += 1
                logger.warning("Error in the data received (wrong checksum), reading data again... ("
                               + str(attempts) + "/" + str(max_attempts) + ")")
                time.sleep(4)  # avoid to close i2c communication


def getCO2P():
    """
    Read the last CO2 instant, CO2 average and pressure measurements, process the bytes, check checksum,
    convert in hPa and ppm
    :return: Dictionary containing the following items {"average", "instant", "pressure"}
    """
    logger.debug('Reading of CO2 and pressure')

    write = i2c_msg.write(CO2_address, [0xE0, 0x27])  # see documentation, reading of CO2 and pressure example
    read = i2c_msg.read(CO2_address, 9)

    attempts = 0  # trial counter for the checksum and the validity of the data received
    reading_trials = 0  # trial counter for the i2c communication

    # Create a dictionary containing the data, return "error" in case of error
    data = {
        "average": "error",
        "instant": "error",
        "pressure": "error"
    }

    # all the following code is in a loop so that if the checksum is wrong, it start a new measurement
    while attempts <= max_attempts:

        while reading_trials <= max_attempts:  # reading loop, will try again if the i2c communication fails
            try:  # SMBUS stop working in case of error, avoid the software to crash in case of i2c error
                with SMBus(1) as bus:
                    bus.i2c_rdwr(write, read)
                break  # break the loop if the try has not failed at the previous line, jump to the process of data

            except:  # what happens if the i2c fails
                if reading_trials == max_attempts:
                    logger.critical("i2c transmission failed "
                                    + str(max_attempts) + " consecutive times, skipping CO2 and pressure reading (" +
                                    str(sys.exc_info()) + ")")
                    return data  # indicate clearly that the data are wrong

                logger.error("Error in the i2c transmission, trying again... (" + str(sys.exc_info()) + ")")
                reading_trials += 1  # increment of reading_trials
                print("Waiting 3 seconds...", end='\r')
                time.sleep(3)  # if I²C comm fails, wait a little bit and try again (sensor is maybe busy)

        # process the data given by the sensor
        reading = list(read)
        # if the two checksums are correct...
        if check(reading[2], [reading[0], reading[1]]) and check(reading[5], [reading[3], reading[4]]) and check(
                reading[8], [reading[6], reading[7]]):
            pressure = (((reading[6]) << 8) + reading[7]) / 10  # reading << 8 = shift bytes 8 times to the left
            print("Pressure is:", pressure, "mbar")

            CO2_average = (reading[0] << 8) + reading[1]  # reading << 8 = shift bytes 8 times to the left
            print("CO2 average is:", CO2_average, "ppm", end="")

            CO2_raw = (reading[3] << 8) + reading[4]
            print("\t| CO2 instant is:", CO2_raw, "ppm")

            data = {
                "average": CO2_average,
                "instant": CO2_raw,
                "pressure": pressure
            }

            return data

        else:  # if one or both checksums are not corrects
            if attempts == max_attempts:
                logger.error("Error in the data received (wrong checksum), skipping this CO2 and pressure reading")
                return data  # indicate clearly that the data are wrong

            else:
                attempts += 1
                logger.warning("Error in the data received (wrong checksum), reading data again... (" +
                               str(attempts) + "/" + str(max_attempts) + ")")
                time.sleep(3)  # avoid too close i2c communication


def get_data():
    """
    Get all the available data from the CO2 sensor (CO2 instant/average, pressure, temperature, humidity
    :return:    Dictionary containing the following items
                {"pressure", "temperature", "CO2 average", "CO2 instant", "relative humidity"}
    """
    # Read status byte
    # attempts = 1
    # while True:
    #     if status(True):
    #         break
    #     else:
    #         print("Waiting for data to be ready...", end='\r')
    #         time.sleep(2)
    #         attempts += 1
    #     if attempts >= 6:
    #         print("Sensor not ready, trying to read...", end='\r')
    #         break

    # Get CO2 and pressure
    data1 = getCO2P()
    # Get RH and temperature
    data2 = getRHT()
    # Append those two dictionary
    data1.update(data2)
    return data1


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

def internal_timestamp(new_timestamp=None):
    """
    Read the internal sampling period of the CO2 sensor
    To change the value, write it between the brackets (in seconds)
    :param new_timestamp: None or empty to read, new value in seconds to change it
    :return: Actual internal sampling period of the sensor
    """
    if new_timestamp is not None:  # if user write something as input in the brackets (arguments)
        if not 15 <= new_timestamp <= 3600:
            logger.warning("Sampling period should be a number between 15 and 3600 seconds (see sensor documentation)")
        to_write = new_timestamp * 10  # see sensor documentation
        msb_timestamp = (to_write & 0xFF00) >> 8
        lsb_timestamp = (to_write & 0xFF)
        reading = write_to_custom_memory(0x00, msb_timestamp, lsb_timestamp)
    else:  # if user doesn't write anything between the brackets
        reading = read_from_custom_memory(0x00, 2)

    if reading is not False:  # read_from_custom_memory() returns False in case of error...
        # ...Python crash if it tries to make calculations with a boolean (True or False)
        measuring_time_interval = (reading[1] + reading[0] * 256) / 10
        if new_timestamp is None:  # adapt the message in function of the wishes of the user (here he want to read)
            logger.info("Internal measuring time interval is " + str(int(measuring_time_interval)) + " seconds")
        else:  # (here he want to write)
            logger.info(
                "Internal measuring time interval set successfully on " + str(int(measuring_time_interval)) + " seconds")
        return measuring_time_interval
    else:
        logger.error("Failed to change the internal timestamp to " + str(new_timestamp) + " seconds")


def trigger_measurement(force=False):
    """
    Request a new CO2, t°, pressure and RH measurement IF the previous one is older than 10 seconds
    Force to avoid the previous 10 seconds condition
    Same function as 'status()'
    :param: force:  True to apply the function two consecutive times to be sure that the sensor is well
                    synchronized with the seacanairy
                    False to apply it once (during the main loop of the Seacanairy for example)
    :return: True or False if status if OK or NOK
    """
    print("Triggering a new measurement...", end='\r')

    # The sensor will not take a new sample if the previous one is older than 10 seconds
    sensor_status = status(False)  # trigger new measurement

    if force:  # if force is True
        if measurement_delay != 0:  # if user/software want to wait for the data to be ready
            loading_bar("Waiting for sensor sampling", measurement_delay)  # usually 10 seconds (see doc)
            # sensor documentation, let time to the sensor to perform the measurement

            # That way, we ensure that the sensor will trigger a new measurement RIGHT now
            sensor_status = status(False)
            loading_bar("Waiting for sensor sampling", measurement_delay)
            # sensor documentation, let time to the sensor to perform the measurement

    return sensor_status  # same function as 'status()', but here we don't want to print the status on the screen


def read_internal_calibration(item):
    """
    Read the internal calibration of a particular sensor item
    :param item: indicate which internal calibration to read: 'relative humidity', 'temperature', 'pressure', 'CO2', 'all'
    :return: List containing the calibration settings [offset, gain, lower_limit, upper_limit]
    """
    if item == 'relative humidity':
        index = 0x01
        unit = "%RH"
        factor = 1 / 100
    elif item == 'temperature':
        index = 0x02
        unit = "Kelvin"
        factor = 1 / 100
    elif item == 'pressure':
        index = 0x03
        unit = "mbar"
        factor = 1 / 10
    elif item == 'CO2':
        index = 0x04
        unit = "ppm"
        factor = 1
    elif item == "all":
        for i in ['relative humidity', 'temperature', 'pressure', 'CO2']:  # iterate this function for each parameter
            read_internal_calibration(i)
            time.sleep(0.5)  # avoid too close i2c communication
        return  # exit the function once the iteration is finished
    else:
        raise TypeError("Argument of read_internal_calibration is wrong, must be: 'relative humidity', "
                        "'temperature', 'pressure', 'CO2' or 'all'")

    reading = read_from_custom_memory(index, 8)

    if reading is False:  # if read_from_custom_memory() function doesn't work, will return False...
        logger.error("Failed to read the internal calibration of the CO2 sensor")
        return False  # indicate error
    print(reading)
    offset = (reading[0] << 8 + reading[1]) * factor
    gain = (reading[2] << 8 + reading[3]) / 32768
    lower_limit = (reading[4] << 8 + reading[5])  # factor taken into account further
    upper_limit = (reading[6] << 8 + reading[7])  # factor taken into account further

    logger.info("Reading calibration for " + str(item) + ":")
    logger.info("\tOffset: " + str(offset) + " " + str(unit))
    logger.info("\tGain: " + str(gain))
    if lower_limit == 0xFFFF:
        logger.info("\tNo last lower limit adjustment")
        lower_limit = 0
    else:
        lower_limit += factor
        logger.info("\tLower limit: " + str(lower_limit) + " " + str(unit))
    if upper_limit == 0xFFFF:
        logger.info("\tNo last upper minute adjustment")
        upper_limit = 0
    else:
        upper_limit *= factor
        logger.info("\tUpper limit: " + str(upper_limit) + " " + str(unit))
    return [offset, gain, lower_limit, upper_limit]


def read_from_custom_memory(index, number_of_bytes):
    """
    Read bytes from specified custom memory address in the CO2 sensor internal memory
    :param index: index of the data to be read (see sensor doc)
    :param number_of_bytes: number of bytes to read (see sensor doc)
    :return: list[bytes] from right to left
    """
    logger.debug("Reading " + str(number_of_bytes) + " bytes from customer memory at index " + str(hex(index)) + "...")
    write = i2c_msg.write(CO2_address, [0x71, 0x54, index])  # usual bytes to send/write to initiate the reading
    attempts = 1
    read = []  # avoid return issue

    while attempts < 4:
        try:
            with SMBus(1) as bus:
                bus.i2c_rdwr(write)
            read = i2c_msg.read(CO2_address, number_of_bytes)
            with SMBus(1) as bus:
                bus.i2c_rdwr(read)
                break  # break the trial loop if the above has not failed
        except:  # if i2c communication fails
            if attempts >= 3:
                logger.warning("i2c communication failed 3 times while writing to customer memory, skipping reading")
                return False  # indicate that the writing process failed, exit this function
            else:
                logger.error("i2c communication failed to read from customer memory (" + str(attempts) + "/3)")
                attempts += 1
                print("Waiting 3 seconds...", end='\r')
                time.sleep(3)  # avoid too close i2c communication, let time to the sensor, may be busy

    reading = list(read)
    logger.debug("Reading from custom memory returned " + str(reading))
    return reading


def write_to_custom_memory(index, *bytes_to_write):
    """
    Write data to a custom memory address in the CO2 sensor internal memory
    :param index: index of the customer memory to write (see sensor doc)
    :param bytes_to_write: unlimited amount of bytes to write into the internal custom memory at index (see sensor doc)
    :return: True (Success) or False (Fail)
    """
    logger.debug("Writing " + str(bytes_to_write) + " inside custom memory at index " + str(hex(index)) + "...")
    crc8 = digest([index, *bytes_to_write])  # calculation of the CRC8 based on the index number and all the bytes sent
    attempts = 1  # trial counter for writing into the customer memory
    cycle = 1  # trial counter for i2c communication

    try:
        with SMBus(1) as bus:
            write = i2c_msg.write(CO2_address, [0x71, 0x54, index, *bytes_to_write, crc8])  # see sensor doc
            bus.i2c_rdwr(write)
            logger.debug("i2c writing succeeded")
            # i2c writing function worked, and sensor didn't replied a NACK on the SCK line
            # (see i2c working principle/theory)

    except:
        logger.critical("i2c failure while writing to custom memory")
        return False

    # check that the data are written correctly
    time.sleep(0.3)
    reading = read_from_custom_memory(index, len(bytes_to_write))
    if reading == [*bytes_to_write]:  # because reading returns a list
        logger.debug("Success in writing " + str(bytes_to_write) + " inside custom memory at index " + str(index))
        return reading  # indicate that the writing process succeeded

    else:
        logger.error("Failed in writing " + str(bytes_to_write) + " inside custom memory at index " + str(hex(index)))
        logger.debug("Value read is " + str(reading) + " in place of " + str(bytes_to_write))

# ---------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------


# __name__ = '__main__' indicate that the Python sheet has been executed directly
# in opposition with __name__ = '__CO2__' when the Python sheet is executed as a library from another Python sheet

# What is below will be executed if user execute this Python code directly ($ python3 CO2.py)
# Code below is used to make trials to the CO2 sensor while developing

if __name__ == '__main__':
    now = datetime.now()
    logger.info("------------------------------------")  # add a line in the log file
    logger.info("Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S")))

    print("Reading internal timestamp")
    internal_timestamp()
    trigger_measurement(force=True)

    while True:  # unstopped loop
        get_data()
        print("waiting 10 seconds...")
        time.sleep(10)  # wait 10 seconds
