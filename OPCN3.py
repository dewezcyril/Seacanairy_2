#! /home/pi/seacanairy_project/venv/bin/python3
"""
Library for the use and operation of Alphasense OPC-N3 sensor
"""

import spidev  # driver for the SPI/serial communication
import time
import struct  # to convert the IEEE bytes to float
import datetime
import sys
import os.path
from progress.bar import IncrementalBar  # progress bar during sampling
# import RPi.GPIO as GPIO

# yaml settings
import yaml

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------

with open('/home/pi/seacanairy_project/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

store_debug_messages = settings['CO2 sensor']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

OPC_flushing_time = settings['OPC-N3 sensor']['Flushing time']

OPC_sampling_time = settings['OPC-N3 sensor']['Sampling time']

take_new_sample_if_checksum_is_wrong = \
    settings['OPC-N3 sensor'][
        'Take a new measurement if checksum is wrong (avoid shorter sampling periods when errors)']

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
# all the settings and other code for the logging
# logging = tak a trace of some messages in a file to be reviewed afterward (check for errors fe)

import logging

if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    log_file = '/home/pi/seacanairy_project/log/OPCN3-debug.log'  # complete file location required for the Raspberry
    print("DEBUG messages will be shown and stored in '" + str(log_file) + "'")

    # define a Handler which writes INFO messages or higher to the sys.stderr/display
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

else:  # if this file is considered as a library (if you execute 'seacanairy.py' for example)
    # it will only print and store INFO messages and above in the corresponding log_file
    if store_debug_messages:
        message_level = logging.DEBUG
    else:
        message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/' + project_name + '.log'  # complete location needed on the RPI
    # no need to add a handler, because there is already one in seacanairy.py

# set up logging to file
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m %H:%M',
                    filename=log_file,
                    filemode='a')

logger = logging.getLogger('OPC-N3')  # name of the logger
# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as 'ROOT' and NOT 'OPC-N3'


# ----------------------------------------------
# SPI CONFIGURATION
# ----------------------------------------------
# configuration of the Serial communication to the sensor


bus = 0  # name of the SPI bus on the Raspberry Pi 3B+
device = 0  # name of the SS (Ship Selection) pin used for the OPC-N3
spi = spidev.SpiDev()  # enable SPI (SPI must be enable in the RPi settings beforehand)
spi.open(bus, device)
spi.max_speed_hz = 400000  # 750 kHz
spi.mode = 0b01  # bytes(0b01) = int(1) --> SPI mode 1
# first bit (from right) = CPHA = 0 --> data are valid when clock is rising
# second bit (from right) = CPOL = 0 --> clock is kept low when idle
wait_10_milli = 0.015  # 15 ms
wait_10_micro = 1e-06
wait_reset_SPI_buffer = 3  # seconds
time_available_for_initiate_transmission = 10  # seconds - amount of time for the system to initiate transmission


# if the sensor is disconnected, it can happen that the RPi wait for its answer, which never comes...
# avoid the system to wait for unlimited time for that answer

# CS (chip selection) manually via GPIO - NOT USED ANYMORE, WORKS GOOD WITH THE BUILD IN CS LINE
# GPIO.setmode(GPIO.BCM)  # use the GPIO names (GPIO1...) instead of the processor pin name (BCM...)
# CS = 25
# GPIO.setup(CS, GPIO.OUT, initial=GPIO.HIGH)


# def cs_high(delay=0.010):
#     """Close communication with OPC-N3 by setting CS on HIGH"""
#     time.sleep(delay)
#     # GPIO.output(CS, GPIO.HIGH)
#     # time.sleep(delay)
#
#
# def cs_low(delay=0.010):
#     """Open communication with OPC-N3 by setting CS on LOW"""
#     time.sleep(delay)
#     # GPIO.output(CS, GPIO.LOW)
#     # time.sleep(delay)


