#! /home/pi/seacanairy_project/venv/bin/python3
"""
Libraries for the use of E+E Elektronik EE894 CO2 sensor via I²C communication
"""
# --------------------------------------------------------
# USEFUL VARIABLES
# --------------------------------------------------------

# get the time
import time
from datetime import date, datetime

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg

# logging
import logging

# yaml settings
import yaml

# 'SMBus' is the general driver for i2c communication
# 'i2c_msg' allow to make i2c write followed by i2c read WITHOUT any STOP byte (see sensor documentation)

# I²C address of the CO2 device
CO2_address = 0x33  # i2c address by default, can be changed (see sensor doc)

# emplacement variable
bus = SMBus(1)  # make it easier to read/write to the sensor (bus.read or bus.write...)

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------

with open('/home/pi/seacanairy_project/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

store_debug_messages = settings['CO2 sensor']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

measurement_delay = settings['CO2 sensor']['Amount of time required for the sensor to take the measurement']

max_attempts = settings['CO2 sensor']['Number of reading attempts']

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
# all the settings and other code for the logging
# logging = tak a trace of some messages in a file to be reviewed afterward (check for errors fe)

if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    log_file = '/home/pi/seacanairy_project/log/CO2-debug.log'  # complete file location required for the Raspberry
    print("DEBUG messages will be shown and stored in '" + str(log_file) + "'")

    # The following HANDLER must be activated ONLY if you run this code alone
    # Without the 'if __name__ == '__main__' condition, all the logging messages are displayed 3 TIMES
    # (once for the handler in CO2.py, once for the handler in OPCN3.py, and once for the handler in seacanairy.py)

    # define a Handler which writes INFO messages or higher to the sys.stderr/display
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

else:  # if this file is considered as a library (if you execute seacanairy.py for example)
    # it will only print and store INFO messages in the corresponding log_file
    if store_debug_messages:
        message_level = logging.DEBUG
    else:
        message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/' + project_name + '.log'  # complete location needed on the RPI

    # no need to add a handler, because there is already one in seacanairy.py

# set up logging to file
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m %H:%M:%S',
                    filename=log_file,
                    filemode='a')

logger = logging.getLogger('CO2 sensor')  # name of the logger


# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as ROOT and NOT 'CO2 sensor'

# --------------------------------------------------------


def digest(buf):
    """
    Calculate the CRC8 checksum (based on the CO2 documentation example)
    :param buf: List[bytes to digest]
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
    :param data: List[bytes to be used in the checksum calculation (see sensor doc)]
    :param checksum: Checksum given by the sensor
    :return:
    """
    calculation = digest(data)
    if calculation == checksum:
        logger.debug("CRC8 is correct, data are valid")
        return True
    else:
        logger.debug("CRC8 does not fit, data are wrong")
        return False


def request_measurement():
    """
    Request a new measurement to the sensor if the previous one is older than 10 seconds.
    Reset the internal counter (after the execution of this function, the sensor will wait for the amount of time
    defined as the internal timestamp before taking the next measurement)
    :return:  status given by the sensor
    """

    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    print('Requesting a new measurement on the CO2 sensor')

    try:
        status = bus.read_byte_data(CO2_address, 0x71)
        logger.debug("Reading status on the CO2 sensor")

        if (status != 0):
            logger.debug("CO2 sensor status is not ok. Value read is " + str(status))

        return status

    except:
        logger.error("I²C error while reading status of CO2 sensor")
        return 255  # indicate that all the bytes are 1 (0b11111111)


