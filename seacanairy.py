"""
Software for the retrieve, storing and management of the Seacanairy 2
"""

# import AFE
import CO2
import OPCN3
import time
from datetime import date, datetime, timedelta
import csv

# -----------------------------------------
# logging
# -----------------------------------------
import logging

log_file = '/home/pi/seacanairy_project/log/seacanairy.log'

message_level = logging.DEBUG

# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=log_file,
                    filemode='a')
# # define a Handler which writes INFO messages or higher to the sys.stderr/display
# console = logging.StreamHandler()
# console.setLevel(message_level)
# # set a format which is simpler for console use
# formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# # tell the handler to use this format
# console.setFormatter(formatter)
# # add the handler to the root logger
# logging.getLogger().addHandler(console)

logger = logging.getLogger('SEACANAIRY')

# ---------------------------------------


timestamp = 60  # secs

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


def wait_timestamp(starting_time):
    """
    Wait that the timestamp is passed out to start the next measurement
    :param starting_time: time at which the measurement has started
    :return: Function stop when next measurement can start
    """
    finish_time = time.time()
    next_launching = starting_time + timestamp
    if finish_time < next_launching:
        print("Waiting", end='')
    else:
        log = "Measurement took more time than the defined sampling time (" + str(timestamp) + ")"
        logger.error(log)
    while time.time() < next_launching:
        time.sleep(2)
        print(".", end='')


    print(" ")
    print("Starting new sample...")
    return

if __name__ == '__main__':

    start_time = datetime.now()
    logger.info("------------------------------------")
    log = "Launching a new execution on the " + str(start_time.strftime("%d/%m/%Y %H:%M:%S"))
    logger.info(log)

    PATH_CSV = "seacanairy.csv"

    sampling_time = 60

    while True:
        start_time = datetime.now()
        millis = time.time()
        next_launching = start_time + timedelta(seconds=sampling_time)
        RHT_data = CO2.getRHT()
        CO2_data = CO2.getCO2P()

        PM = OPCN3.getPM(5, 5)

        append_data_to_csv(start_time, RHT_data[0], RHT_data[1], CO2_data[2], CO2_data[0], CO2_data[1], PM[0], PM[1], PM[2])
        finish_time = time.time()
        print("Sampling finished in", round(finish_time - millis, 0), "seconds")
        wait_timestamp(millis)