def initiate_transmission(command_byte):
    """
    Initiate SPI transmission to the OPC-N3
    First loop of the Flow Chart
    :return: TRUE when power state has been initiated
    """
    attempts = 1  # sensor is busy loop
    cycle = 1  # SPI buffer reset loop (going to the right on the flowchart)

    logger.debug("Initiate transmission with command byte " + str(command_byte))

    stop = time.time() + time_available_for_initiate_transmission
    # time in seconds at which we consider it tooks too much time to answer

    spi.open(0, 0)  # open the serial port
    # cs_low()  # not used anymore

    while time.time() < stop:
        reading = spi.xfer([command_byte])  # initiate control of power state
        # spi.xfer() = write a byte AND READ AT THE SAME TIME

        if reading == [243]:  # SPI ready = 0xF3 = 243
            time.sleep(wait_10_micro)
            return True  # indicate that the initiation succeeded

        if reading == [49]:  # SPI busy = 0x31 = 49
            time.sleep(wait_10_milli)
            attempts += 1

        elif reading == [230] or reading == [99] or reading == [0]:
            # during developing, I noticed that those were the value read while having this kind of issue
            # this comes from personal investigation and not from the official documentation
            logger.critical("Problem with the SS (Slave Select) line "
                            "(error code " + str(hex(reading[0])) + "), skipping")
            cycle += 1
            logger.debug("Check that SS line is well kept DOWN (0V) during transmission."
                         " Try again by connecting SS Line of sensor to Ground")
            time.sleep(wait_reset_SPI_buffer)
            return False

        else:
            logger.critical(
                "Failed to initiate transmission (unexpected code returned: " + str(hex(reading[0])) + ") (" + str(
                    cycle) + "/3)")
            time.sleep(wait_reset_SPI_buffer)
            cycle += 1  # increment of attempts

        if attempts > 60:
            # it is recommended to use > 20 in the Alphasense documentation
            # 60 seems to be a good value
            # (does not take too much time, and let some chance to the sensor to answer READY)
            logger.error("Failed 60 times to initiate control of power state, reset OPC-N3 SPI buffer, trying again")
            # cs_high()
            time.sleep(wait_reset_SPI_buffer)  # time for spi buffer to reset

            attempts = 1  # reset the "SPI busy" loop
            cycle += 1  # increment of the SPI reset loop
            # cs_low()

        if cycle >= 3:
            logger.critical("Failed to initiate transmission (reset 3 times SPI, still error)")
            return False

    logger.critical("Transmission initiation took too much time (> "
                    + str(time_available_for_initiate_transmission) + " secs)")
    return False  # function depending on initiate_transmission function will not continue, indicate error


def fan_off():
    """
    Turn OFF the fan of the OPC-N3
    :return: FALSE
    """
    log = "Turning fan OFF"
    logger.debug(log)
    attempts = 1

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x02])
            # cs_high()
            spi.close()  # close the serial port to let it available for another device
            if reading == [0x03]:  # official answer of the OPC-N3
                print("Fan is OFF")
                time.sleep(0.5)  # avoid too close communication (AND let some time to the OPC-N3 to stop the fan)
                return False
            else:
                time.sleep(1)  # let some time to the OPC-N3 (to try to stop the fan)
                reading = read_DAC_power_status('fan')
                if reading == 0:
                    return False
                elif reading == 1:
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
                    logger.warning("Failed to stop the fan, trying again...")
                else:
                    attempts += 1
            if attempts >= 3:
                logger.critical("Failed 3 consecutive times to stop the fan")
                return True
        else:
            logger.critical("Failed to stop the fan (transmission problem)")
            return True


def fan_on():
    """
    Turn ON the fan of the OPC-N3 ON.
    :return: TRUE
    """
    logger.debug("Turning fan on")

    attempts = 1

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x03])
            # cs_high()
            spi.close()
            time.sleep(0.6)  # wait > 600 ms to let the fan start
            if reading == [0x03]:  # official answer of the OPC-N3
                print("Fan is ON")
                time.sleep(0.5)  # avoid too close communication
                return True  # indicate that fan has started
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to start the fan
                reading = read_DAC_power_status('fan')
                if reading == 1:
                    return True  # indicate that fan has started
                elif reading == 0:
                    logger.error("Failed to start the fan...")
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
                else:
                    attempts += 1
            if attempts >= 3:
                log = "Failed 3 times to start the fan"
                logger.critical(log)
                return False  # indicate that fan is OFF
        else:
            logger.critical("Failed to start the fan (transmission problem)")
            return False


