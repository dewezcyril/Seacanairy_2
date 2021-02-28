"""
Software for the retrieve, storing and management of the Seacanairy 2
"""

import AFE
import CO2
import OPCN3
import time
from datetime import date, datetime
import csv

# -----------------------------------------
# logging
# -----------------------------------------
import logging

log_file = './log/seacanairy.log'

message_level = logging.DEBUG

# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
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

now = datetime.now()
logging.info("------------------------------------")
log = "Launching a new execution on the " + str(now.strftime("%d/%m/%Y %H:%M:%S"))
logging.info(log)

PATH_CSV = "seacanairy.csv"

def append_data_to_csv(data_to_write):
    """
    Store all the measurements in the .csv file
    :param data_to_write: List
    :return:
    """
    with open(PATH_CSV, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(data_to_write)
    csv_file.close()




