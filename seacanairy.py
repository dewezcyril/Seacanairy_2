#! /home/pi/seacanairy_project/venv/bin/python3
"""
This code aims to make the whole Seacanairy works! It start the pump, read the date from the CO2 sensor,
the OPC-N3, the AFE board, the GPS, stop the pump, and store the whole in a file.
"""

# import all libraries
import time
from datetime import date, datetime, timedelta
import csv  # for storing data in file
from progress.bar import IncrementalBar  # to show beautiful loading bar on the screen during sampling
import os  # to be able to create new files/folders and see the current path
import yaml  # to read the settings stored in the 'seacanairy_settings.yaml' file
import logging  # to store the errors messages in a separate log file
import threading

# ---------------------------------------
# HELLO
# ---------------------------------------
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
print("~~~~~~~~~~~~~~~~ SEACANAIRY ~~~~~~~~~~~~~~~~")
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

# ---------------------------------------
# CHECK THE TIME
# ---------------------------------------
print("\n################# TIME #################")
print("Current date and time is:", datetime.now())
print("If time is not correct, close this window and click on 'Check Date and Time'")

# ---------------------------------------
# SETTINGS
# ---------------------------------------
# Import the settings from the Yaml file
# Store the different settings in dedicated variables to get it more easy

print("\n################ FILES #################")

current_working_directory = str(os.getcwd())  # returns the path where the python script is currently running

