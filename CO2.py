# get the time
from datetime import date
from datetime import datetime
import time

# get the locations of the input on the rpi and ADC (imported from Lukas code)
import smbus
import sys
import subprocess

# smbus2 is the new smbus, allow more than 32 bits writing/reading
from smbus2 import SMBus, i2c_msg


# I²C address of the CO2 device
CO2_address: int = 0x33


#emplacement variable
bus = SMBus(1)


def CO2_read(register, length)
    """
    Read data from a certain customer memory address on th CO2 sensor.
    :param repository: int
    :param length: int
    :return: 
    """
    reading = bus.read_i2c_block_data(CO2_address, register, length)
    #TODO: allow the user to skip the register if not needed
    #TODO: convert data read into an integrer (if needed)
    return reading


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

    :return:  List of int[Relative Humidity, Temperature]
    """

    bus.i2c_msg.write(CO2_address, 0xE0, 0x00)
    # write function should automatically  add a 0 at the end, just after the CO2_Address
    # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

    time.sleep(0.5)     # Copy-pasted from the code of Lukas

    reading = bus.i2c_msg.read(CO2_address, 48)
    # 48 is the lenght of the string of bytes to read (6 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    print("Raw data from the sensor is: ", reading)

    # & = AND gate --> 1 & 1 = 1 ; 1 & 0 = 0 ; 0 & 1 = 1 ; 0 & 0 = 0
    RH = (reading & 0xFF0)      # keep the 8 last bytes     see documentation on page 9 of TUG pdf
    T = (reading & 0xFF0000)    # keep the 8 first bytes    see documentation on page 9 of TUG pdf

    # convert bytes to integrer and make calculations       maybe not usefull
    # 'big' means to read from right to left
    temperature = int.from_bytes(T, 'big') /100 - 273.15
    print("Temperature is: ", temperature, " °C")

    relative_humidity = int.from_bytes(RH, 'big') /100      # maybe not usefull
    print("Relative humidity is: ", relative_humidity, " %RH")

    RH_T = [relative_humidity, temperature]      # create a chain of values to be returned by the function
    # CO2_get_RH_T()[0] = relative_humidity
    # CO2_get_RH_T()[1] = temperature

    return RH_T


def CO2_get_CO2_P():
    """
    Read the CO2 and pressure from the CO2 sensor.

    :return: List of int[CO2 (average), CO2 (instant measurement), Atmospheric Pressure)
    """
    print("Reading of CO2 and pressure...")

    bus.i2c_msg.write(CO2_address, 0xE0, 0x27)
    # write function should automatically  add a 0 at the end, just after the CO2_Address
    # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

    time.sleep(0.5) # Copy-pasted from the code of Lukas

    reading = bus.i2c_msg.read(CO2_address, 72)
    # 72 is the lenght of the string of bytes to read (9 x 8)
    # I should maybe add the ACK of the Master in the length
    # read function should add a 1 after the CO2_Address
    # If not, write on address 0x67 (this include the mandatory 0 of the I²C communication)

    print("Raw data from the sensor is: ", reading)

    # & = AND gate --> 1 & 1 = 1 ; 1 & 0 = 0 ; 0 & 1 = 1 ; 0 & 0 = 0
    CO2_average = (reading & 0xFF0000000)           # see documentation on page 10 of TUG pdf
    print("CO2 average is: ", CO2_average, " ppm")

    CO2_raw = (reading & 0xFF0000)                  # see documentation on page 10 of TUG pdf
    print("CO2 instant is: ", CO2_raw, " ppm")

    pressure = (reading & 0xFF0)
    print("Pressure is: ", pressure, " mbar")

    CO2_P = [CO2_average, CO2_raw, pressure]        # create a chain of values to be returned by the function
    # CO2_get_CO2_P()[0] = CO2_average
    # CO2_get_CO2_P()[1] = CO2_raw
    # CO2_get_CO2_P()[2] = pressure

    return CO2_P





#Execute the function above
while(True):
    CO2_get_RH_T()
    CO2_get_CO2_P()
    print("waiting...")
    time.sleep(20)      # wait 20 seconds
