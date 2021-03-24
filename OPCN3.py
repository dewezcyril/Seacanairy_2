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

    # The following HANDLER must be activated ONLY if you run this code alone
    # Without the 'if __name__ == '__main__' condition, all the logging messages are displayed 3 TIMES
    # (once for the handler in CO2.py, once for the handler in OPCN3.py, and once for the handler in seacanairy.py)

    # define a Handler which writes INFO messages or higher to the sys.stderr/display
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)
else:  # if this file is considered as a library (if you execute seacanairy.py for example)
    # it will only print and store INFO messages in the corresponding log_file
    message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/seacanairy.log'  # complete location needed on the RPI

    # no need to add a handler, because there is already one in seacanairy.py

# set up logging to file
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%d-%m %H:%M:%S',
                    filename=log_file,
                    filemode='a')

logger = logging.getLogger('OPC-N3')  # name of the logger
# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as ROOT and NOT 'OPC-N3'

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
            # during developping, I noticed that those were the value read while having this kind of issue
            # this comes from personal investigation and not from the official documentation
            logger.critical("Problem with the SS (Slave Select) line "
                            "(error code " + str(hex(reading[0])) + "), Trying again...")
            cycle += 1
            logger.debug("Check that SS line is well kept DOWN (0V) during transmission."
                         " Try again by connecting SS Line of sensor to Ground")
            time.sleep(wait_reset_SPI_buffer)
            return False

        else:
            logger.critical("Failed to initiate transmission (unexpected code returned: " + str(hex(reading[0])) + ")")
            time.sleep(1)  # wait 1e-05 before next command
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
                    logger.warning("Wrong answer received after SPI writing, but fan is well OFF")
                    return False
                elif reading == 1:
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
                    logger.warning("Failed to stop the fan, trying again...")
        else:
            attempts += 1
        if attempts >= 3:
            logger.critical("Failed 3 times to stop the fan")
            return


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
                    logger.warning("Wrong answer received after SPI writing, but fan is well ON")
                    return True  # indicate that fan has started
                elif reading == 0:
                    logger.error("Failed to start the fan")
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
        else:
            attempts += 1
        if attempts >= 3:
            log = "Failed 3 times to start the fan"
            logger.critical(log)
            return False  # indicate that fan is OFF


def laser_on():
    """
    Turn ON the laser of the OPC-N3.
    :param: end_of_print_message: (optional) to concatenate the print messages on a same line on the console
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
        else:
            attempts += 1
        if attempts >= 3:
            logger.critical("Failed 3 times to start the laser")
            return False  # indicate that laser is still off


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
        else:
            attempts += 1
        if attempts >= 3:
            logger.critical("Failed 4 times to stop the laser")
            return True  # indicate that laser is still on


def read_DAC_power_status(item='all'):
    """
    Read the status of the Digital to Analog Converter as well as the Power Status
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
        logger.error(log)
        return False


