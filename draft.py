#---------------------------------------------------------------------
# CO2_data sensor
#---------------------------------------------------------------------

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
CO2_PRESS = 0xE027      # Read the averaged CO2_data value in 1 ppm, the raw CO2_data value in 1 ppm and ambient pressure in 0.1 mbar
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
#fl_E2bus_Read_CO2_MEAN(void) # Read Measurement Value 4 (CO2_data MEAN [ppm])
#unsigned char fl_E2bus_Read_Status(void) #read Statusbyte from E2-Interface

#from the documentation
retrys = 3          # number of read attempts
DELAY_FACTOR = 2    # delay factor for configuration of interface speed


#-------------------------------------------------------------------
# temperature and relative humidity
#-------------------------------------------------------------------


# & = AND gate --> 1 & 1 = 1 ; 1 & 0 = 0 ; 0 & 1 = 1 ; 0 & 0 = 0
 RH = (reading & 0xFF0)      # keep the 8 last bytes     see documentation on page 9 of TUG pdf
 T = (reading & 0xFF0000)    # keep the 8 first bytes    see documentation on page 9 of TUG pdf

# convert bytes to integer and make calculations       maybe not useful
# 'big' means to read from right to left
temperature = int.from_bytes(T, 'big') /100 - 273.15

#-------------------------------------------------------------------
# CO2_data and pressure
#-------------------------------------------------------------------

# & = AND gate --> 1 & 1 = 1 ; 1 & 0 = 0 ; 0 & 1 = 1 ; 0 & 0 = 0
CO2_average = (reading & 0xFF0000000)           # see documentation on page 10 of TUG pdf
CO2_raw = (reading & 0xFF0000)  # see documentation on page 10 of TUG pdf
pressure = (reading & 0xFF0)
relative_humidity = int.from_bytes(RH, 'big') /100      # maybe not useful

#------------------------------------------------------------------
# CRC8
#------------------------------------------------------------------

if crc8 == reading[5]:
 relative_humidity = ((reading[3] << 8) + reading[4]) / 100
 print("Relative humidity is: ", relative_humidity, " %RH")

else:
 logging.warning("CRC8 check found mistake in the data transmission for temperature")

# -----------------------------------------------------------------
# CRC8 for RHT_data
# -----------------------------------------------------------------
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
  log = "CRC8 check found mistake in the I²C transmission for temperature from CO2_data sensor"
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

 # checking for temperature
 check.update(reading[0])
 check.update(reading[1])
 checksum = check.hexdigest()
 log = "CRC8 is: " + str(checksum)
 logger.debug(log)

# ------------------------------------------
# CO2_data ...
# ------------------------------------------

 if checksum == reading[2]:
  log = "CRC8 is correct. CO2_data average transmission is correct"
  logger.debug(log)

 else:
  log = "CRC8 check found mistake in the I²C transmission for CO2_data average"
  logger.warning(log)
  log = "CRC8 from sensor is " + str(reading[2]) + " and CRC8 calculation is " + str(checksum)
  logger.warning(log)

 check.update(reading[3])
 check.update(reading[4])
 checksum = check.hexdigest()
 log = "CRC8 is: " + str(checksum)
 logger.debug(log)

 if checksum == reading[5]:
  log = "CRC8 is correct. CO2_data raw transmission is correct"
  logger.debug(log)

 else:
  log = "CRC8 check found mistake in the I²C transmission for CO2_data raw"
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