with open(current_working_directory + '/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)  # load all the yaml file in a dictionary
    file.close()  # always close the file after use

# Sampling period
sampling_period = settings['Seacanairy settings']['Sampling period']

# CO2 sampling period (CO2 sensor takes samples automatically)
CO2_sampling_period = int(sampling_period / settings['CO2 sensor']['Automatic sampling frequency ' \
                                                                   '(number of sample during the above sampling period)'])

# Amount of time required for the CO2 sensor to take the measurement
CO2_startup_delay = settings['CO2 sensor']['Amount of time required for the sensor to take the measurement']

# Name of the research (f-e 'Air measurement in my room')
project_name = settings['Seacanairy settings']['Sampling session name']

# Amount of time while the OPCN3 fan keep running without measurement to flush fresh air inside the casing
OPC_flushing_time = settings['OPC-N3 sensor']['Flushing time']

# Amount of time the OPCN3's laser takes PM sample
OPC_sampling_time = settings['OPC-N3 sensor']['Sampling time']

# OPCN3 Fan speed (0-100)
OPC_fan_speed = settings['OPC-N3 sensor']['Fan speed']

# Number of reading AFE must take and average
AFE_readings_averaged = settings['AFE Board']['Noise reduction - number of reading averaged']

# Let the user choose if he want to activate the following sensor or not
# Seen the problems encountered with GPS and OPCN3, could be good to disable the unnecessary sensors (GPS f-e)
# This does not shut down the sensor powering
CO2_activation = settings['CO2 sensor']['Activate this sensor']
OPCN3_activation = settings['OPC-N3 sensor']['Activate this sensor']
GPS_activation = settings['GPS']['Activate this sensor']
AFE_activation = settings['AFE Board']['Activate this sensor']
air_pump_activation = settings['Seacanairy settings']['Activate M&C air pump']
flow_sensor_activation = settings['Air flow sensor']['Activate this sensor']
OPCN3_flow_measurement = settings['Air flow sensor']['Measure during OPCN3 measurement']

# Air pump settings
fresh_air_piping_flushing_time = settings['Seacanairy settings']['Flushing time before measurement']

# -----------------------------------------
# CREATE FILES
# -----------------------------------------

# Create a directory to store everything if it doesn't exit
directory_path = current_working_directory + "/" + project_name
if not os.path.exists(directory_path):
    os.mkdir(directory_path)  # create the directory
    print("Created directory", directory_path)

# Create a file to store the log if it doesn't exist
log_file = directory_path + "/" + project_name + "-log.log"
if not os.path.isfile(log_file):
    os.mknod(log_file)  # create the file
    print("Created log file", log_file)
else:
    # Add a line to separate different executions
    file_logfile = open(log_file, "a")
    file_logfile.write("********************** NEW SESSION **********************\n")
    file_logfile.close()
# You can't go further in the program without creating the folder and the logger file

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

if air_pump_activation:
    import RPi.GPIO as GPIO  # to put GPIO high/low to switch the air pump relay on and off

if flow_sensor_activation:
    import flow as flow

# -----------------------------------------
# LOGGING
# -----------------------------------------
# Save the messages shown on the console in a dedicated file to understand the possible issues afterwards

message_level = logging.INFO

# set up logging to file
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

# Following logging messages must be called by logger.debug (...)

# -----------------------------------------
# FUNCTIONS
# -----------------------------------------
# Use the GPIO to turn on and off the air pump via relay

if air_pump_activation:
    GPIO.setwarnings(False)  # avoid messages concerning GPIO (GPIO is already low, blablabla)
    GPIO.setmode(GPIO.BCM)  # use the GPIO names (GPIO1...) instead of the processor pin name (BCM...)
    pump_gpio = 27
    GPIO.setup(pump_gpio, GPIO.OUT, initial=GPIO.LOW)


# -----------------------------------------
# FUNCTIONS
# -----------------------------------------


def loading_bar(name, delay):
    """
    Show a loading bar on the screen during a a certain amount of time
    Make the user understand the software is doing/waiting for something
    :param name: Text to be shown on the left of the loading bar
    :param delay: Amount of time the system is waiting in seconds
    :return: nothing
    """
    bar = IncrementalBar(name, max=(2 * delay), suffix='%(elapsed)s/' + str(delay) + ' seconds')
    for i in range(2 * delay):
        time.sleep(0.5)
        bar.next()
    bar.finish()
    return


def pump_start():
    """
    It put tension on the GPIO number 27 to turn on the air pump relay
    :return: nothing
    """
    GPIO.output(pump_gpio, GPIO.HIGH)


def pump_stop():
    """
    It remove tension from the GPIO number 27 to turn off the air pump relay
    :return: nothing
    """
    GPIO.output(pump_gpio, GPIO.LOW)


def append_data_to_csv(*data_to_write):
    """
    Store all the arguments given in the -data.csv file
    All arguments will be separated by a coma in the csv file
    :param data_to_write: unlimited amount of arguments
    :return: nothing
    """
    to_write = []
    for i in data_to_write:
        if isinstance(i, list):
            to_write += i
        else:
            to_write += [i]

    # to_write = [*data_to_write]  # Concatenate all the arguments in one list

    with open(csv_file, mode='a', newline='') as data_file:
        writer = csv.writer(data_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(to_write)
    data_file.close()  # close file after use(general safety practice)


def wait_timestamp(starting_time):
    """
    Wait that the sampling period is passed out to start the next measurement
    :param starting_time: time at which the measurement has started ('time.time()' required)
    :return: Nothing, function will stop when the next measurement can start
    """
    finishing_time = time.time()
    next_launching = starting_time + sampling_period  # time at which the next sample should start

    # if the sampling process took more time than the expected sampling period
    if finishing_time >= next_launching:
        logger.error("Sampling cycle took " + str(round((finishing_time - next_launching), 1)) +
                     "seconds more than expected (" + str(round(sampling_period, 0)) + " seconds)")
        print("Starting new sample...")
        return  # function stop and new sample start

    while True:
        now = time.time()
        for i in range(10):
            if now < next_launching:
                time.sleep(.1)
            else:
                break
        to_wait = round(next_launching - now, 0)  # amount of time system will wait
        print("Waiting before next measurement:", int(to_wait), "seconds (sampling time is set on",
              sampling_period,
              "seconds)  ", end="\r")
        if not now < next_launching:
            break

    # Delete the waiting countdown and skip a line
    # Print a whole blank to remove completely the previous line ("Waiting before next measurement...")
    print("                                                                                    ")
    print("Starting new sample...")
    return  # function stop and new sample start


# --------------------------------------------
# MAIN CODE
# --------------------------------------------

# INITIATE CSV FILE

# Create the file to store the data if it doesn't exist
csv_file = directory_path + "/" + str(project_name) + "-data.csv"
if not os.path.isfile(csv_file):  # if the file doesn't exist
    os.mknod(csv_file)  # create the file
    print("Initializing data file", csv_file)
    # Write a first line to the file, this will be the column headers
    to_write = []
    to_write += ["Date/Time"]

    # for the OPC-N3 sensor:
    to_write += ["PM 1 (μg/m³)", "PM 2.5 (μg/m³)", "PM 10 (μg/m³)",
                 "Temperature OPC (°C)", "Relative Humidity OPC (%RH)",
                 "sampling time OPC (sec)", "sample flow rate OPC (ml/s)",
                 "bin 0", "bin 1", "bin 2", "bin 3", "bin 4", "bin 5",
                 "bin 6", "bin 7", "bin 8", "bin 9", "bin 10", "bin 11",
                 "bin 12", "bin 13", "bin 14", "bin 15", "bin 16", "bin 17",
                 "bin 18", "bin 19", "bin 20", "bin 21", "bin 22", "bin 23",
                 "bin 1 MToF", "bin 3 MToF", "bin 5 MToF", "bin 7 MToF",
                 "reject count glitch", "reject count long TOF", "reject count ratio",
                 "reject count out of range", "fan revolution count", "laser status"]

    # for the OPC-N3 flow measurement:
    to_write += ["average flow[sccm]", "average flow [slm]", "average flow [slh]"]

    # for the AFE:
    to_write += ["temperature (°C)", "temperature (mV)",
                 "NO2 (ppm)", "NO2 main (mV)", "NO2 aux (mV)",
                 "OX (ppm)", "OX main (mV)", "OX aux (mV)",
                 "SO2 (ppm)", "SO2 main (mV)", "SO2 aux (mV)",
                 "CO2 (ppm)", "CO2 main (mV)", "CO2 aux (mV)"]

    # for the flow sensor:
    to_write += ["flow (sccm)", "flow (slm)", "flow (slh)"]

    # for the GPS:
    to_write += ["Date and time (UTC)",
                 "GPS fix date and time (UTC)", "latitude", "longitude", "SOG (kts)", "COG",
                 "horizontal dilution of precision", "accuracy",
                 "altitude (m)", "WGS84 correction (m)", "fix type", "GPS status"]

    # for the CO2 sensor:
    to_write += ["Relative Humidity (%RH)", "Temperature (°C)", "Pressure (hPa)",
                 "CO2 average (ppm)", "CO2 instant (ppm)"]

    append_data_to_csv(to_write)

else:
    logger.info("'" + str(csv_file) + "' already exist")
    logger.info("Appending data to this file")

print("\n########### STARTING SENSORS ############")

# Keep a trace of the day and time at which the system has started

now = datetime.now()  # get time
logger.info("Starting of Seacanairy on the " + str(now.strftime("%d/%m/%Y at %H:%M:%S")))  # delete time decimals

# WARN USER IF A SENSOR IS DEACTIVATED

if not CO2_activation:
    logger.warning("CO2 sensor has been disabled by the user in 'seacanairy_settings.yaml'")

if not OPCN3_activation:
    logger.warning("OPC-N3 sensor has been disabled by the user in 'seacanairy_settings.yaml'")

if not GPS_activation:
    logger.warning("GPS has been disabled by the user in 'seacanairy_settings.yaml'")

if not air_pump_activation:
    logger.warning("Air pump has been disabled by the user in 'seacanairy_settings.yaml'")

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
    # Initialize OPCN3 SPI, avoid loosing first communication
    OPCN3.initialization_SPI()

if CO2_activation:
    # Ask the CO2 sensor to take a new sample
    print("Synchronizing CO2 sensor with Seacanairy sampling period")
    CO2.trigger_measurement(True)  # True == force

if OPCN3_activation:
    # Set the desired OPC fan speed
    OPCN3.set_fan_speed(OPC_fan_speed)


print("\n############## SAMPLING! ###############")

# LOOP which will run continuously

while True:
    # Get date and time to store in the Excel file
    now = datetime.now()
    now = now.strftime("%d-%m-%Y %H:%M:%S")  # remove the decimals and change the date order

    # Get the time in second at which the measurement start
    start = time.time()  # return the time expressed in second since the python date reference
    # a bit the same as 'millis()' on Arduino
    # easier to work with than with a complex string datetime format and a timedelta function...

    if air_pump_activation:
        pump_start()  # start the pump
        print("Air pump is on")

    # If user want to flush the piping system before beginning the sampling
    if fresh_air_piping_flushing_time != 0:
        loading_bar('Flushing fresh air in the piping system', fresh_air_piping_flushing_time)

    to_write = []  # create the list in which data to store will be saved
    # [a, b, c] + [d, e, f] = [a, b, c, d, e, f]

    if CO2_activation:
        print("Triggering CO2 measurement (measurement reading will come later...)")
        CO2.trigger_measurement()

    if AFE_activation:
        AFE_thread = threading.Thread(target=AFE.start_averaged_data, args=[AFE_readings_averaged], daemon=True)
        print("Reading averaged AFE in background (data will show up later...)")
        AFE_thread.start()

    if OPCN3_activation:
        # Start Flow Rate thread
        flow_period = 4
        flow_number_measurements = 4
        flow_delay = 3
        if OPCN3_flow_measurement:
            flow_thread = threading.Thread(target=flow.start_averaged_measurement,
                                           args=[flow_period, flow_number_measurements, flow_delay], daemon=True)
            print("Reading flow rate during", flow_period, "seconds after", flow_delay,
                  "seconds delay in background (readings will come later...)")
            flow_thread.start()
        # Get OPC-N3 sensor data (see 'OPCN3.py')
        print("********************* OPC-N3 *********************")
        OPC_data = OPCN3.get_data(OPC_flushing_time, OPC_sampling_time)
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

        if OPCN3_flow_measurement:
            print("**************** OPC FLOW AVERAGE ****************")
            print("Finishing reading averaged flow rate...", end='\r')
            flow_thread.join()  # wait the end of the thread
            print("                                        ", end='\r')
            flow_OPC_data = flow.get_averaged_measurement()
            to_write += [flow_OPC_data['average flow [sccm]'], flow_OPC_data['average flow [slm]'],
                         flow_OPC_data['average flow [slh]']]

    if AFE_activation:
        # Get OPC-N3 sensor data (see 'AFE.py')
        print("****************** AFE BOARD ********************")
        print("Finishing reading background averaged AFE...", end='\r')
        AFE_thread.join()  # wait the end of the thread
        print("                                  ", end='\r')
        AFE_data = AFE.get_averaged_data()
        to_write += [AFE_data["temperature"], AFE_data["temperature raw"],
                     AFE_data["NO2 ppm"], AFE_data["NO2 main"], AFE_data["NO2 aux"],
                     AFE_data["OX ppm"], AFE_data["OX main"], AFE_data["OX aux"],
                     AFE_data["SO2 ppm"], AFE_data["SO2 main"], AFE_data["SO2 aux"],
                     AFE_data["CO ppm"], AFE_data["CO main"], AFE_data["CO aux"]]

    if flow_sensor_activation:
        # get flow measure
        print("******************* FLOW METER *******************")
        flow_data = flow.get_data()
        to_write += [flow_data['flow [sccm]'], flow_data['flow [slm]'], flow_data['flow [slh]']]

    if air_pump_activation:
        pump_stop()
        print("Air pump is off (pump has run", round(time.time() - start, 0), "seconds)")

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

    if CO2_activation:
        # Get CO2 sensor data (see 'CO2.py')
        print("******************* CO2 SENSOR *******************")
        CO2_data = CO2.get_data()
        to_write += [CO2_data["relative humidity"], CO2_data["temperature"], CO2_data["pressure"],
                     CO2_data["average"], CO2_data["instant"]]


    # Store everything in the csv file
    append_data_to_csv(now, to_write)

    # Time at which the sampling finishes
    finish = time.time()  # as previously, expressed in seconds since reference date

    # Calculate the amount of time the sampling process took, round to 0 to avoid decimals
    # int(...) to delete the remaining 0 behind the coma
    logger.info("Sampling finished in " + str(int(round(finish - start, 0))) + " seconds")

    # Wait that the sampling period is passed
    wait_timestamp(start)
