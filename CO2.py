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


# emplacement variable
bus = SMBus(1)


def read(length):
    """
    Easy reading on the CO2 sensor.
    :param length: int, number of bytes to read
    :return: reading
    """
    reading = bus.read_i2c_block_data(CO2_address, length)
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

    return


def CO2_request_measurement():
    """
    Request a new measurement to the sensor if the previous one is older than 10 seconds.

    :return:  1 if status of the sensor is OK
    """

    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    print("Send status execution...")

    status = bus.read_byte_data(CO2_address, 0x71)
    print("Status of CO2 sensor is ", status)

    if(status == 0):
        print("Status is ok")

    return status


def CO2_get_RH_T():
    """
    Read temperature and relative humidity from the CO2 sensor.

    CO2_get_RH_T()[0] = relative humidity

    CO2_get_RH_T()[1] = temperature

    :return:  List of int[Relative Humidity, Temperature]
    """

    write(0xE0, 0x00)
    
    time.sleep(0.5)     # Copy-pasted from the code of Lukas

    reading = read(48)
    # 48 is the length of the string of bytes to read (6 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    print("Raw data from the sensor is: ", reading)

    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    temperature = ( (reading[0] << 8) + reading[1] ) / 100 - 273.15
    relative_humidity = ( ( reading[2] << 8) + reading [3] ) / 100


    print("Temperature is: ", temperature, " °C")

    # relative_humidity = int.from_bytes(RH, 'big') /100      # maybe not useful
    print("Relative humidity is: ", relative_humidity, " %RH")

    RH_T = [relative_humidity, temperature]      # create a chain of values to be returned by the function

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

    time.sleep(0.5) # Copy-pasted from the code of Lukas

    reading = read(72)
    # 72 is the lenght of the string of bytes to read (9 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    print("Raw data from the sensor is: ", reading)

    CO2_average = ( reading[0] << 8) + reading[1]
    print("CO2 average is: ", CO2_average, " ppm")

    #TODO: CRC8 calculation for reading[2]

    CO2_raw = ( reading[3] << 8 ) + reading[4]
    print("CO2 instant is: ", CO2_raw, " ppm")

    #TODO: CRC8 calculation for reading[5]

    # reading << 8 = shift bytes 8 times to the left, equally, add 8 times 0 on the right
    pressure = ( ( ( reading[6]) << 8 ) + reading[7]) / 10
    print("Pressure is: ", pressure, " mbar")

    CO2_P = [CO2_average, CO2_raw, pressure]        # create a chain of values to be returned by the function

    return CO2_P

# ---------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------

while(True):
    CO2_get_RH_T()
    CO2_get_CO2_P()
    print("waiting...")
    time.sleep(20)      # wait 20 seconds