def laser_on():
    """
    Turn ON the laser of the OPC-N3.
    :return: TRUE
    """
    logger.debug("Turn the laser ON")
    attempts = 0

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x07])
            # cs_high()
            spi.close()
            if reading == [0x03]:
                print("Laser is ON")
                time.sleep(1)  # avoid too close communication
                return True  # indicate that the laser is ON
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to start the laser
                reading = read_DAC_power_status('laser')
                if reading == 1:
                    logger.info("Wrong answer received after SPI writing, but laser is well on")
                    return True  # indicate that the laser is ON
                elif reading == 0:
                    logger.error("Failed to start the laser, trying again...")
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
            if attempts >= 3:
                logger.critical("Failed 3 times to start the laser")
                return False  # indicate that laser is still off
        else:
            logger.critical("Failed to start the laser (transmission problem)")
            return False


def laser_off():
    """
    Turn the laser of the OPC-N3 OFF.
    :return: FALSE
    """
    logger.debug("Turn the laser OFF")
    attempts = 0

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x06])
            # cs_high()
            spi.close()
            if reading == [0x03]:
                print("Laser is OFF")
                time.sleep(1)  # avoid too close communication
                return False
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to stop the laser
                reading = read_DAC_power_status('laser')
                if reading == 0:
                    logger.info("Wrong answer received after writing, but laser is well off")
                    return False
                elif reading == 1:
                    logger.error("Failed to stop the laser (code returned is " + str(reading) + "), trying again...")
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
            if attempts >= 3:
                logger.critical("Failed 4 times to stop the laser")
                return True  # indicate that laser is still on
        else:
            logger.critical("Failed to stop the laser (transmission problem)")


def read_DAC_power_status(item='all'):
    """
    Read the status of the Digital to Analog Converter as well as the Power Status (TRY TO READ ONLY ONCE)
    :param item: 'fan', 'laser', fanDAC', 'laserDAC', 'laser_switch', 'gain', 'auto_gain_toggle', 'all'
    :return:
    """
    if initiate_transmission(0x13):
        response = spi.xfer([0x13, 0x13, 0x13, 0x13, 0x13, 0x13])
        # cs_high()
        spi.close()
        time.sleep(0.5)  # avoid too close communication

        if item == 'fan':
            logger.debug("DAC power status for " + str(item) + " is " + str(response[0]))
            return response[0]
        elif item == 'laser':
            logger.debug("DAC power status for " + str(item) + " is " + str(response[1]))
            return response[1]
        elif item == 'fanDAC':
            logger.debug("DAC power status for " + str(item) + " is " + str(response[2]))
            response = 1 - (response[2] / 255) * 100  # see documentation concerning fan pot
            logger.info("Fan is running at " + str(response) + "% (0 = slow, 100 = fast)")
            return response
        elif item == 'laserDAC':
            logger.debug("DAC power status for " + str(item) + " is " + str(response[3]))
            response = response[3] / 255 * 100  # see documentation concerning laser pot
            logger.debug("Laser is at " + str(response) + "% of its maximal power")
            return response
        elif item == 'laser_switch':
            logger.debug("DAC power status for " + str(item) + " is " + str(response[4]))
            return response[4]
        elif item == 'gain':
            response = response[5] & 0x01
            logger.debug("DAC power status for " + str(item) + " is " + str(response))
            return response
        elif item == 'auto_gain_toggle':
            response = response[5] & 0x02
            logger.debug("DAC power status for " + str(item) + " is " + str(response))
            return response
        elif item is 'all':
            logger.debug("Full DAC power status is " + str(list(response)))
            return response
        else:
            raise ValueError("Argument of 'read_ADC_power_status' is unknown, check your code!")

    else:
        time.sleep(wait_reset_SPI_buffer)
        return False  # indicate an error


def digest(data):
    """
    Calculate the CRC8 Checksum with the given bytes
    :param data: infinite number of bytes to use to calculate the checksum
    :return: checksum
    """
    crc = 0xFFFF

    for byteCtr in range(0, len(data)):
        to_xor = int(data[byteCtr])
        crc ^= to_xor
        for bit in range(0, 8):
            if (crc & 1) == 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    # log = "Checksum is " + str(crc)
    # logger.debug(log)
    return crc & 0xFFFF


