# get the time
from datetime import date
from datetime import datetime
import time

# get the locations of the input on the rpi and ADC
import smbus
import sys
import subprocess

# ports location
from smbus import SMBus

# address of the CO2 device
CO2_address = 0x33


#emplacement variable
bus = SMBus(1)

#copy-pasted from the pdf of Epulse: https://www.epluse.com/en/products/co2-measurement/co2-sensor/ee894/

#constant definitions
TYPE_LO = 0x11          # ControlByte for reading Sensortype Low-Byte
TYPE_SUB = 0x21         # ControlByte for reading Sensor-Subtype
AVAIL_PHYSIC_MES = 0x31 # ControlByte for reading Available physical measurements
TYPE_HI = 0x41          # ControlByte for reading Sensortype High-Byte
REQU_MES = 0x71         # ControlByte for reading Statusbyte
MV_1_LO = 0x81          # ControlByte for reading Measurement value 1 Low-Byte
MV_1_HI = 0x91          # ControlByte for reading Measurement value 1 High-Byte
MV_2_LO = 0xA1          # ControlByte for reading Measurement value 2 Low-Byte
MV_2_HI = 0xB1          # ControlByte for reading Measurement value 2 High-Byte
MV_3_LO = 0xC1          # ControlByte for reading Measurement value 3 Low-Byte
MV_3_HI = 0xD1          # ControlByte for reading Measurement value 3 High-Byte
MV_4_LO = 0xE1          # ControlByte for reading Measurement value 4 Low-Byte
MV_4_HI = 0xF1          # ControlByte for reading Measurement value 4 High-Byte
E2_DEVICE_ADR = 0       # Address of E2-slave-Device
TEMP_RH = 0xE000        # Read the temperature value in 0.01 Kelvin and relative humidity value in 0.01 %
CO2_PRESS = 0xE027      # Read the averaged CO2 value in 1 ppm, the raw CO2 value in 1 ppm and ambient pressure in 0.1 mbar
CUSTOM = 0x7154         # Command for measurement time configuration and customer adjustment

# declaration of functions
# I did a translation of the code of Epulse written in C++.
# But this was too complicated and the lines below are not usefull anymore
#fl_E2bus_Read_SensorType(void) = 0 #read Sensortype from E2-Interface
#fl_E2bus_Read_SensorSubType(void) = abc #read Sensor Subtype from E2-Interface
#fl_E2bus_Read_AvailablePhysicalMeasurements(void) = abc #read available physical Measurements from E2-Interface
#fl_E2bus_Read_RH(void) # Read Measurement Value 1 (relativ Humidity [%RH])
#fl_E2bus_Read_Temp(void) # Read Measurement Value 2 (Temperature [°C])
#fl_E2bus_Read_pres(void) # Read Measurement Value 3 (Ambient pressure [mbar])
#fl_E2bus_Read_CO2_MEAN(void) # Read Measurement Value 4 (CO2 MEAN [ppm])
#unsigned char fl_E2bus_Read_Status(void) #read Statusbyte from E2-Interface



#constants definition
#from the documentation
retrys = 3          # number of read attempts
DELAY_FACTOR = 2    # delay factor for configuration of interface speed


def CO2_request_measurement():
    # Is equal to reading the status
    # The sensor make the measurements, calculations and calibration by itself.
    # In the settings of the sensor, the firmware automatically make measurement every x seconds
    # Sending this STATUS will request a new measurement IF the previous one is older than 10 seconds
    print("********* SEND STATUS ************")

    status = bus.read_byte_data(CO2_address, 0x71)
    print("Status of CO2 sensor is ", status)

    if(status == 0):
        print("Status is ok")
        # SHOULD I ADD A NEW LINE HERE? OR 2 LINES?
    return status


def CO2_get_RH_T():
    print("****** GET TEMPERATURE AND RH ******")

    bus.write_I2C_block_data(CO2_address, 0xE0, 0x00)
    # write function should automatically  add a 0 at the end, just after the CO2_Address
    # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

    time.sleep(0.5)     # Copy-pasted from the code of Lukas

    reading = bus.read_I2C_block_data(CO2_address, 48)
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
    print("****** GET CO2 AND PRESSURE ******")

    bus.write_I2C_block_data(CO2_address, 0xE0, 0x27)
    # write function should automatically  add a 0 at the end, just after the CO2_Address
    # If not, write on address 0x66 (this include the mandatory 1 of the I²C communication)

    time.sleep(0.5) # Copy-pasted from the code of Lukas

    reading = bus.read_I2C_block_data(CO2_address, 72)
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
