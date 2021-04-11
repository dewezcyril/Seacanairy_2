#! /home/pi/seacanairy_project/venv/bin/python3
"""
Main Seacanairy Python Code that execute all the necessary functions to make the system work and take sample
at required intervals
"""

# import all libraries
import time
from datetime import date, datetime, timedelta
import csv  # for storing data in file
from progress.bar import IncrementalBar
import os.path
import os
import yaml
import logging
import RPi.GPIO as GPIO

# ---------------------------------------
# SETTINGS
# ---------------------------------------
# Import the settings from the Yaml file
# Store the different settings in dedicated variables

current_working_directory = str(os.getcwd())

with open(current_working_directory + '/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()  # always close the used files after use

# Sampling period
sampling_period = settings['Seacanairy settings']['Sampling period']

# CO2 sampling period (CO2 sensor takes samples automatically)
CO2_sampling_period = int(sampling_period / settings['CO2 sensor']['Automatic sampling frequency ' \
                                                                   '(number of sample during the above sampling period)'])

# Amount of time required for the CO2 sensor to take the measurement
CO2_startup_delay = settings['CO2 sensor']['Amount of time required for the sensor to take the measurement']

# Name of the research (f-e 'Air measurement in my room'
project_name = settings['Seacanairy settings']['Sampling session name']

# Amound of time while the OPCN3 fan keep running without measurement
OPC_flushing_time = settings['OPC-N3 sensor']['Flushing time']

# Amount of time the OPCN3's laser takes PM sample
OPC_sampling_time = settings['OPC-N3 sensor']['Sampling time']

# OPCN3 Fan speed (0-100)
OPC_fan_speed = settings['OPC-N3 sensor']['Fan speed']

# Let the user choose if he want to activate the following sensor or not
# Seen the problems encountered with GPS and OPCN3, could be good to disable the unnecessary sensors (GPS f-e)
CO2_activation = settings['CO2 sensor']['Activate this sensor']
OPCN3_activation = settings['OPC-N3 sensor']['Activate this sensor']
GPS_activation = settings['GPS']['Activate this sensor']
AFE_activation = settings['AFE Board']['Activate this sensor']

# Pump settings
fresh_air_piping_flushing_time = settings['Seacanairy settings']['Flushing time before measurement']

# -----------------------------------------
# CREATE FILES
# -----------------------------------------

# Create a directory to store everything if it doesn't exit
directory_path = current_working_directory + "/" + project_name
if not os.path.exists(directory_path):
    os.mkdir(directory_path)
    print("Created directory", directory_path)

# Create a file to store the log if it doesn't exist
log_file = directory_path + "-log.log"
if not os.path.isfile(log_file):
    os.mknod(log_file)
    print("Created log file", log_file)
# You can't go further in the program without making those two steps first.

# -----------------------------------------
# IMPORT NECESSARY SENSORS
# -----------------------------------------
# Seen the above settings, import the necessary libraries
# Avoid starting module (i2c, SPI, UART) that will not be used
if CO2_activation:
    import CO2  # Library for the CO2 sensor

if OPCN3_activation:
    import OPCN3  # Library for the OPC-N3 sensor

if GPS_activation:
    import GPS  # Library for the GPS

if AFE_activation:
    import AFE

# -----------------------------------------
# LOGGING
# -----------------------------------------


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

GPIO.setmode(GPIO.BCM)  # use the GPIO names (GPIO1...) instead of the processor pin name (BCM...)
pump_gpio = 27
GPIO.setup(pump_gpio, GPIO.OUT, initial=GPIO.LOW)

# -----------------------------------------
# FUNCTIONS
# -----------------------------------------


def loading_bar(name, delay):
    """
    Show a loading bar on the screen during sampling for example
    :param name: Text to be shown on the left of the loading bar
    :param length: Number of increments necessary for the bar to be full
    :return: nothing
    """
    bar = IncrementalBar(name, max=(2 * delay), suffix='%(elapsed)s/' + str(delay) + ' seconds')
    for i in range(2 * delay):
        time.sleep(0.5)
        bar.next()
    bar.finish()
    return


def pump_start():
    GPIO.output(pump_gpio, GPIO.HIGH)
    print("Air pump is on")


def pump_stop():
    GPIO.output(pump_gpio, GPIO.LOW)
    print("Air pump is off")


def append_data_to_csv(*data_to_write):
    """
    Store all the measurements in the .csv file
    :param data_to_write: unlimited amount of arguments
    :return: nothing
    """
    # Concatenate all the arguments in one list
    to_write = [*data_to_write]

    with open(csv_file, mode='a', newline='') as data_file:
        writer = csv.writer(data_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(to_write)
    data_file.close()  # close file after use(general safety practice)


def wait_timestamp(starting_time):
    """
    Wait that the sampling period is passed out to start the next measurement
    :param starting_time: time at which the measurement has started ('time.time()' required)
    :return: Function stop when next measurement can start
    """
    finishing_time = time.time()
    next_launching = starting_time + sampling_period  # time at which the next sample should start

    # if the sampling process took more time than the sampling period
    if finishing_time >= next_launching:
        logger.error("Measurement took more time than required (" + str(round(sampling_period, 0)) + " seconds)")
        return

    while True:
        now = time.time()
        if now < next_launching:
            to_wait = round(next_launching - now, 0)  # amount of time system will wait
            print("Waiting before next measurement:", int(to_wait), "seconds (sampling time is set on",
                  sampling_period,
                  "seconds)", end="\r")
            time.sleep(.2)
        else:
            break

    # Delete the waiting countdown and skip a line
    # Print a whole blank to remove completely the previous line ("Waiting before next measurement...")
    print("                                                                                    ")
    print("Starting new sample...")
    return


# --------------------------------------------
# MAIN CODE
# --------------------------------------------

# INITIATE CSV FILE

# Create the file to store the data if it doesn't exist
csv_file = directory_path + "/" + str(project_name) + "-data.csv"
if not os.path.isfile(csv_file):  # if the file doesn't exist
    os.mknod(csv_file)  # create the file
    print("Created data file", csv_file)
    # Write a first line to the file, this will be the column headers
    append_data_to_csv("Date/Time", "Relative Humidity (%RH)", "Temperature (°C)", "Pressure (hPa)",
                       "CO2 average (ppm)", "CO2 instant (ppm)",
                       "PM 1 (μg/m³)", "PM 2.5 (μg/m³)", "PM 10 (μg/m³)",
                       "Temperature OPC (°C)", "Relative Humidity OPC (%RH)",
                       "sampling time OPC (sec)", "sample flow rate OPC (ml/s)",
                       "bin 0", "bin 1", "bin 2", "bin 3", "bin 4", "bin 5",
                       "bin 6", "bin 7", "bin 8", "bin 9", "bin 10", "bin 11",
                       "bin 12", "bin 13", "bin 14", "bin 15", "bin 16", "bin 17",
                       "bin 18", "bin 19", "bin 20", "bin 21", "bin 22", "bin 23",
                       "bin 1 MToF", "bin 3 MToF", "bin 5 MToF", "bin 7 MToF",
                       "reject count glitch", "reject count long TOF", "reject count ratio",
                       "reject count out of range", "fan revolution count", "laser status",
                       "temperature (°C)", "temperature (mV)",
                       "NO2 (ppm)", "NO2 main (mV)", "NO2 aux (mV)",
                       "OX (ppm)", "OX main (mV)", "OX aux (mV)",
                       "SO2 (ppm)", "SO2 main (mV)", "SO2 aux (mV)",
                       "CO2 (ppm)", "CO2 main (mV)", "CO2 aux (mV)",
                       "Date and time (UTC)",
                       "GPS fix date and time (UTC)", "latitude", "longitude", "SOG (kts)", "COG",
                       "horizontal dilution of precision", "accuracy",
                       "altitude (m)", "WGS84 correction (m)", "fix type", "sensor status")
else:
    logger.info("'" + str(csv_file) + "' already exist, appending data to this file")

now = datetime.now()  # get time
logger.info("Starting of Seacanairy on the " + str(now.strftime("%d/%m/%Y at %H:%M:%S")))  # delete time decimals

# WARN USER IF A SENSOR IS DEACTIVATED

if not CO2_activation:
    logger.warning("CO2 sensor has been disabled by the user in 'seacanairy_settings.yaml'")

if not OPCN3_activation:
    logger.warning("OPC-N3 sensor has been disabled by the user in 'seacanairy_settings.yaml'")

if not GPS_activation:
    logger.warning("GPS has been disabled by the user in 'seacanairy_settings.yaml'")

    # SET INTERNAL CO2 SENSOR TIMESTAMP

if CO2_activation:
    # Read the internal timestamp of the CO2 sensor, and change the value if necessary
    if CO2_sampling_period != CO2.internal_timestamp():  # if internal timestamp is not the good one... change it
        CO2.internal_timestamp(CO2_sampling_period)
        # nothing in the brackets = read, timestamp in the brackets = write
else:  # if user don't want to use the sensor...
    try:
        # set the internal timestamp to the longest period available to reduce its wear...
        CO2.internal_timestamp(3600)
        logger.info("CO2 sensor disabled, internal timestamp set on 3600 seconds to reduce its wear")
    except:
        # It means that CO2 sensor is maybe not plugged in...
        pass  # nothing to do if it fails

if OPCN3_activation:
    # Set the desired OPC fan speed
    OPCN3.set_fan_speed(OPC_fan_speed)

if CO2_activation:
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

    pump_start()

    if fresh_air_piping_flushing_time != 0:
        loading_bar('Flushing fresh air in the piping system', fresh_air_piping_flushing_time)

    to_write = []  # create the list in which data to store will be saved
    # [a, b, c] + [d, e, f] = [a, b, c, d, e, f]

    if CO2_activation:
        # Get CO2 sensor data (see 'CO2.py')
        print("******************* CO2 SENSOR *******************")
        CO2.trigger_measurement()
        CO2_data = CO2.get_data()
        to_write += [CO2_data["relative humidity"], CO2_data["temperature"], CO2_data["pressure"],
                     CO2_data["average"], CO2_data["instant"]]

    if OPCN3_activation:
        # Get OPC-N3 sensor data (see 'OPCN3.py')
        print("********************* OPC-N3 *********************")
        OPC_data = OPCN3.getdata(OPC_flushing_time, OPC_sampling_time)
        to_write += [OPC_data["PM 1"], OPC_data["PM 2.5"], OPC_data["PM 10"],
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
                     OPC_data["fan revolution count"], OPC_data["laser status"]]

    if AFE_activation:
        # Get OPC-N3 sensor data (see 'AFE.py')
        print("****************** AFE BOARD ********************")
        AFE_data = AFE.getdata()
        to_write += [AFE_data["temperature"], AFE_data["temperature raw"],
                     AFE_data["NO2 ppm"], AFE_data["NO2 main"], AFE_data["NO2 aux"],
                     AFE_data["OX ppm"], AFE_data["OX main"], AFE_data["OX aux"],
                     AFE_data["SO2 ppm"], AFE_data["SO2 main"], AFE_data["SO2 aux"],
                     AFE_data["CO ppm"], AFE_data["CO main"], AFE_data["CO aux"]
                     ]

    pump_stop()

    if GPS_activation:
        # print("Wait switching from SPI to UART...", end='\r')
        # time.sleep(1)  # avoid too close communication between SPI of OPC and UART of GPS
        # Get GPS information
        print("********************** GPS **********************")
        GPS_data = GPS.get_position()
        to_write += [GPS_data["current time"], GPS_data["fix date and time"],
                     GPS_data["latitude"], GPS_data["longitude"],
                     GPS_data["SOG"], GPS_data["COG"], GPS_data["horizontal precision"], GPS_data["accuracy"],
                     GPS_data["altitude"], GPS_data["WGS84 correction"], GPS_data["fix status"], GPS_data["status"]]

    # Store everything in the csv file
    append_data_to_csv(now, *to_write)

    # Time at which the sampling finishes
    finish = time.time()  # as previously, expressed in seconds since reference date

    # Calculate the amount of time the sampling process took, round to 0 to avoid decimals
    # int(...) to delete the remaining 0 behind the coma
    logger.info("Sampling finished in " + str(int(round(finish - start, 0))) + " seconds")

    # Wait that the sampling period is passed
    wait_timestamp(start)