def check(checksum, *data):
    """
    Check that the data received are correct, based on those data and the checksum given
    :param checksum: checksum sent by the sensor (the last byte)
    :param data: all the other bytes sent by the sensor
    :return:
    """
    to_digest = []
    for i in data:
        to_digest.extend(i)
    if digest(to_digest) == join_bytes(checksum):
        log = "Checksum is correct"
        logger.debug(log)
        return True
    else:
        log = "Checksum is wrong"
        logger.debug(log)
        return False


def convert_IEEE754(value):
    value = join_bytes(value)
    answer = struct.unpack('f', bytes(value))
    return answer


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


def PM_reading():
    """
    Read the PM bytes from the OPC-N3 sensor
    Read the data and convert them in readable format, checksum enabled
    Does neither start the fan nor start the laser
    :return: List[PM 1, PM2.5, PM10]
    """
    attempts = 1
    while attempts < 4:
        if initiate_transmission(0x32):
            PM_A = spi.xfer([0x32, 0x32, 0x32, 0x32])
            PM_B = spi.xfer([0x32, 0x32, 0x32, 0x32])
            PM_C = spi.xfer([0x32, 0x32, 0x32, 0x32])
            checksum = spi.xfer([0x32, 0x32])
            spi.close()

            PM1 = round(struct.unpack('f', bytes(PM_A))[0], 3)
            PM25 = round(struct.unpack('f', bytes(PM_B))[0], 3)
            PM10 = round(struct.unpack('f', bytes(PM_C))[0], 3)

            if check(checksum, PM_A, PM_B, PM_C):
                print("PM 1:", PM1, "mg/m3\t|\tPM 2.5:", PM25, "mg/m3\t|\tPM10:", PM10, "mg/m3")
                time.sleep(0.5)  # avoid too close SPI communication
                return [PM1, PM25, PM10]
            if attempts >= 4:
                log = "PM data wrong 3 consecutive times, skipping PM measurement"
                logger.critical(log)
                return ["error", "error", "error"]
            else:
                attempts += 1
                log = "Checksum for PM data is not correct, reading again (" + str(attempts) + "/3)"
                logger.error(log)
                time.sleep(0.5)  # avoid too close SPI communication


def getPM(flushing, sampling_time):
    """
    Get PM measurement from OPC-N3
    :param flushing: time (seconds) during which the fan runs alone to flush the sensor with fresh air
    :param sampling_time: time (seconds) during which the laser reads the particulate matter in the air
    :return: List[PM1, PM2.5, PM10]
    """
    try:
        fan_on()
        time.sleep(flushing)
        laser_on()
        print("Starting sampling")  # will be printed on the same line as "Laser is ON"
        time.sleep(sampling_time)
        PM = PM_reading()

        laser_off()
        fan_off()
    except SystemExit or KeyboardInterrupt:  # to stop the laser and the fan in case of error or shutting down the program
        laser_off()
        fan_off()
        raise
    return PM


