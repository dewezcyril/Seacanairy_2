"""
Libraries for the use of E+E Elektronik EE894 CO2 sensor via I²C communication

Execution at the end of the functions written above
"""
# --------------------------------------------------------
# USEFUL VARIABLES
# --------------------------------------------------------

# get the time
import time
from datetime import date, datetime

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg

# I²C address of the CO2 device
CO2_address = 0x33

# emplacement variable
bus = SMBus(1)

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
import logging

if __name__ == "__main__":
    # If you run the code from this file directly, it will show all the DEBUG messages
    message_level = logging.DEBUG
    log_file = '/home/pi/seacanairy_project/log/CO2-debug.log'  # complete location needed on the RPI
    print("CO2 running in DEBUG mode")

else:
    # If you run this code from another file (using this one as a library), it will only print INFO messages
    message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/seacanairy.log'  # complete location needed on the RPI


# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename=log_file,
                    filemode='a')

logger = logging.getLogger('CO2 sensor')

# define a Handler which writes INFO messages or higher to the sys.stderr/display
console = logging.StreamHandler()
console.setLevel(message_level)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)

# --------------------------------------------------------

def digest(buf):
    """
    Digest the data to return the corresponding checksum
    :param buf: List of data to digest
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
    Check that the data transmitted are correct using the data and the checksum
    :param data: List containing the data to be digested (see sensor doc)
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

    :return:  1 if status of the sensor is OK
    """

    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    print('Requesting a new measurement on the CO2 sensor')

    try:
        status = bus.read_byte_data(CO2_address, 0x71)
        logger.debug("Reading status on the CO2 sensor")

        if (status != 0):
            log = "CO2 sensor status is not ok. Value read is " + str(status)
            logger.debug(log)

        return status

    except:
        log = "Error while reading status of CO2 sensor via I²C"
        logger.error(log)
        return 0


def getRHT():
    """
    Read temperature and relative humidity from the CO2 sensor.
        CO2_get_RH_T()[0] = relative humidity
        CO2_get_RH_T()[1] = temperature

    :return:  List of int[Relative Humidity (%RH), Temperature (°C)]
    """
    log = "Reading RH and Temperature from CO2 sensor"
    logger.debug(log)

    write = i2c_msg.write(CO2_address, [0xE0, 0x00])
    read = i2c_msg.read(CO2_address, 6)

    attempts = 0  # reset trial counter
    reading_trials = 0  # reset trial counter

    while attempts < 4:

        while reading_trials < 4:
            try:
                time.sleep(1)  # if transmission fails, wait a bit to try again
                with SMBus(1) as bus:
                    bus.i2c_rdwr(write, read)
                break  # break the loop if the try has not failed at the previous line

            except:
                if reading_trials == 3:
                    log = "RH and temperature lecture from CO2 sensor aborted. (3/3) i2c transmission problem."
                    logger.critical(log)
                    return [-255, -255]  # indicate on the SD card that data are wrong
                reading_trials += 1  # increment of reading_trials
                log = "Error in the i2c transmission. Trying again... (" + str(reading_trials + 1) + ")"
                logger.error(log)

        reading = list(read)
        if check(reading[2], [reading[0], reading[1]]) and check(reading[5], [reading[3], reading[4]]):
            # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
            temperature = round(((reading[0] << 8) + reading[1]) / 100 - 273.15, 2)
            relative_humidity = ((reading[3] << 8) + reading[4]) / 100

            print("Temperature from CO2 sensor is:", temperature, "°C")
            print("Relative humidity from CO2 sensor is:", relative_humidity, "%RH")

            RH_T = [relative_humidity, temperature]  # create a chain of values to be returned by the function

            return RH_T

        else:
            attempts += 1
            if attempts == 3:
                log = "Error in the data received. (3/3) Temperature and humidity reading aborted"
                logger.error(log)
                return [-255, -255]  # indicate on the SD card that data are wrong
            else:
                log = "Error in the data received. Reading data again... (" + str(attempts) + "/3)"
                logger.error(log)
                time.sleep(1)

        if attempts == 3:
            return [-255, -255]  # indicate on the SD card that data are wrong


def getCO2P():
    """
    Read the CO2 and pressure from the CO2 sensor.
        CO2_get_CO2_P()[0] = CO2_average
        CO2_get_CO2_P()[1] = CO2_raw
        CO2_get_CO2_P()[2] = pressure

    :return: List of int[CO2 (average), CO2 (instant measurement), Atmospheric Pressure)
    """
    log = 'Reading of CO2 and pressure'
    logger.debug(log)

    write = i2c_msg.write(CO2_address, [0xE0, 0x27])
    read = i2c_msg.read(CO2_address, 9)

    attempts = 0  # reset trial counter
    reading_trials = 0  # reset trial counter

    while attempts < 4:

        while reading_trials < 4:
            try:
                time.sleep(1)  # if I²C comm fails, wait a little bit before the next reading (this is a general
                # recommendation concerning I²C comm)
                with SMBus(1) as bus:
                    bus.i2c_rdwr(write, read)
                break  # break the loop if the try has not failed at the previous line

            except:
                if reading_trials == 3:
                    log = "RH and temperature lecture from CO2 sensor aborted. i2c transmission problem."
                    logger.critical(log)
                    return [-255, -255, -255]  # indicate that the data are wrong
                log = "Error in the i2c transmission. Trying again... (" + str(reading_trials + 1) + "/3)"
                logger.error(log)
                reading_trials += 1  # increment of reading_trials

        reading = list(read)
        if check(reading[2], [reading[0], reading[1]]) and check(reading[5], [reading[3], reading[4]]) and check(
                reading[8], [reading[6], reading[7]]):
            CO2_average = (reading[0] << 8) + reading[1]  # reading << 8 = shift bytes 8 times to the left
            print("CO2 average is:", CO2_average, "ppm")

            CO2_raw = (reading[3] << 8) + reading[4]
            print("CO2 instant is:", CO2_raw, "ppm")

            pressure = (((reading[6]) << 8) + reading[7]) / 10  # reading << 8 = shift bytes 8 times to the left
            print("Pressure is:", pressure, "mbar")

            CO2_P = [CO2_average, CO2_raw, pressure]  # create a chain of values to be returned by the function

            return CO2_P

        else:
            attempts += 1
            if attempts == 3:
                log = "Error in the data received. CO2 and pressure reading aborted"
                logger.error(log)
                return [-255, -255, -255]  # indicate that the data are wrong
            else:
                log = "Error in the data received. Reading data again... (" + str(attempts) + "/3)"
                logger.error(log)


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

