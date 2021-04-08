#! /home/pi/seacanairy_project/venv/bin/python3
"""
Main Seacanairy Python Code that execute all the necessary functions to make the system work and take sample
at required intervals
"""

# import libraries
import CO2  # Library for the CO2 sensor
import OPCN3  # Library for the OPC-N3 sensor
import GPS  # Library for the GPS
import time
from datetime import date, datetime, timedelta
import csv  # for storing data in file
from progress.bar import IncrementalBar
import os.path
import yaml
import logging
# import SPI_test as SPI

# ---------------------------------------
# SETTINGS
# ---------------------------------------
with open('/home/pi/seacanairy_project/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

# Sampling period
sampling_period = settings['Seacanairy settings']['Sampling period']

# CO2 sampling period (CO2 sensor takes samples automatically)
CO2_sampling_period = int(sampling_period / settings['CO2 sensor']['Automatic sampling frequency ' \
                                                                   '(number of sample during the above sampling period)'])

CO2_read_data_delay = settings['CO2 sensor']['Amount of time required for the sensor to take the measurement']

project_name = settings['Seacanairy settings']['Sampling session name']

OPC_flushing_time = settings['OPC-N3 sensor']['Flushing time']

OPC_sampling_time = settings['OPC-N3 sensor']['Sampling time']

OPC_fan_speed = settings['OPC-N3 sensor']['Fan speed']

path_csv = project_name + ".csv"

# -----------------------------------------
# logging
# -----------------------------------------

log_file = "/home/pi/seacanairy_project/log/" + project_name + ".log"

message_level = logging.INFO

# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m %H:%M:%S',
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

logger = logging.getLogger('SEACANAIRY')


# -----------------------------------------
# FUNCTIONS
# -----------------------------------------

def append_data_to_csv(*data_to_write):
    """
    Store all the measurements in the .csv file
    :param data_to_write: List
    :return:
    """
    # Concatenate all the arguments in one list
    to_write = [*data_to_write]

    # Iterate for every argument in the brackets
    # for arg in data_to_write:
    #     to_write.append(arg)
    with open(path_csv, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(to_write)
    csv_file.close()  # close file after use(general safety practice)


def wait_timestamp(starting_time):
    """
    Wait that the sampling period is passed out to start the next measurement
    :param starting_time: time at which the measurement has started ('time.time()' required)
    :param finishing_time: time at which the measurement has finished ('time.time()' required)
    :return: Function stop when next measurement can start
    """
    finishing_time = time.time()
    next_launching = starting_time + sampling_period  # time at which the next sample should start
    to_wait = round(next_launching - finishing_time, 0)  # amount of time system will wait

    # if the sampling process took more time than the sampling period
    if finishing_time >= next_launching:
        logger.error("Measurement took more time than required (" + str(round(sampling_period, 0)) + " seconds)")
        return

    # As long as the current time is smaller than the starting time...
    for i in range(0, int(to_wait)):
        if time.time() < next_launching:
            print("Waiting before next measurement: ", int(to_wait) - i, "seconds (sampling time is set on",
                  sampling_period,
                  "seconds)", end="\r")
            time.sleep(1)

    # Delete the waiting countdown and skip a line
    # Print a whole blank to remove completely the previous line ("Waiting before next measurement...")
    print("                                                                                    ")
    print("Starting new sample...")
    return


# --------------------------------------------
# MAIN CODE
# --------------------------------------------

# INITIATION

now = datetime.now()  # get time
logger.info("Starting of Seacanairy on the " + str(now.strftime("%d/%m/%Y at %H:%M:%S")))  # delete time decimals

# Check that the data file exist, if not, write the first line (which is the columns' name)
if os.path.isfile(path_csv):  # if file exist
    logger.info("'" + str(path_csv) + "' already exist, appending data to this file")
else:  # if file doesn't exist
    logger.info("Initiating '" + str(project_name) + "' file")
    append_data_to_csv("Date/Time", "Relative Humidity", "Temperature", "Pressure",
                       "CO2 average", "CO2 instant",
                       "PM 1", "PM 2.5", "PM 10",
                       "Temperature OPC", "Relative Humidity OPC",
                       "sampling time OPC", "sample flow rate OPC",
                       "bin 0", "bin 1", "bin 2", "bin 3", "bin 4", "bin 5",
                       "bin 6", "bin 7", "bin 8", "bin 9", "bin 10", "bin 11",
                       "bin 12", "bin 13", "bin 14", "bin 15", "bin 16", "bin 17",
                       "bin 18", "bin 19", "bin 20", "bin 21", "bin 22", "bin 23",
                       "bin 1 MToF", "bin 3 MToF", "bin 5 MToF", "bin 7 MToF",
                       "reject count glitch", "reject count long TOF", "reject count ratio",
                       "reject count out of range", "fan revolution count", "laser status",
                       "GPS fix time", "latitude", "longitude", "SOG", "COG", "horizontal precision",
                       "altitude", "WGS84 correction", "fix status")

# Read the internal timestamp of the CO2 sensor, and change the value if necessary
if CO2_sampling_period != CO2.internal_timestamp():  # if internal timestamp is not the good one... change it
    CO2.internal_timestamp(CO2_sampling_period)
    # nothing in the brackets = read, timestamp in the brackets = write

# Set the desired OPC fan speed
OPCN3.set_fan_speed(OPC_fan_speed)  # (check the sampling flow rate displayed by the sensor for seacanairy pump choice)

# Ask the CO2 sensor to take a new sample
CO2.trigger_measurement()

# LOOP

while True:
    # Get date and time to store in the Excel file
    now = datetime.now()
    now = now.strftime("%Y-%m-%d %H:%M:%S")

    # Get the time in second at which the measurement start
    start = time.time()  # return the time expressed in second since the python date reference
    # a bit the same as 'millis()' on Arduino
    # easier to work with than with a complex datetime format and a timedelta function...

    # Get CO2 sensor data (see 'CO2.py')
    print("********* CO2 SENSOR *********")
    CO2_data = CO2.get_data()

    # Get OPC-N3 sensor data (see 'OPCN3.py')
    print("*********** OPC-N3 ***********")
    OPC_data = OPCN3.getdata(OPC_flushing_time, OPC_sampling_time)

    time.sleep(1)

    # Get GPS informations
    print("************ GPS ************")
    GPS_data = GPS.get_position()

    # Save the data in the .csv file
    print("Saving data in", path_csv)
    # If user want to store all the technical data (for the OPCN3, bin, MToF...)
    append_data_to_csv(now, CO2_data["relative humidity"], CO2_data["temperature"], CO2_data["pressure"],
                       CO2_data["average"], CO2_data["instant"],
                       OPC_data["PM 1"], OPC_data["PM 2.5"], OPC_data["PM 10"],
                       OPC_data["temperature"], OPC_data["relative humidity"],
                       OPC_data["sampling time"], OPC_data["sample flow rate"],
                       OPC_data["bin 0"], OPC_data["bin 1"], OPC_data["bin 2"], OPC_data["bin 3"],
                       OPC_data["bin 4"], OPC_data["bin 5"], OPC_data["bin 6"], OPC_data["bin 7"],
                       OPC_data["bin 8"], OPC_data["bin 9"], OPC_data["bin 10"], OPC_data["bin 11"],
                       OPC_data["bin 12"], OPC_data["bin 13"], OPC_data["bin 14"], OPC_data["bin 15"],
                       OPC_data["bin 16"], OPC_data["bin 17"], OPC_data["bin 18"], OPC_data["bin 19"],
                       OPC_data["bin 20"], OPC_data["bin 21"], OPC_data["bin 22"], OPC_data["bin 23"],
                       OPC_data["bin 1 MToF"], OPC_data["bin 3 MToF"],
                       OPC_data["bin 5 MToF"], OPC_data["bin 7 MToF"],
                       OPC_data["reject count glitch"],
                       OPC_data["reject count long TOF"], OPC_data["reject count ratio"],
                       OPC_data["reject count out of range"],
                       OPC_data["fan revolution count"], OPC_data["laser status"],
                       GPS_data["fix time"], GPS_data["latitude"], GPS_data["longitude"],
                       GPS_data["SOG"], GPS_data["COG"], GPS_data["horizontal precision"],
                       GPS_data["altitude"], GPS_data["WGS84 correction"], GPS_data["fix status"])

    # Time at which the sampling finishes
    finish = time.time()  # as previously, expressed in seconds since reference date

    # Calculate the amount of time the sampling process took, round to 0 to avoid decimals
    # int(...) to delete the remaining 0 behind the coma
    logger.info("Sampling finished in " + str(int(round(finish - start, 0))) + " seconds")

    # Wait that the sampling period is passed
    wait_timestamp(start)