def read_histogram(sampling_period):
    """
    Read all the data of the OPC-N3
    :param: flush: time (seconds) during while the fan is running
    :return: Dictionary["PM 1", "PM 2.5", "PM 10", "temperature", "relative humidity", "bin", "MToF", "sampling time",
                  "sample flow rate", "reject count glitch", "reject count longTOF", "reject count ratio",
                  "reject count out of range", "fan revolution count", "laser status"]
    """
    logger.debug("Reading histogram...")

    # Create a dictionary containing data to be returned in case of error
    to_return = {
        "PM 1": "error",
        "PM 2.5": "error",
        "PM 10": "error",
        "temperature": "error",
        "relative humidity": "error",
        "sampling time": "error",
        "sample flow rate": "error",
        "reject count glitch": "error",
        "reject count long TOF": "error",
        "reject count ratio": "error",
        "reject count out of range": "error",
        "fan revolution count": "error",
        "laser status": "error",
        "bin 0": "error",
        "bin 1": "error",
        "bin 2": "error",
        "bin 3": "error",
        "bin 4": "error",
        "bin 5": "error",
        "bin 6": "error",
        "bin 7": "error",
        "bin 8": "error",
        "bin 9": "error",
        "bin 10": "error",
        "bin 11": "error",
        "bin 12": "error",
        "bin 13": "error",
        "bin 14": "error",
        "bin 15": "error",
        "bin 16": "error",
        "bin 17": "error",
        "bin 18": "error",
        "bin 19": "error",
        "bin 20": "error",
        "bin 21": "error",
        "bin 22": "error",
        "bin 23": "error",
        "bin 1 MToF": "error",
        "bin 3 MToF": "error",
        "bin 5 MToF": "error",
        "bin 7 MToF": "error"
    }

    # Delete old histogram data and start a new one
    if initiate_transmission(0x30):
        spi.xfer([0x30] * 86)
        spi.close()
        logger.debug("Old histogram in the OPC-N3 deleted, starting a new one")
    else:
        logger.critical("Failed to initiate histogram, skipping this measurement")
        return to_return  # indicate clearly an error in the data recording

    delay = sampling_period * 2  # you must wait two times the sampling_period in order that
    # the sampling time given by the OPC-N3 respects your sampling time wishes
    # first 5 seconds are with low gain, and the next seconds are with high gain (automatically performed by OPC-N3)

    if not take_new_sample_if_checksum_is_wrong:
        loading_bar('Sampling', delay)

    attempts = 1  # reset the counter for next measurement
    while attempts < 4:
        if take_new_sample_if_checksum_is_wrong:
            loading_bar('Sampling', delay)

        if initiate_transmission(0x30):
            # read all the bytes and store them in a dedicated variable
            bin = spi.xfer([0x30] * 48)
            MToF = spi.xfer([0x30] * 4)
            sampling_time = spi.xfer([0x30] * 2)
            sample_flow_rate = spi.xfer([0x30] * 2)
            temperature = spi.xfer([0x30] * 2)
            relative_humidity = spi.xfer([0x30] * 2)
            PM_A = spi.xfer([0x30] * 4)
            PM_B = spi.xfer([0x30] * 4)
            PM_C = spi.xfer([0x30] * 4)
            reject_count_glitch = spi.xfer([0x30] * 2)
            reject_count_longTOF = spi.xfer([0x30] * 2)
            reject_count_ratio = spi.xfer([0x30] * 2)
            reject_count_Out_Of_Range = spi.xfer([0x30] * 2)
            fan_rev_count = spi.xfer([0x30] * 2)
            laser_status = spi.xfer([0x30] * 2)
            checksum = spi.xfer([0x30] * 2)
            spi.close()

            # check that the data transmitted are correct by comparing the checksums
            if check(checksum, bin, MToF, sampling_time, sample_flow_rate, temperature, relative_humidity,
                     PM_A, PM_B,
                     PM_C, reject_count_glitch, reject_count_longTOF, reject_count_ratio, reject_count_Out_Of_Range,
                     fan_rev_count, laser_status):
                # return TRUE if the data are correct, and execute the below
                # rounding until 2 decimals, as this is the accuracy of the OPC-N3 for PM values
                PM1 = round(struct.unpack('f', bytes(PM_A))[0], 2)
                PM25 = round(struct.unpack('f', bytes(PM_B))[0], 2)
                PM10 = round(struct.unpack('f', bytes(PM_C))[0], 2)
                print("PM 1:\t", PM1, " mg/m3", end="\t\t|\t")
                print("PM 2.5:\t", PM25, " mg/m3", end="\t\t|\t")
                print("PM 10:\t", PM10, " mg/m3")

                relative_humidity = round(100 * (join_bytes(relative_humidity) / (2 ** 16 - 1)), 2)
                temperature = round(-45 + 175 * (join_bytes(temperature) / (2 ** 16 - 1)), 2)  # conversion in °C
                print("Temperature:", temperature, " °C (PCB Board)\t| \tRelative Humidity:", relative_humidity,
                      " %RH (PCB Board)")

                sampling_time = join_bytes(sampling_time) / 100
                print(" Sampling period:", sampling_time, "seconds", end="\t\t|\t")
                sample_flow_rate = join_bytes(sample_flow_rate) / 100
                print(" Sampling flow rate:", sample_flow_rate, "ml/s |", round(sample_flow_rate * 60, 2), "mL/min")

                reject_count_glitch = join_bytes(reject_count_glitch)
                print(" Reject count glitch:", reject_count_glitch, end="\t\t|\t")
                reject_count_longTOF = join_bytes(reject_count_longTOF)
                print(" Reject count long TOF:", reject_count_longTOF)
                reject_count_ratio = join_bytes(reject_count_ratio)
                print(" Reject count ratio:", reject_count_ratio, end="\t\t|\t")
                reject_count_Out_Of_Range = join_bytes(reject_count_Out_Of_Range)
                print(" Reject count Out Of Range:", reject_count_Out_Of_Range)
                fan_rev_count = join_bytes(fan_rev_count)
                print(" Fan revolutions count:", fan_rev_count, end="\t\t|\t")
                laser_status = join_bytes(laser_status)
                print(" Laser status:", laser_status)

                to_return = {
                    "PM 1": PM1,
                    "PM 2.5": PM25,
                    "PM 10": PM10,
                    "temperature": temperature,
                    "relative humidity": relative_humidity,
                    "sampling time": sampling_time,
                    "sample flow rate": sample_flow_rate,
                    "reject count glitch": reject_count_glitch,
                    "reject count long TOF": reject_count_longTOF,
                    "reject count ratio": reject_count_ratio,
                    "reject count out of range": reject_count_Out_Of_Range,
                    "fan revolution count": fan_rev_count,
                    "laser status": laser_status,
                    "bin 0": join_bytes(bin[0:1]),
                    "bin 1": join_bytes(bin[2:3]),
                    "bin 2": join_bytes(bin[4:5]),
                    "bin 3": join_bytes(bin[6:7]),
                    "bin 4": join_bytes(bin[8:9]),
                    "bin 5": join_bytes(bin[10:11]),
                    "bin 6": join_bytes(bin[12:13]),
                    "bin 7": join_bytes(bin[14:15]),
                    "bin 8": join_bytes(bin[16:17]),
                    "bin 9": join_bytes(bin[18:19]),
                    "bin 10": join_bytes(bin[20:21]),
                    "bin 11": join_bytes(bin[22:23]),
                    "bin 12": join_bytes(bin[24:25]),
                    "bin 13": join_bytes(bin[26:27]),
                    "bin 14": join_bytes(bin[28:29]),
                    "bin 15": join_bytes(bin[30:31]),
                    "bin 16": join_bytes(bin[32:33]),
                    "bin 17": join_bytes(bin[34:35]),
                    "bin 18": join_bytes(bin[36:37]),
                    "bin 19": join_bytes(bin[38:39]),
                    "bin 20": join_bytes(bin[40:41]),
                    "bin 21": join_bytes(bin[42:43]),
                    "bin 22": join_bytes(bin[44:45]),
                    "bin 23": join_bytes(bin[46:47]),
                    "bin 1 MToF": MToF[0],
                    "bin 3 MToF": MToF[1],
                    "bin 5 MToF": MToF[2],
                    "bin 7 MToF": MToF[3],
                }

                print(" Bin number:\t", end='')
                for i in range(0, 24):
                    print(to_return["bin " + str(i)], end=", ")
                print("")  # go to next line
                print(" MToF:\t\t", end='')

                for i in range(0, 4):
                    i = (i * 2) + 1
                    print(to_return["bin " + str(i) + " MToF"], end=", ")
                print("")  # go to next line

                if sampling_time > (sampling_period + 0.5):  # we tolerate a difference of 0.5 seconds
                    log = "Sampling period of the sensor was " \
                          + str(round(sampling_time - sampling_period, 2)) + " seconds longer than expected"
                    logger.warning(log)

                elif sampling_time < (sampling_period - 0.5):
                    logger.warning("Sampling period of the sensor was "
                                   + str(round(sampling_period - sampling_time, 2)) + " seconds shorter than expected")

                return to_return

            else:
                # if the function with the checksum return an error (FALSE)
                logger.warning("Error in the data received (wrong checksum), reading histogram again... (" + str(attempts) + "/3)")
                time.sleep(wait_reset_SPI_buffer)  # let some times between two SPI communications
                attempts += 1
        else:
            logger.critical("Failed to read histogram (transmission initiation problem)")
            return to_return

        if attempts >= 3:
            logger.error("Data were wrong 3 times (wrong checksum), skipping this histogram reading")
            return to_return


