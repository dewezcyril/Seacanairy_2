"""
Main Seacanairy Python Code that execute all the necessary functions to make the system work and take sample
at required intervals
"""

# import AFE
import CO2
import OPCN3
import time
from datetime import date, datetime, timedelta
import csv
from progress.bar import IncrementalBar

# -----------------------------------------
# logging
# -----------------------------------------
import logging

log_file = '/home/pi/seacanairy_project/log/seacanairy.log'

message_level = logging.INFO

# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
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

# ---------------------------------------

sampling_period = 60  # secs


def append_data_to_csv(*data_to_write):
    """
    Store all the measurements in the .csv file
    :param data_to_write: List
    :return:
    """
    to_write = []
    for arg in data_to_write:
        to_write.append(arg)
    print("Saving data in", PATH_CSV)
    with open(PATH_CSV, mode='a', newline='') as csv_file:
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
            print("Waiting before next measurement: ", int(to_wait) - i, "seconds (sampling time is set on", sampling_period,
                  "seconds)", end="\r")
            time.sleep(1)
    print("                                                                                    ")  # to go to next line
    print("Starting new sample...")
    return

# --------------------------------------------
# MAIN CODE
# --------------------------------------------

now = datetime.now()
log = "Starting of Seacanairy on the " + str(now.strftime("%d/%m/%Y %H:%M:%S"))
logger.info(log)

PATH_CSV = "seacanairy.csv"

if CO2.internal_timestamp() != sampling_period:
    CO2.internal_timestamp(sampling_period)

CO2.trigger_measurement()
time.sleep(10)  # it needs around 10 seconds to make the measurement

while True:
    now = datetime.now()

    start = time.time()
    print("***** CO2 SENSOR *****")
    RHT_data = CO2.getRHT()
    CO2_data = CO2.getCO2P()
    print("***** OPC-N3 *****")
    OPC = OPCN3.getdata(1, 5)

    print("  ")
    # date/time, RH, temperature, pressure, CO2 average, CO2 instant, PM1, PM25, PM10, temperature, relative_humidity
    append_data_to_csv(now, RHT_data[0], RHT_data[1], CO2_data[2], CO2_data[0], CO2_data[1], OPC[0], OPC[1], OPC[2], OPC[3], OPC[4])

    finish = time.time()
    log = "Sampling finished in " + str(round(finish - start, 0)) + " seconds"
    logger.info(log)

    wait_timestamp(start, finish)