def internal_timestamp(new_timestamp=None):
    """
    Read/write the internal sampling timestamp of the CO2 sensor
    :param new_timestamp: to change the timestamp, let empty to read tge timestamp
    :return: internal sampling timestamp
    """
    if new_timestamp is not None:
        if not 15 <= new_timestamp <= 3600:
            raise TypeError("Sampling timestamp must be a number between 15 and 3600 seconds")
        to_write = new_timestamp * 10
        msb_timestamp = (to_write & 0xFF00) >> 8
        lsb_timestamp = (to_write & 0xFF)
        reading = write_to_custom_memory(0x00, msb_timestamp, lsb_timestamp)
    else:
        reading = read_from_custom_memory(0x00, 2)

    if reading is not False:  # avoid to make calculation with a False value from above, which generate an error
        measuring_time_interval = (reading[1] + reading[0] * 256) / 10
        if new_timestamp is None:
            logger.info("Internal measuring time interval is " + str(measuring_time_interval) + " seconds")
        else:
            logger.info("Internal measuring time interval set successfully on " + str(measuring_time_interval) + " seconds")
        return measuring_time_interval


def read_internal_calibration(item):
    if item == 'relative humidity':
        index = 0x01
        unit = "%RH"
        factor = 1/100
    elif item == 'temperature':
        index = 0x02
        unit = "Kelvin"
        factor = 1/100
    elif item == 'pressure':
        index = 0x03
        unit = "mbar"
        factor = 1/10
    elif item == 'CO2':
        index = 0x04
        unit = "ppm"
        factor = 1
    elif item == "all":
        for i in ['relative humidity', 'temperature', 'pressure', 'CO2']:
            read_internal_calibration(i)
            time.sleep(0.5)
        return
    else:
        raise TypeError("Argument of read_internal_calibration is wrong, must be: 'relative humidity', "
                        "'temperature', 'pressure', 'CO2' or 'all'")

    reading = read_from_custom_memory(index, 8)

    if reading is False:
        return  # avoid make any calculation below with a value which is False, would make an error
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
    :param index: index of the data to be read
    :param number_of_bytes: number of bytes to read
    :return: list[bytes] from right to left
    """
    logger.debug("Reading " + str(number_of_bytes) + " bytes from customer memory at index " + str(hex(index)) + "...")
    write = i2c_msg.write(CO2_address, [0x71, 0x54, index])
    attempts = 1
    while attempts < 4:
        try:
            with SMBus(1) as bus:
                bus.i2c_rdwr(write)
            read = i2c_msg.read(CO2_address, number_of_bytes)
            with SMBus(1) as bus:
                bus.i2c_rdwr(read)
                break  # break the trial loop
        except:
            if attempts >= 3:
                logger.error("i2c communication failed 3 times while writing to customer memory, skipping reading")
                return False  # indicate that the writing process failed, exit this function
            else:
                logger.error("i2c communication failed to read from customer memory (" + str(attempts) + "/3)")
                attempts += 1
                time.sleep(1)
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
    logger.debug("Writing " + str(bytes_to_write) + " inside custom memory at index "+ str(hex(index)) + "...")
    crc8 = digest([index, *bytes_to_write])  # calculation of the CRC8 based on the index number and all the bytes sent
    attempts = 1  # for writing into memory
    cycle = 1  # for i2c communication

    while cycle < 4 and attempts < 4:
        try:
            with SMBus(1) as bus:
                write = i2c_msg.write(CO2_address, [0x71, 0x54, index, *bytes_to_write, crc8])
                bus.i2c_rdwr(write)
                logger.debug("i2c writing succeeded")

        except:
            if attempts >= 3:
                logger.error("i2c communication failed 3 times while writing to customer memory, skipping writing")
                return False  # indicate that the writing process failed, exit this function
            else:
                logger.error("i2c communication failed to write into customer memory (" + str(cycle) + "/3)")
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
            logger.error("Failed in writing " + str(bytes_to_write) + " inside custom memory at index " + str(hex(index))
                         + " (" + str(attempts) + "/3), trying again")
            logger.debug("Value read is " + str(reading) + " in place of " + str(bytes_to_write))
            time.sleep(0.5)
            attempts += 1


# ---------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------
if __name__ == '__main__':
    now = datetime.now()
    logger.info("------------------------------------")
    log = "Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S"))
    logger.info(log)

    # while (True):
    #     getRHT()
    #     time.sleep(1)
    #     getCO2P()
    #     print("waiting...")
    #     time.sleep(10)  # wait 20 seconds

    read_internal_calibration('all')
    internal_timestamp(60)
