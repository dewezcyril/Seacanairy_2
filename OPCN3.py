"""
Library for the use and operation of Alphasense OPC-N3 sensor
"""

import spidev
import time
import struct
import datetime
import sys
import os.path
from progress.bar import IncrementalBar
# import RPi.GPIO as GPIO

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
import logging


if __name__ == '__main__':
    # If you run the code from this file directly, it will show all the DEBUG messages
    message_level = logging.DEBUG
    log_file = '/home/pi/seacanairy_project/log/OPCN3-debug.log'
    # define a Handler which writes INFO messages or higher to the sys.stderr/display
    console = logging.StreamHandler()
    console.setLevel(message_level)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)

else:
    # If you run this code from another file (using this one as a library), it will only print INFO messages
    message_level = logging.INFO
    log_file = '/home/pi/seacanairy_project/log/seacanairy.log'


# set up logging to file - see previous section for more details
logging.basicConfig(level=message_level,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',
                    filename=log_file,
                    filemode='a')

logger = logging.getLogger('OPC-N3')

# ----------------------------------------------
# SPI CONFIGURATION
# ----------------------------------------------

bus = 0  # name of the SPI bus on the Raspberry Pi 3B+
device = 0  # name of the SS (Ship Selection) pin used for the OPC-N3
spi = spidev.SpiDev()  # enable SPI
spi.open(bus, device)
spi.max_speed_hz = 400000  # 750 kHz
spi.mode = 0b01  # bytes(0b01) = int(1) --> SPI mode 1
# first bit (from right) = CPHA = 0 --> data are valid when clock is rising
# second bit (from right) = CPOL = 0 --> clock is kept low when idle
wait_10_milli = 0.015  # 15 ms
wait_10_micro = 1e-06
wait_reset_SPI_buffer = 3  # seconds
time_available_for_initiate_transmission = 10  # seconds


# CS (chip selection) manually via GPIO
# GPIO.setmode(GPIO.BCM)  # use the GPIO names (GPIO1...) instead of the processor pin name (BCM...)
# CS = 25
# GPIO.setup(CS, GPIO.OUT, initial=GPIO.HIGH)


def cs_high(delay=0.010):
    """Close communication with OPC-N3 by setting CS on HIGH"""
    time.sleep(delay)
    # GPIO.output(CS, GPIO.HIGH)
    # time.sleep(delay)


def cs_low(delay=0.010):
    """Open communication with OPC-N3 by setting CS on LOW"""
    time.sleep(delay)
    # GPIO.output(CS, GPIO.LOW)
    # time.sleep(delay)


# ----------------------------------------------
# OPC-N3 variables
# ----------------------------------------------


def initiate_transmission(command_byte):
    """
    Initiate SPI transmission to the OPC-N3
    First loop of the Flow Chart
    :return: TRUE when power state has been initiated
    """
    attempts = 0  # sensor is busy loop
    cycle = 0  # SPI buffer reset loop (going to the right on the flowchart)

    log = "Initiate transmission with command byte " + str(command_byte)
    logger.debug(log)

    stop = time.time() + time_available_for_initiate_transmission

    spi.open(0, 0)
    # cs_low()

    while time.time() < stop:
        reading = spi.xfer([command_byte])  # initiate control of power state

        if reading == [243]:  # SPI ready = 0xF3
            time.sleep(wait_10_micro)
            return True  # if function wll continue working once true is returned

        if reading == [49]:  # SPI busy = 0x31
            time.sleep(wait_10_micro)
            attempts += 1

        elif reading == [230] or reading == [99] or reading == [0]:
            cycle += 1
            log = "Problem with the SS (Slave Select) line (error code " + str(hex(reading[0])) + ")"
            logger.critical(log)
            log = "Check that SS line is well kept DOWN (0V) during transmission. " \
                  "Try again by connecting SS Line of sensor to Ground"
            logger.debug(log)
            time.sleep(wait_reset_SPI_buffer)
            log = "Trying again..."
            logger.info(log)

        else:
            log = "Failed to initiate transmission (unexpected code returned: " + str(hex(reading[0])) + ")"
            logger.critical(log)
            time.sleep(1)  # wait 1e-05 before next command
            attempts += 1  # increment of attempts

        if attempts > 60:
            log = "Failed 60 times to initiate control of power state, reset OPC-N3 SPI buffer"
            logger.error(log)
            # cs_high()
            time.sleep(wait_reset_SPI_buffer)  # time for spi buffer to reset

            log = "Trying again..."
            logger.info(log)
            attempts = 0  # reset the "SPI busy" loop
            cycle += 1  # increment of the SPI reset loop
            # cs_low()

        if cycle >= 2:
            log = "Failed to initiate transmission (reset 3 times SPI, still error)"
            logger.critical(log)
            return False  # function depending on initiate_transmission function will not continue

    if time.time() > stop:
        log = "Transmission initiation took too much time (> " + str(time_available_for_initiate_transmission) + " secs)"
        logger.critical(log)
        return False  # function depending on initiate_transmission function will not continue


def fan_off():
    """
    Turn OFF the fan of the OPC-N3.
    :return: FALSE
    """
    log = "Turning fan OFF"
    logger.debug(log)
    attempts = 0

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x02])
            # cs_high()
            spi.close()
            if reading == [0x03]:
                print("Fan is OFF")
                time.sleep(1)  # avoid too close communication
                return False
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to stop the fan
                reading = read_DAC_power_status('fan')
                if reading == 0:
                    log = "Wrong answer received after SPI writing, but fan is well OFF"
                    logger.info(log)
                    return False
                elif reading == 1:
                    log = "Failed to stop the fan"
                    logger.error(log)
                    attempts += 1
                    time.sleep(3)
                    log = "Trying again to stop the fan..."
                    logger.info(log)

    if attempts >= 3:
        log = "Failed 3 times to stop the fan"
        logger.critical(log)


