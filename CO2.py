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
CO2_address: int = 0x33

# emplacement variable
bus = SMBus(1)

# --------------------------------------------------------
# CRC8 CHECKSUM CALCULATION
# --------------------------------------------------------
import crc8

check = crc8.crc8()

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
import logging

if __name__ == "__main__":
    message_level = logging.DEBUG
    # If you run the code from this file directly, it will show all the DEBUG messages

else:
    message_level = logging.INFO
    # If you run this code from another file (using this one as a library), it will only print INFO messages

log_file = './log/CO2.log'

# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=log_file,
                    filemode='a')
# define a Handler which writes INFO messages or higher to the sys.stderr/display
console = logging.StreamHandler()
console.setLevel(message_level)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)

logger = logging.getLogger('CO2 sensor')


# --------------------------------------------------------


def CO2_request_measurement():
    """
    Request a new measurement to the sensor if the previous one is older than 10 seconds.

    :return:  1 if status of the sensor is OK
    """

    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    print('Sending status execution.')

    try:
        status = bus.read_byte_data(CO2_address, 0x71)
        log = "Reading status on the CO2 sensor"
        logger.info(log)

        if (status != 0):
            log = "CO2 sensor status is not ok. Value read is " + str(status)
            logger.info(log)

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

    attempts = 0                # reset trial counter

    while attempts < 3:
        try:
            with SMBus(1) as bus:
                bus.i2c_rdwr(write, read)
            break               # break the loop if the try has not failed at the previous line

        except:
            log = "Error while reading RH and Temperature from CO2 sensor " + str(attempts) + "/3"
            logger.critical(log)
            time.sleep(1)       # if I²C comm fails, wait a little bit before the next reading (this is a general
                                # recommendation concerning I²C comm)
            attempts += 1       # increment of attempts
            pass                # doesn't worth to make further calculations if I²C process fails

    reading = list(read)
    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    temperature = round(((reading[0] << 8) + reading[1]) / 100 - 273.15, 2)
    relative_humidity = ((reading[3] << 8) + reading[4]) / 100

    log = "Temperature from CO2 sensor is: " + str(temperature) + " °C"
    logger.info(log)
    log = "Relative humidity is: " + str(relative_humidity) + " %RH"
    logger.info(log)

    RH_T = [relative_humidity, temperature]  # create a chain of values to be returned by the function

    return RH_T


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

    attempts = 0                # reset trial counter

    while attempts < 3:
        try:
            with SMBus(1) as bus:
                bus.i2c_rdwr(write, read)
            break               # break the loop if the try has not failed at the previous line

        except:
            log = "Error while reading CO2 and Pressure from CO2 sensor via I²C " + str(attempts) + "/3"
            logger.critical(log)
            time.sleep(1)       # if I²C comm fails, wait a little bit before the next reading (this is a general
                                # recommendation concerning I²C comm)
            attempts += 1       # increment of attempts
            pass                # doesn't worth to make further calculations if I²C process fails

    reading = list(read)

    CO2_average = (reading[0] << 8) + reading[1]
    log = "CO2 average is: " + str(CO2_average) + " ppm"
    logger.info(log)

    CO2_raw = (reading[3] << 8) + reading[4]
    log = "CO2 instant is: "+ str(CO2_raw) + " ppm"
    logger.info(log)

    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    pressure = (((reading[6]) << 8) + reading[7]) / 10
    log = "Pressure is: " + str(pressure) + " mbar"
    logger.info(log)

    CO2_P = [CO2_average, CO2_raw, pressure]  # create a chain of values to be returned by the function

    return CO2_P


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

def time_interval(seconds):
    """
    Def measurement timestamp for CO2 sensor
    :param seconds: seconds
    :return: 0 for success, 1 for error
    """
    try:
        t = hex(seconds * 10)

        check.update(0x71)
        check.update(0x54)
        check.update(t)
        checksum = check.hexdigest()
        log = "CRC8 calculation for timestamp change is " + str(checksum)
        logger.debug(log)

        write([0x71, 0x54, 0x00, t, checksum])
        # bus.write_i2c_block_data(CO2_address, 0x71, 0x54, 0x00, t, checksum)
        sleep()
        reading = read(16)
        set = (reading[0] << 8 + reading[1]) / 10
        if int(set) == seconds:
            log = "Measurement timestamp set successfully on " + str(set) + " seconds"
            logger.info(log)
            return 0
        else:
            log = "Failed to set measurement timestamp to " + str(set) + " seconds"
            logger.error(log)
            log = "Timestamp remains on " + str(set)
            logger.error(log)
            return 1

    except:
        log = "Something went wrong with timestamp modification"
        logger.error(log)
        return 1


def write_calibration(calibration, offset, gain, lower_limit, upper_limit):
    """
    Read calibration settings of the sensor
    :param calibration: 'relative humidity', 'temperature', 'pressure', or 'CO2'
    :param offset:
    :param gain:
    :param lower_limit:
    :param upper_limit:
    :return: 0 if success, 1 if fail
    """

    if calibration == 'relative humidity':
        index = 0x01

    if calibration == 'temperature':
        index = 0x02

    if calibration == 'pressure':
        index = 0x03

    if calibration == 'CO2':
        index = 0x04

    else:
        log = "The calibration command " + calibration + " is unknown"
        logger.error(log)
        pass  # don't send calibration information if calibration function is not recognized

    GainValue = gain * 32768

    check.update(hex(index))
    check.update(hex(offset))
    check.update(hex(GainValue))
    check.update(hex(lower_limit))
    check.update(hex(upper_limit))
    checksum = check.hexdigest()

    write([0x71, 0x54, index, GainValue, lower_limit, upper_limit, checksum])
    # bus.write_i2c_block_data(CO2_address, 0x71, 0x54, index, GainValue, lower_limit, upper_limit, checksum)

    # ........... still to do some things (reading, checking...)


# ---------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------
if __name__ == '__main__':
    now = datetime.now()
    logging.info("------------------------------------")
    log = "Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S"))
    logging.info(log)

    while (True):
        getRHT()
        time.sleep(1)
        getCO2P()
        print("waiting...")
        time.sleep(20)  # wait 20 seconds