def getRHT():
    """
    Read temperature and relative humidity from the CO2 sensor.
        CO2_get_RH_T()[0] = relative humidity
        CO2_get_RH_T()[1] = temperature

    :return:  Dictionary("RH", "temperature")
    """
    logger.debug("Reading RH and Temperature from CO2 sensor")

    write = i2c_msg.write(CO2_address, [0xE0, 0x00])  # see documentation, example for reading t° and RH
    read = i2c_msg.read(CO2_address, 6)

    attempts = 0  # trial counter for the checksum and the validity of the data received
    reading_trials = 0  # trial counter for the i2c communication

    # In case there is a problem and it return nothing, return "error", which can be understood as an error
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
                    log = "RH and temperature lecture from CO2 sensor aborted. (" + str(max_attempts) + "/" + str(max_attempts) + ") i2c transmission problem."
                    logger.critical(log)
                    return data  # indicate clearly that data are wrong

                log = "Error in the i2c transmission, trying again... (" + str(reading_trials + 1) + "/" + str(max_attempts) + ")"
                logger.error(log)
                reading_trials += 1  # increment of reading_trials
                time.sleep(2)  # if transmission fails, wait a bit to try again (sensor is maybe busy)

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
                logger.error("Error in the data received (3/3), temperature and humidity reading skipped")
                return data  # indicate on the SD card that data are wrong

            else:
                attempts += 1
                logger.warning("Error in the data received, trying again... (" + str(attempts) + "/3)")
                time.sleep(1)  # avoid to close i2c communication


