"""
Main Seacanairy Python Code that execute all the necessary functions to make the system work and take sample
at required intervals
"""

# import libraries
import CO2  # Library for the CO2 sensor
import OPCN3  # Library for the OPC-N3 sensor
import time
from datetime import date, datetime, timedelta
import csv  # for storing data in file
from progress.bar import IncrementalBar
import os.path
import yaml
import logging

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

OPC_keep_all_data = settings['OPC-N3 sensor']['Keep a record of all the technical data']

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
    to_write = []
    for arg in data_to_write:
        to_write.append(arg)
    print("Saving data in", path_csv)
    with open(path_csv, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(to_write)
    csv_file.close()


def wait_timestamp(starting_time, finish_time):
    """
    Wait that the sampling period is passed out to start the next measurement
    :param starting_time: time at which the measurement has started
    :return: Function stop when next measurement can start
    """
    next_launching = starting_time + sampling_period
    to_wait = round(sampling_period - (finish_time - starting_time), 0)
    if finish_time >= next_launching:
        log = "Measurement took more time than required (" + str(round(sampling_period, 0)) + " seconds)"
        logger.error(log)
        return
    while time.time() < next_launching:
        time.sleep(0.5)
        for i in range(0, int(to_wait)):
            print("Waiting before next measurement: ", int(to_wait) - i, "seconds (sampling time is set on",
                  sampling_period,
                  "seconds)", end="\r")
            time.sleep(1)
    print("                                                                                    ")  # to go to next line
    print("Starting new sample...")
    return


# --------------------------------------------
# MAIN CODE
# --------------------------------------------


now = datetime.now()
logger.info("Starting of Seacanairy on the " + str(now.strftime("%d/%m/%Y %H:%M:%S")))

# Check that the file exist, if not, write the first line (name of the columns)
if os.path.isfile(path_csv):
    logger.info("'" + str(path_csv) + "' already exist, appending data to this file")
else:
    append_data_to_csv("Date/Time", "Relative Humidity", "Temperature", "Pressure", "CO2 average", "CO2 instant",
                       "PM 1", "PM 2.5", "PM 10", "Temperature OPC", "Relative Humidity OPC",
                       "bin", "MToF", "Sampling Time", "Sample flow rate",
                       "reject count glitch", "reject count longTOF", "reject count ratio", "reject count out of range",
                       "fan revolution count", "laser status")

# Read the internal timestamp of the sensor, and change the value if necessary
if CO2_sampling_period != CO2.internal_timestamp():
    CO2.internal_timestamp(CO2_sampling_period)

CO2.trigger_measurement()
time.sleep(settings['CO2 sensor']['Amount of time required for the sensor to take the measurement'])
# it needs around 10 seconds to make the measurement

while True:
    now = datetime.now()

    start = time.time()

    print("********* CO2 SENSOR *********")
    CO2_data = CO2.get_data()

    print("********* OPC-N3 *********")
    OPC_data = OPCN3.getdata(OPC_flushing_time, OPC_sampling_time)

    print("  ")

    if OPC_keep_all_data:
        append_data_to_csv(now, CO2_data["relative humidity"], CO2_data["temperature"], CO2_data["average"], CO2_data["instant"],
                           OPC_data["PM 1"], OPC_data["PM 2.5"], OPC_data["PM 10"], OPC_data["temperature"], OPC_data["relative humidity"],
                           OPC_data["bin"],
                           OPC_data["MToF"], OPC_data["sampling time"], OPC_data["sample flow rate"], OPC_data["reject count out of range"],
                           OPC_data["fan revolution count"], OPC_data["laser status"])
    else:
        append_data_to_csv(now, CO2_data["relative humidity"], CO2_data["temperature"], CO2_data["average"], CO2_data["instant"],
                           OPC_data["PM 1"], OPC_data["PM 2.5"], OPC_data["PM 10"], OPC_data["temperature"], OPC_data["relative humidity"])

    finish = time.time()
    log = "Sampling finished in " + str(round(finish - start, 0)) + " seconds"
    logger.info(log)

    wait_timestamp(start, finish)
