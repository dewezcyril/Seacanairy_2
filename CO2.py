"""
Libraries for the use of E+E Elektronik EE894 CO2 sensor via I²C communication

Execution at the end of the functions written above
"""
# --------------------------------------------------------
# USEFUL VARIABLES
# --------------------------------------------------------

# get the time
import time
from datetime import date

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg

# I²C address of the CO2 device
CO2_address: int = 0x33

# attempt
i = 0

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

log_file = './log/CO2.log'

# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=log_file,
                    filemode='a')
# define a Handler which writes INFO messages or higher to the sys.stderr/display
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)

logger = logging.getLogger('CO2 sensor')


# --------------------------------------------------------

def sleep():
    time.sleep(0.5)


def read(length):
    """
    Easy reading on the CO2 sensor.
    :param length: int, number of bytes to read
    :return: reading
    """
    log = 'I²C reading process from CO2 sensor'
    logger.debug(log)
    try:
        # msg = i2c_msg.read(CO2_address, length)
        # bus.i2c_rdwr(msg)
        # reading = msg
        # It seems that the function return the reading in the same function as the one between brackets (msg)
        reading = bus.read_i2c_block_data(CO2_address, length)
        log = "I²C reading is: " + str(reading)
        logger.debug(log)

    except:
        log = "Error while reading data from CO2 sensor on I²C"
        logger.error(log)
        return 0

    return reading


def write(data):
    """
    Write two data only to the CO2 sensor.
    :param data: list of bytes to write
    """
    try:
        log = "I²C writing process to CO2 sensor"
        logger.debug(log)
        msg = i2c_msg.write(CO2_address, data)
        bus.i2c_rdwr(msg)
        # bus.write_i2c_block_data(CO2_address, data[0], data[1])
        sleep()

    except:
        log = "Error while writing " + str(data) + " via I²C to the CO2 sensor"
        logger.error(log)

    return


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


def CO2_get_RH_T():
    """
    Read temperature and relative humidity from the CO2 sensor.

    CO2_get_RH_T()[0] = relative humidity

    CO2_get_RH_T()[1] = temperature

    :return:  List of int[Relative Humidity, Temperature]
    """
    log = "Read RH and Temperature from CO2 sensor"
    logger.debug(log)

    try:
        write([0xE0, 0x00])

        sleep()  # Copy-pasted from the code of Lukas

        reading = read(6)
        # 6 bytes to read
        # I should maybe add the ACK of the Master in the length
        # read function should add a 1 after the CO2_Address
        # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

        # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
        temperature = ((reading[0] << 8) + reading[1]) / 100 - 273.15
        relative_humidity = ((reading[2] << 8) + reading[3]) / 100

        log = "Temperature from CO2 sensor is: " + str(temperature) + " °C"
        logger.info(log)
        log = "Relative humidity is: " + str(relative_humidity) + " %RH"
        logger.info(log)

        RH_T = [relative_humidity, temperature]  # create a chain of values to be returned by the function

        # checking for temperature
        check.update(reading[0])
        check.update(reading[1])
        checksum = check.hexdigest()
        log = "CRC8 is: " + str(checksum)
        logger.debug(log)

        if checksum == reading[2]:
            log = "CRC8 is correct. Temperature transmission is correct"
            logger.debug(log)

        else:
            log = "CRC8 check found mistake in the I²C transmission for temperature from CO2 sensor"
            logger.warning(log)
            log = "CRC8 from sensor is " + str(reading[2]) + " and CRC8 calculation is " + str(crc8)
            logger.warning(log)

        check.update(reading[3])
        check.update(reading[4])
        checksum = check.hexdigest()
        log = "CRC8 is: " + str(checksum)
        logger.debug(log)

        if checksum == reading[5]:
            log = "CRC8 is correct. Relative humidity transmission is correct"
            logger.debug(log)

        else:
            log = "CRC8 check found mistake in the I²C transmission for relative humidity"
            logger.warning(log)
            log = "CRC8 from sensor is " + str(reading[5]) + " and CRC8 calculation is " + str(checksum)
            logger.warning(log)

        return RH_T

    except:
        log = "Error while reading RH and Temperature from the CO2 sensor"
        logger.error(log)


def CO2_get_CO2_P():
    """
    Read the CO2 and pressure from the CO2 sensor.

    CO2_get_CO2_P()[0] = CO2_average

    CO2_get_CO2_P()[1] = CO2_raw

    CO2_get_CO2_P()[2] = pressure

    :return: List of int[CO2 (average), CO2 (instant measurement), Atmospheric Pressure)
    """
    log = "Reading of CO2 and pressure"
    print(log)

    try:

        write([0xE0, 0x27])
        # write function should automatically  add a 0 at the end, just after the CO2_Address
        # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

        sleep()  # Copy-pasted from the code of Lukas

        reading = read(72)
        # 72 is the lenght of the string of bytes to read (9 x 8)
        # I should maybe add the ACK of the Master in the length
        # read function should add a 1 after the CO2_Address
        # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

        CO2_average = (reading[0] << 8) + reading[1]
        logger.info("CO2 average is: ", CO2_average, " ppm")

        CO2_raw = (reading[3] << 8) + reading[4]
        logger.info("CO2 instant is: ", CO2_raw, " ppm")

        # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
        pressure = (((reading[6]) << 8) + reading[7]) / 10
        logger.info("Pressure is: ", pressure, " mbar")

        CO2_P = [CO2_average, CO2_raw, pressure]  # create a chain of values to be returned by the function

        # checking for temperature
        check.update(reading[0])
        check.update(reading[1])
        checksum = check.hexdigest()
        log = "CRC8 is: " + str(checksum)
        logger.debug(log)

        if checksum == reading[2]:
            log = "CRC8 is correct. CO2 average transmission is correct"
            logger.debug(log)

        else:
            log = "CRC8 check found mistake in the I²C transmission for CO2 average"
            logger.warning(log)
            log = "CRC8 from sensor is " + str(reading[2]) + " and CRC8 calculation is " + str(checksum)
            logger.warning(log)

        check.update(reading[3])
        check.update(reading[4])
        checksum = check.hexdigest()
        log = "CRC8 is: " + str(checksum)
        logger.debug(log)

        if checksum == reading[5]:
            log = "CRC8 is correct. CO2 raw transmission is correct"
            logger.debug(log)

        else:
            log = "CRC8 check found mistake in the I²C transmission for CO2 raw"
            logger.warning(log)
            log = "CRC8 from sensor is " + str(reading[5]) + "  and CRC8 calculation is " + str(checksum)
            logger.warning(log)

            check.update(reading[6])
            check.update(reading[7])
            checksum = check.hexdigest()

            if checksum == reading[8]:
                log = "CRC8 is correct. Pressure transmission is correct"
                logger.debug(log)

            else:
                log = "CRC8 check found mistake in the I²C transmission for Pressure"
                logger.warning(log)
                log = "CRC8 from sensor is " + str(reading[8]) + " and CRC8 calculation is " + str(checksum)
                logger.warning(log)

    except:
        log = "Error while reading CO2 and Pressure"
        logger.error(log)
        CO2_P = [0, 0]

    return CO2_P


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

def time_interval(sec):
    """
    Def measurement timestamp for CO2 sensor
    :param timestamp: seconds
    :return: 0 for success, 1 for error
    """
    try:
        t = hex(sec * 10)

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
        if int(set) == sec:
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

now = datetime.now()
logging.info("------------------------------------")
log = "Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S"))
logging.info(log)

while (True):
    CO2_get_RH_T()
    CO2_get_CO2_P()
    print("waiting...")
    time.sleep(20)  # wait 20 seconds
