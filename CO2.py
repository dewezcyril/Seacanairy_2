"""
Libraries for the use of E+E Elektronik EE894 CO2 sensor

Execution at the end of the functions written above
"""

# get the time
from datetime import date
from datetime import datetime
import time

# get the locations of the input on the rpi and ADC (imported from Lukas code)
# import smbus
# import sys
# import subprocess

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg

# I²C address of the CO2 device
CO2_address: int = 0x33

#attempt
i = 0

# emplacement variable
bus = SMBus(1)

#CRC8 checksum calculation
import crc8
check = crc8.crc8()

# logging
import logging
log_file = './log/CO2.log'
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

def sleep():
    time.sleep(0.5)


def read(length):
    """
    Easy reading on the CO2 sensor.
    :param length: int, number of bytes to read
    :return: reading
    """
    reading = bus.read_i2c_block_data(CO2_address, length)
    logging.debug("I²C reading is: ", reading)
    # TODO: check that this is the good function. Wiring needed.
    # TODO: convert data read into an integer (if needed)

    return reading


def write(data1, data2):
    """
    Write two data only to the CO2 sensor.
    :param data1: hexadecimal
    :param data2: hexadecimal
    """

    bus.write_i2c_block_data(CO2_address, data1, data2)
    sleep()

    return


def CO2_request_measurement():
    """
    Request a new measurement to the sensor if the previous one is older than 10 seconds.

    :return:  1 if status of the sensor is OK
    """

    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    logging.debug("Send status execution...")

    status = bus.read_byte_data(CO2_address, 0x71)
    logging.debug("Status of CO2 sensor is ", status)

    if (status != 0):
        logging.warning("CO2 sensor status is not ok")

    return status


def CO2_get_RH_T():
    """
    Read temperature and relative humidity from the CO2 sensor.

    CO2_get_RH_T()[0] = relative humidity

    CO2_get_RH_T()[1] = temperature

    :return:  List of int[Relative Humidity, Temperature]
    """

    write(0xE0, 0x00)

    sleep()  # Copy-pasted from the code of Lukas

    reading = read(48)
    # 48 is the length of the string of bytes to read (6 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    logging.debug("I²C reading for temperature and RH measurement is: ", reading)

    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    temperature = ( (reading[0] << 8) + reading[1] ) / 100 - 273.15
    relative_humidity = ( ( reading[2] << 8) + reading [3] ) / 100

    print("Temperature from CO2 sensor is: ", temperature, " °C")
    print("Relative humidity is: ", relative_humidity, " %RH")

    RH_T = [relative_humidity, temperature]  # create a chain of values to be returned by the function

    # checking for temperature
    check.update(reading[0])
    check.update(reading[1])
    crc8 = check.hexdigest()
    logging.debug("CRC8 is: ", crc8)

    if crc8 == reading[2]:
        logging.debug("CRC8 is correct. Temperature transmission is correct")

    else:
        logging.warning("CRC8 check found mistake in the I²C transmission for temperature from CO2 sensor")
        logging.warning("CRC8 from sensor is ", crc8, " and CRC8 calculation is ", reading[5])

    check.update(reading[3])
    check.update(reading[4])
    crc8 = check.hexdigest()

    if crc8 == reading[5]:
        logging.debug("CRC8 is correct. Relative humidity transmission is correct")

    else:
        logging.warning("CRC8 check found mistake in the I²C transmission for relative humidity")
        logging.warning("CRC8 from sensor is ", crc8, " and CRC8 calculation is ", reading[5])


    return RH_T


def CO2_get_CO2_P():
    """
    Read the CO2 and pressure from the CO2 sensor.

    CO2_get_CO2_P()[0] = CO2_average

    CO2_get_CO2_P()[1] = CO2_raw

    CO2_get_CO2_P()[2] = pressure

    :return: List of int[CO2 (average), CO2 (instant measurement), Atmospheric Pressure)
    """
    print("Reading of CO2 and pressure...")

    write(0xE0, 0x27)
    # write function should automatically  add a 0 at the end, just after the CO2_Address
    # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

    sleep()  # Copy-pasted from the code of Lukas

    reading = read(72)
    # 72 is the lenght of the string of bytes to read (9 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    print("Raw data from the sensor is: ", reading)

    CO2_average = (reading[0] << 8) + reading[1]
    print("CO2 average is: ", CO2_average, " ppm")

    # TODO: CRC8 calculation for reading[2]

    CO2_raw = (reading[3] << 8) + reading[4]
    print("CO2 instant is: ", CO2_raw, " ppm")

    # TODO: CRC8 calculation for reading[5]

    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    pressure = (((reading[6]) << 8) + reading[7]) / 10
    print("Pressure is: ", pressure, " mbar")

    CO2_P = [CO2_average, CO2_raw, pressure]  # create a chain of values to be returned by the function

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
    t = bytes(sec * 10)
    # TODO: CRC8 calculation, unless we're happy with 20 seconds
    CRC8 = 0xB5
    bus.write_i2c_block_data(CO2_address, 0x71, 0x54, 0x00, t, CRC8)
    sleep()
    reading = read(16)
    if reading == t:
        print("Measurement timestamp set successfully on ", sec, " seconds")
        return 0
    else:
        print("Failed to set measurement timestamp to ", sec, " seconds")
        return 1


def write_calibration(calibration,  offset, gain, lower_limit, upper_limit):
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
        print("Calibration command unknown")

    GainValue = gain * 32768

    check.update(hex(index))
    check.update(hex(offset))
    check.update(hex(GainValue))
    check.update(hex(lower_limit))
    check.update(hex(upper_limit))
    crc8 = check.hexdigest()

    bus.write_i2c_block_data(CO2_address, 0x71, 0x54, index, GainValue, LL, UL, crc8)

# ---------------------------------------------------------------------
# Test Execution
# ---------------------------------------------------------------------

while (True):
    CO2_get_RH_T()
    CO2_get_CO2_P()
    print("waiting...")
    time.sleep(20)  # wait 20 seconds