def getCO2P():
    """
    Read the CO2 and pressure from the CO2 sensor.
        CO2_get_CO2_P()[0] = CO2_average
        CO2_get_CO2_P()[1] = CO2_raw
        CO2_get_CO2_P()[2] = pressure

    :return: Dictionary["average", "instant", "pressure")
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
                    logger.critical("RH and temperature lecture from CO2 sensor aborted. i2c transmission problem.")
                    return data  # indicate clearly that the data are wrong

                logger.error("Error in the i2c transmission, trying again... (" + str(reading_trials + 1) + "/3)")
                reading_trials += 1  # increment of reading_trials
                time.sleep(1)  # if I²C comm fails, wait a little bit and try again (sensor is maybe busy)

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
            print("\t\t| CO2 instant is:", CO2_raw, "ppm")

            data = {
                "average": CO2_average,
                "instant": CO2_raw,
                "pressure": pressure
            }

            return data

        else:  # if one or both checksums are not corrects
            if attempts == max_attempts:
                logger.error("Error in the data received. CO2 and pressure reading aborted")
                return data  # indicate clearly that the data are wrong

            else:
                attempts += 1
                logger.warning("Error in the data received. Reading data again... (" + str(attempts) + "/3)")
                time.sleep(1)  # avoid too close i2c communication


def get_data():
    """
    Read all the data from the CO2 sensor
    :return: Dictionary("pressure", "temperature", "CO2 average", "CO2 instant")
    """
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
    :param new_timestamp: None to read, new value in seconds to change it
    :return: internal sampling period of the sensor
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
        logger.error("Failed in changing internal timestamp to " + str(new_timestamp) + " seconds")


def status(print_information=True):
    """
    Read the status byte of the CO2 sensor
    !! Will trigger a new measurement if the previous one is older than 10 seconds
    :param: print_information: Optional: False to hide the messages
    :return: List[CO2 status, temperature status, humidity status]
    """
    with SMBus(1) as bus:
        reading = bus.read_byte_data(CO2_address, 0x71)
    # see documentation for the following decryption
    CO2_status = reading & 0b00001000
    temperature_status = reading & 0b00000010
    humidity_status = reading & 0b00000001
    if print_information:  # if user/software indicate to print the information
        if CO2_status == 0:
            logger.info("CO2 measurement is OK")
        else:
            logger.warning("CO2 measurement is NOK")
        if temperature_status == 0:
            logger.info("Temperature measurement is OK")
        else:
            logger.warning("Temperature measurement is NOK")
        if humidity_status == 0:
            logger.info("Humidity measurement is OK")
        else:
            logger.warning("Humidity measurement is NOK")
    return [CO2_status, temperature_status, humidity_status]


def trigger_measurement(let_time_to_sensor_to_measure=True):
    """
    Ask the CO2 sensor to start a new measurement now if the previous one is older than 10 seconds
    Same function as 'status()'
    :param: wait_for_available_measurement: True to let time to the sensor to take the measurement
    :return: Status of the sensor: List[CO2 status, temperature status, humidity status]
    """
    logger.info("Triggering a new measurement...")
    sensor_status = status(False)
    if let_time_to_sensor_to_measure:  # if user/software want to wait for the data to be ready
        logger.info("Waiting " + str(measurement_delay) + " seconds for sensor to take measurement")
        time.sleep(measurement_delay)  # sensor documentation, let time to the sensor to perform the measurement
    return sensor_status  # same function as 'status()', but here we don't want to print the status on the screen


def read_internal_calibration(item):
    """
    Read the internal calibration of the sensor
    :param item: 'relative humidity', 'temperature', 'pressure', 'CO2', 'all'
    :return: List[offset, gain, lower_limit, upper_limit]
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
    Read data from custom memory address in the CO2 sensor
    :param index: index of the data to be read (see sensor doc)
    :param number_of_bytes: number of bytes to read (see sensor doc)
    :return: list[bytes] from right to left
    """
    logger.debug("Reading " + str(number_of_bytes) + " bytes from customer memory at index " + str(hex(index)) + "...")
    write = i2c_msg.write(CO2_address, [0x71, 0x54, index])  # usual bytes to send/write to initiate the reading
    attempts = 1

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
                time.sleep(2)  # avoid too close i2c communication, let time to the sensor, may be busy

    reading = list(read)
    logger.debug("Reading from custom memory returned " + str(reading))
    return reading


def write_to_custom_memory(index, *bytes_to_write):
    """
    Write data to a custom memory address in the CO2 sensor
    :param index: index of the customer memory to write
    :param bytes_to_write: infinite number of data to write at that place
    :return: True (Success) or False (Fail)
    """
    logger.debug("Writing " + str(bytes_to_write) + " inside custom memory at index " + str(hex(index)) + "...")
    crc8 = digest([index, *bytes_to_write])  # calculation of the CRC8 based on the index number and all the bytes sent
    attempts = 1  # trial counter for writing into the customer memory
    cycle = 1  # trial counter for i2c communication

    while cycle < 4 and attempts < 4:
        try:
            with SMBus(1) as bus:
                write = i2c_msg.write(CO2_address, [0x71, 0x54, index, *bytes_to_write, crc8])  # see sensor doc
                bus.i2c_rdwr(write)
                logger.debug("i2c writing succeeded")
                # i2c writing function worked, and sensor didn't replied a NACK on the SCK line
                # (see i2c working principle/theory)

        except:
            if attempts >= 3:
                logger.error("i2c communication failed 3 times while writing to customer memory, skipping writing")
                return False  # indicate that the writing process failed, exit this function
            else:
                logger.warning("i2c communication failed to write into customer memory (" + str(cycle) + "/3)")
                cycle += 1
                time.sleep(1)

        # check that the data are written correctly
        time.sleep(0.3)
        reading = read_from_custom_memory(index, len(bytes_to_write))
        cycle = 1  # reset the attempts counter, let the chance of the sensor to fail 3 i2c communication...
        # ...each time it fails the writing process
        if reading == [*bytes_to_write]:  # because reading returns a list
            logger.debug("Success in writing " + str(bytes_to_write) + " inside custom memory at index " + str(index))
            return reading  # indicate that the writing process succeeded
        if attempts >= 3:
            logger.critical("Failed 3 consecutive times to write " + str(bytes_to_write) +
                            " into customer memory at index " + str(hex(index)))
            return False  # indicate that the writing process failed
        else:
            logger.error(
                "Failed in writing " + str(bytes_to_write) + " inside custom memory at index " + str(hex(index))
                + " (" + str(attempts) + "/3), trying again")
            logger.debug("Value read is " + str(reading) + " in place of " + str(bytes_to_write))
            time.sleep(2)  # avoid too close i2c communication
            attempts += 1


# ---------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------


# __name__ = '__main__' indicate that the Python sheet has been executed directly
# in opposition with __name__ = '__CO2__' when the Python sheet is executed as a library from another Python sheet

# What is below will be executed if user execute this Python code directly ($ python3 CO2.py)
# Code below is used to make trials to the CO2 sensor while developping

if __name__ == '__main__':
    now = datetime.now()
    logger.info("------------------------------------")  # add a line in the log file
    logger.info("Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S")))

    print("Reading internal timestamp")
    internal_timestamp()

    while True:  # unstopped loop
        getRHT()
        time.sleep(1)
        getCO2P()
        print("waiting...")
        time.sleep(10)  # wait 10 seconds