def fan_on():
    """
    Turn ON the fan of the OPC-N3 ON.
    :return: TRUE
    """
    log = "Turning fan on"
    logger.debug(log)

    attempts = 0

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x03])
            # cs_high()
            spi.close()
            time.sleep(0.6)  # wait > 600 ms to let the fan start
            if reading == [0x03]:
                print("Fan is ON")
                time.sleep(1)  # avoid too close communication
                return True
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to start the fan
                reading = read_DAC_power_status('fan')
                if reading == 1:
                    log = "Wrong answer received after SPI writing, but fan is well ON"
                    logger.info(log)
                    return True
                elif reading == 0:
                    log = "Failed to start the fan"
                    logger.error(log)
                    attempts += 1
                    time.sleep(3)
                    log = "Trying again to start the fan..."
                    logger.info(log)

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
    log = "Turn the laser ON"
    logger.debug(log)
    attempts = 0

    while attempts < 4:
        if initiate_transmission(0x03):
            reading = spi.xfer([0x07])
            # cs_high()
            spi.close()
            if reading == [0x03]:
                print("Laser is ON")
                time.sleep(1)  # avoid too close communication
                return True
            else:
                time.sleep(1)  # let time to the OPC-N3 to try to start the laser
                reading = read_DAC_power_status('laser')
                if reading == 1:
                    log = "Wrong answer received after SPI writing, but laser is well ON"
                    logger.info(log)
                    return True
                elif reading == 0:
                    log = "Failed to start the laser"
                    logger.error(log)
                    attempts += 1
                    time.sleep(wait_reset_SPI_buffer)
                    log = "Trying again to start laser..."
                    logger.info(log)

        if attempts >= 3:
            log = "Failed 3 times to start the laser"
            logger.critical(log)
            return False  # indicate that laser is still off


def laser_off():
    """
    Turn the laser of the OPC-N3 OFF.
    :return: FALSE
    """
    log = "Turn the laser OFF"
    logger.debug(log)
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
                    log = "Wrong answer received after writing, but laser is well off"
                    logger.info(log)
                    return False
                elif reading == 1:
                    log = "Failed to stop the laser (code returned is " + str(reading) + ")"
                    logger.error(log)
                    attempts += 1
                    time.sleep(3)
                    log = "Trying again to stop laser..."
                    logger.info(log)

        if attempts >= 3:
            log = "Failed 4 times to stop the laser"
            logger.critical(log)
            return True  # indicate that laser is still on


def read_DAC_power_status(item=None):
    """
    Read the status of the Digital to Analog Converter as well as the Power Status
    :param item: 'fan', 'laser', fanDAC', 'laserDAC', 'laser_switch', 'gain', 'auto_gain_toggle'
    :return:
    """
    if initiate_transmission(0x13):
        response = spi.xfer([0x13, 0x13, 0x13, 0x13, 0x13, 0x13])
        # cs_high()
        spi.close()
        time.sleep(0.5)  # avoid too close communication

        if item == 'fan':
            log = "DAC power status for " + str(item) + " is " + str(response[0])
            logger.debug(log)
            return response[0]
        elif item == 'laser':
            log = "DAC power status for " + str(item) + " is " + str(response[1])
            logger.debug(log)
            return response[1]
        elif item == 'fanDAC':
            log = "DAC power status for " + str(item) + " is " + str(response[2])
            logger.debug(log)
            response = 1 - (response[2] / 255) * 100  # see documentation concerning fan pot
            log = "Fan is running at " + str(response) + "% (0 = slow, 100 = fast)"
            logger.info(log)
            return response
        elif item == 'laserDAC':
            log = "DAC power status for " + str(item) + " is " + str(response[3])
            logger.debug(log)
            response = response[3] / 255 * 100  # see documentation concerning laser pot
            log = "Laser is shining at " + str(response) + "%"
            logger.debug(log)
            return response
        elif item == 'laser_switch':
            log = "DAC power status for " + str(item) + " is " + str(response[4])
            logger.debug(log)
            return response[4]
        elif item == 'gain':
            response = response[5] & 0x01
            log = "DAC power status for " + str(item) + " is " + str(response)
            logger.debug(log)
            return response
        elif item == 'auto_gain_toggle':
            response = response[5] & 0x02
            log = "DAC power status for " + str(item) + " is " + str(response)
            logger.debug(log)
            return response
        elif item is None:
            log = "Full DAC power status is " + str(response)
            logger.debug(log)
            print(log)
            return response
        else:
            raise ValueError("Argument of 'read_ADC_power_status' is unknown, check your code!")

    else:
        time.sleep(wait_reset_SPI_buffer + 1)
        return 255


def digest(data):
    """
    Calculate the CRC8 Checksum
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
    while True:
        if initiate_transmission(0x30):
            spi.xfer([0x30] * 86)
            spi.close()
            log = "Old histogram in the OPC-N3 deleted, start a new one"
            logger.debug(log)
            break  # histogram measurement has been initiated, proceeding to
        if attempts < 3:
            attempts += 1
            log = "Failed to initiate histogram, trying again (" + str(attempts) + "/3)"
            logger.error(log)
            time.sleep(wait_reset_SPI_buffer)
        if attempts >= 3:
            log = "Failed 3 times to initiate histogram, skipping this measurement"
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
        time.sleep(flushing_time/2)
        if laser_on():
            time.sleep(flushing_time/2)
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


if __name__ == '__main__':
    # The code below runs if you execute this code from this file (you must execute OPC-N3 and not seacanairy)
    logger.info("Code is running from the OPC-N3 file itself, debug messages shown")
    getdata(2, 5)