def getdata(flushing_time, sampling_time):
    """
    Get all the possible data from the OPC-N3 sensor
    :param flushing_time: time during which the ventilator is running, without laser, no sampling
    :param sampling_time: time during which the sensor is sampling
    :return: List[PM1, PM25, PM10, temperature, relative_humidity]
    """
    # return "error" everywhere in case of error during the measurement
    # seacanairy.py need that the dictionary is full of items, if not, python instance will stop
    to_return = {
        "PM 1": "error",
        "PM 2.5": "error",
        "PM 10": "error",
        "temperature": "error",
        "relative humidity": "error",
        "sampling time": "error",
        "sample flow rate": "error",
        "reject count glitch": "error",
        "reject count long TOF": "error",
        "reject count ratio": "error",
        "reject count out of range": "error",
        "fan revolution count": "error",
        "laser status": "error",
        "bin 0": "error",
        "bin 1": "error",
        "bin 2": "error",
        "bin 3": "error",
        "bin 4": "error",
        "bin 5": "error",
        "bin 6": "error",
        "bin 7": "error",
        "bin 8": "error",
        "bin 9": "error",
        "bin 10": "error",
        "bin 11": "error",
        "bin 12": "error",
        "bin 13": "error",
        "bin 14": "error",
        "bin 15": "error",
        "bin 16": "error",
        "bin 17": "error",
        "bin 18": "error",
        "bin 19": "error",
        "bin 20": "error",
        "bin 21": "error",
        "bin 22": "error",
        "bin 23": "error",
        "bin 1 MToF": "error",
        "bin 3 MToF": "error",
        "bin 5 MToF": "error",
        "bin 7 MToF": "error"
    }
    try:  # necessary to put an except condition (see below)
        if fan_on():
            time.sleep(flushing_time/2)
            if laser_on():
                time.sleep(flushing_time/2)
                to_return = read_histogram(sampling_time)
            else:
                logger.critical("Skipping histogram reading")
            laser_off()
        else:
            logger.critical("Skipping histogram reading")
        fan_off()
        return to_return

    except:  # in case of error AND if user stop the software
        print("  ")  # go to the next line
        logger.info("Python instance has been stopped, shutting laser and fan OFF...")
        laser_off()
        fan_off()
        raise