def convert_IEEE754(value):
    value = join_bytes(value)
    answer = struct.unpack('f', bytes(value))
    return answer


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
                return [-255, -255, -255]
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
    :return: List[PM1, PM25, PM10, temperature, relative_humidity]
    """
    # Delete old histogram data and start a new one
    attempts = 1

    logger.debug("Reading histogram...")

    if initiate_transmission(0x30):
        spi.xfer([0x30] * 86)
        spi.close()
        log = "Old histogram in the OPC-N3 deleted, start a new one"
        logger.debug(log)
    else:
        log = "Failed to initiate histogram, skipping this measurement"
        logger.critical(log)
        return

    delay = sampling_period * 2  # you must wait two times the sampling_period in order that
    # the sampling time given by the OPC-N3 respects your sampling time wishes
    bar = IncrementalBar('Sampling', max=(2 * delay), suffix='%(elapsed)s/' + str(delay) + ' seconds')
    for i in range(0, 2 * delay):
        time.sleep(0.5)
        bar.next()

    bar.finish()

    attempts = 1  # reset the counter for next measurement
    try:
        while attempts < 4:
            if initiate_transmission(0x30):
                unused = spi.xfer([0x30] * 48)
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

                if check(checksum, unused, MToF, sampling_time, sample_flow_rate, temperature, relative_humidity,
                         PM_A, PM_B,
                         PM_C, reject_count_glitch, reject_count_longTOF, reject_count_ratio, reject_count_Out_Of_Range,
                         fan_rev_count, laser_status):
                    # this means that the data are correct, they can be processed and printed
                    # rounding until 2 decimals, as this is the accuracy of the OPC-N3 for PM values
                    PM1 = round(struct.unpack('f', bytes(PM_A))[0], 2)
                    PM25 = round(struct.unpack('f', bytes(PM_B))[0], 2)
                    PM10 = round(struct.unpack('f', bytes(PM_C))[0], 2)
                    print("PM 1:\t", PM1, " mg/m3", end = "\t\t|\t")
                    print("PM 2.5:\t", PM25, " mg/m3", end = "\t\t|\t")
                    print("PM 10:\t", PM10, " mg/m3")

                    relative_humidity = round(100 * (join_bytes(relative_humidity) / (2 ** 16 - 1)), 2)
                    temperature = round(-45 + 175 * (join_bytes(temperature) / (2 ** 16 - 1)), 2)  # conversion in °C
                    print("Temperature:", temperature, " °C (PCB Board)\t| \tRelative Humidity:", relative_humidity, " %RH (PCB Board)")

                    sampling_time = join_bytes(sampling_time) / 100
                    print(" Sampling period:", sampling_time, "seconds", end="\t\t|\t")
                    sample_flow_rate = join_bytes(sample_flow_rate) / 100
                    print(" Sampling flow rate:", sample_flow_rate, "ml/s |", round(sample_flow_rate * 60 / 1000, 2),"L/min")

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

                    print(" Bin number:\t", end='')
                    for i in range(0, 24):
                        x = 2 * i
                        y = x + 1
                        answer = join_bytes(unused[x:y])
                        print(answer, end=", ")
                    print("")  # go to next line
                    print(" MToF:\t\t", end='')
                    for i in range(0, 4):
                        print(MToF[i], end=", ")
                    print("")  # go to next line

                    if sampling_time > (sampling_period + 0.5):  # we tolerate a difference of 0.5 seconds
                        log = "Sampling period of the sensor was " + str(round(sampling_time - sampling_period, 2)) + " seconds longer than expected"
                        logger.info(log)

                    elif sampling_time < (sampling_period - 0.5):
                        logger.info("Sampling period of the sensor was " + str(round(sampling_period - sampling_time, 2)) + " seconds shorter than expected")

                    return [PM1, PM25, PM10, temperature, relative_humidity]

                else:
                    log = "Checksum is wrong, trying again to read the histogram (" + str(attempts) + "/3)"
                    logger.error(log)
                    time.sleep(wait_reset_SPI_buffer)  # let some times between two SPI communications
                    attempts += 1
            if attempts >= 3:
                log = "Checksum was wrong 3 times, skipping this histogram reading"
                logger.critical(log)
                return [-255, -255, -255, -255, -255]

    except SystemExit or KeyboardInterrupt:  # to stop the laser and the fan in case of error or shutting down the program
        log = "Stopping Python instance during measurement, stopping laser and fan"
        logger.info(log)
        laser_off()
        fan_off()
        raise


def getdata(flushing_time, sampling_time):
    """
    Get all the possible data from the OPC-N3 sensor
    :param flushing_time: time during which the ventilator is running, without laser, no sampling
    :param sampling_time: time during which the sensor is sampling
    :return: List[PM1, PM25, PM10, temperature, relative_humidity]
    """
    data = [-255, -255, -255, -255, -255]
    if fan_on():
        time.sleep(flushing_time)
        if laser_on():
            data = read_histogram(sampling_time)
        laser_off()
    fan_off()
    return data


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


if __name__ == '__name__':
    # The code below runs if you execute this code from this file (you must execute OPC-N3 and not seacanairy)
    logger.debug("Code is running from the OPC-N3 file itself, debug messages shown")
    print(message_level)
    getdata(2, 5)
    print("waiting...")
    time.sleep(10)