def join_bytes(list_of_bytes):
    """
    Join bytes into an integer, from byte 0 to byte infinite (right to left)
    :param list_of_bytes:list of bytes coming from the spi.readbytes or spi.xfer function
    :return:integer concatenated
    """
    val = 0
    for i in reversed(list_of_bytes):
        val = val << 8 | i
    return val


def set_fan_speed(speed):
    """
    Define the speed of the build in sensor fan
    The goal is to avoid dust formation in the sensor due to high polluted air
    :param speed: number between 0 and 100 (0 = slowest, 100 = fastest)
    :return: nothing
    """
    if speed < 0 or speed > 100:
        raise ValueError("Fan speed of OPC-N3 sensor must be a number between 0 and 100 (0 = slowest, 100 = fastest")
    value = int((45 + speed / 100 * 55) / 100 * 255)
    # Personal investigations shows that the fan don't work below 45%
    # Formula makes a calculation to convert 0% as 45% --> easier for user input
    if initiate_transmission(0x42):
        reading = spi.xfer([0, value])
        logger.info("Fan speed is set on " + str(speed) + " (0 = the slowest, 100 = the fastest)")
    else:
        logger.error("Failed to set the fan speed")


if __name__ == '__main__':
    # The code below runs if you execute this code from this file (you must execute OPC-N3 and not seacanairy)
    while True:
        logger.debug("Code is running from the OPC-N3 file itself, debug messages shown")
        print("Fan on 0")
        set_fan_speed(0)
        time.sleep(2)
        fan_on()
        time.sleep(3)
        fan_off()
        print("Fan on 100")
        set_fan_speed(100)
        time.sleep(2)
        fan_on()
        time.sleep(3)
        fan_off()
        # answer = getdata(OPC_flushing_time, OPC_sampling_time)
        # print(answer)
        # print("waiting 10 seconds...")
        time.sleep(2)
