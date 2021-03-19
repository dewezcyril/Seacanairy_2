"""
Library for the use and operation of Alphasense OPC-N3 sensor.
Inspired and adapted from the library of JarvisSan22 available on Github: https://github.com/JarvisSan22/OPC-N3_python

Submitted to LICENCE due to the Git Clone
"""

import spidev
import time
import struct
import datetime
import sys
import os.path
# import RPi.GPIO as GPIO

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
import logging

log_file = '/home/pi/seacanairy_project/log/seacanairy.log'

if __name__ == '__main__':
    message_level = logging.DEBUG
    # If you run the code from this file directly, it will show all the DEBUG messages

else:
    message_level = logging.INFO
    # If you run this code from another file (using this one as a library), it will only print INFO messages

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
wait_reset_SPI_buffer = 3  # 3 seconds
time_for_initiate_transmission = 30


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

    stop = time.time() + time_for_initiate_transmission

    spi.open(0, 0)
    # cs_low()

    while time.time() < stop:
        reading = spi.xfer([command_byte])  # initiate control of power state

        if reading == [243]:  # SPI ready = 0xF3
            time.sleep(wait_10_micro)
            return True  # if function wll continue working once true is returned

        if reading == [49]:  # SPI busy = 0x31
            attempts += 1

        elif reading == [230] or reading == [99] or reading == [0]:
            attempts += 2  # this is big error, if it occurs, then there are lot of chance if will not work anymore
            log = "Problem with the SS (Slave Select) line (error code " + str(reading) + ")"
            logger.critical(log)
            log = "Check that SS line is well kept DOWN (0V) during transmission. " \
                  "Try again by connecting SS Line of sensor to Ground"
            logger.debug(log)
            time.sleep(wait_reset_SPI_buffer)
            log = "Trying again..."
            logger.info(log)

        else:
            log = "Failed to initiate transmission (unexpected code returned: " + str(reading) + ")"
            logger.critical(log)
            time.sleep(1)  # wait 1e-05 before next command
            attempts += 1  # increment of attempts

        if attempts > 60:
            log = "Failed 60 times to initiate control of power state, reset OPC-N3 SPI buffer"
            logger.critical(log)
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
        log = "Transmission initiation took too much time (> " + str(time_for_initiate_transmission) + " secs)"
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
                print("PM 1:", PM1, "mg/m3 | PM 2.5:", PM25, "mg/m3 | PM10:", PM10, "mg/m3")
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


def read_histogram(timestamp):
    """
    Read histogram of the OPC-N3
    :param: flush: time (seconds) during while the fan is running
    :return:
    """
    # Delete old histogram data and start a new one
    attempts = 1
    while True:
        if initiate_transmission(0x30):
            spi.xfer([0x30] * 86)
            spi.close()
            log = "Old histogram in the OPC-N3 deleted, starting a new one"
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

    delay = timestamp * 2  # you must wait two times the timestamp in order that
    # the sampling time given by the OPC-N3 respects your sampling time wishes
    time.sleep(delay)  # sampling time of this histogram

    attempts = 1  # reset the counter for next measurement
    try:
        while attempts < 4:
            if initiate_transmission(0x30):
                unused = spi.xfer([0x30] * 48)
                MToF = spi.xfer([0x30] * 4)
                sampling_period = spi.xfer([0x30] * 2)
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

                if check(checksum, unused, MToF, sampling_period, sample_flow_rate, temperature, relative_humidity,
                         PM_A, PM_B,
                         PM_C, reject_count_glitch, reject_count_longTOF, reject_count_ratio, reject_count_Out_Of_Range,
                         fan_rev_count, laser_status):
                    # this means that the data are correct, they can be processed and printed
                    PM1 = round(struct.unpack('f', bytes(PM_A))[0], 3)
                    PM25 = round(struct.unpack('f', bytes(PM_B))[0], 3)
                    PM10 = round(struct.unpack('f', bytes(PM_C))[0], 3)
                    print("PM 1:", PM1, "mg/m3 | PM 2.5:", PM25, "mg/m3 | PM10:", PM10, "mg/m3")

                    relative_humidity = round(100 * (join_bytes(relative_humidity) / (2 ** 16 - 1)), 2)
                    temperature = round(-45 + 175 * (join_bytes(temperature) / (2 ** 16 - 1)), 2)  # conversion in °C
                    print("Temperature:", temperature, "| Relative Humidity:", relative_humidity)

                    sampling_period = join_bytes(sampling_period) / 100
                    print("Sampling period:", sampling_period, "seconds")
                    sample_flow_rate = join_bytes(sample_flow_rate) / 100
                    print("Sampling flow rate:", sample_flow_rate, "ml/s |", round(sample_flow_rate * 60 / 1000, 2),
                          "L/min")

                    reject_count_glitch = join_bytes(reject_count_glitch)
                    print("Reject count glitch:", reject_count_glitch)
                    reject_count_longTOF = join_bytes(reject_count_longTOF)
                    print("Reject count long TOF:", reject_count_longTOF)
                    reject_count_ratio = join_bytes(reject_count_ratio)
                    print("Reject count ratio:", reject_count_ratio)
                    reject_count_Out_Of_Range = join_bytes(reject_count_Out_Of_Range)
                    print("Reject count Out Of Range:", reject_count_Out_Of_Range)
                    fan_rev_count = join_bytes(fan_rev_count)
                    print("Fan revolutions count:", fan_rev_count)
                    laser_status = join_bytes(laser_status)
                    print("Laser status:", laser_status)

                    print("MToF:", MToF)

                    print("Unused bytes:")
                    for i in range(0, 24):
                        x = 2 * i
                        y = x + 1
                        answer = join_bytes(unused[x:y])
                        print(answer, ", ", end='')
                    print("")  # so that newt console printing will go to the next line
                    return

                else:
                    log = "Checksum is wrong, trying again to read the histogram (" + str(attempts) + "/3)"
                    logger.error(log)
                    time.sleep(wait_reset_SPI_buffer)  # let some times between two SPI communications
                    attempts += 1

        if attempts >= 3:
            log = "Checksum was wrong 3 times, skipping this histogram reading"
            logger.critical(log)
            return

    except SystemExit or KeyboardInterrupt:  # to stop the laser and the fan in case of error or shutting down the program
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


def RHcon(ans):
    # ans is  combine_bytes(ans[52],ans[53])
    RH = 100 * (ans / (2 ** 16 - 1))
    return RH


def Tempcon(ans):
    # ans is  combine_bytes(ans[52],ans[53])
    Temp = -45 + 175 * (ans / (2 ** 16 - 1))
    return Temp


def combine_bytes(LSB, MSB):
    return (MSB << 8) | LSB


def Histdata(ans):
    """
    Create a dictionary of all the bytes read.
    :param ans: chain of bytes to proceed
    :return:Dictionary of all the possible data read
    """

    data = {}
    data['Bin 0'] = combine_bytes(ans[0], ans[1])
    data['Bin 1'] = combine_bytes(ans[2], ans[3])
    data['Bin 2'] = combine_bytes(ans[4], ans[5])
    data['Bin 3'] = combine_bytes(ans[6], ans[7])
    data['Bin 4'] = combine_bytes(ans[8], ans[9])
    data['Bin 5'] = combine_bytes(ans[10], ans[11])
    data['Bin 6'] = combine_bytes(ans[12], ans[13])
    data['Bin 7'] = combine_bytes(ans[14], ans[15])
    data['Bin 8'] = combine_bytes(ans[16], ans[17])
    data['Bin 9'] = combine_bytes(ans[18], ans[19])
    data['Bin 10'] = combine_bytes(ans[20], ans[21])
    data['Bin 11'] = combine_bytes(ans[22], ans[23])
    data['Bin 12'] = combine_bytes(ans[24], ans[25])
    data['Bin 13'] = combine_bytes(ans[26], ans[27])
    data['Bin 14'] = combine_bytes(ans[28], ans[29])
    data['Bin 15'] = combine_bytes(ans[30], ans[31])
    data['Bin 16'] = combine_bytes(ans[32], ans[33])
    data['Bin 17'] = combine_bytes(ans[34], ans[35])
    data['Bin 18'] = combine_bytes(ans[36], ans[37])
    data['Bin 19'] = combine_bytes(ans[38], ans[39])
    data['Bin 20'] = combine_bytes(ans[40], ans[41])
    data['Bin 21'] = combine_bytes(ans[42], ans[43])
    data['Bin 22'] = combine_bytes(ans[44], ans[45])
    data['Bin 23'] = combine_bytes(ans[46], ans[47])
    data['Bin 24'] = combine_bytes(ans[48], ans[49])
    data['period'] = combine_bytes(ans[52], ans[53])
    data['FlowRate'] = combine_bytes(ans[54], ans[55])
    data['Temp'] = Tempcon(combine_bytes(ans[56], ans[57]))
    data['RH'] = RHcon(combine_bytes(ans[58], ans[59]))
    data['pm1'] = struct.unpack('f', bytes(ans[60:64]))[0]
    data['pm2.5'] = struct.unpack('f', bytes(ans[64:68]))[0]
    data['pm10'] = struct.unpack('f', bytes(ans[68:72]))[0]
    data['Check'] = combine_bytes(ans[84], ans[85])

    #  print(data)
    return (data)


def read_all(port, chunk_size=86):
    """Read all characters on the serial port of the OPC-N3 and return them."""
    #    if not port.timeout:
    #        raise TypeError('Port needs to have a timeout set!')

    read_buffer = b''

    while True:
        # Read in chunks. Each chunk will wait as long as specified by
        # timeout. Increase chunk_size to fail quicker
        byte_chunk = spi.readbytes(size=chunk_size)
        print("read_all loop")
        # read_buffer += byte_chunk
        if not len(byte_chunk) == chunk_size:
            break

    return read_buffer


def filter_data(response):
    """
    Get ride of the 0x61 byte response from the hist data, returning just the wanted data
    :return:Data cleaned of unnecessary bytes
    """
    hist_response = []
    for j, k in enumerate(response):  # Each of the 86 bytes we expect to be returned is prefixed by 0xFF.
        if ((j + 1) % 2) == 0:  # Throw away 0th, 2nd, 4th, 6th bytes, etc.
            hist_response.append(k)
    return hist_response


def getData():
    """
    Read the 86 bytes of data from the OPC-N3 sensor.
    :return: List of 3 items
    """
    print("Get PM data")
    T = 0

    while True:
        # initsiate getData commnad
        if initiate_transmission(0x32):
            # write to the OPC
            for i in range(14):  # Send the whole stream of bytes at once.
                spi.writebytes([0x61, 0x01])
                time.sleep(0.00001)
                # time.sleep(.1)
            # read the data
            ans = bytearray(ser.readall())
            # print("ans=",ans)
            ans = filter_data(ans)
            # print("ans=",ans)
            b1 = ans[0:4]
            b2 = ans[4:8]
            b3 = ans[8:12]
            c1 = struct.unpack('f', bytes(b1))[0]
            c2 = struct.unpack('f', bytes(b2))[0]
            c3 = struct.unpack('f', bytes(b3))[0]
            check = combine_bytes(ans[12], ans[13])
            print("Check=", check)
            return [c1, c2, c3]


def getHist():
    """
    Get Histogram data from OPC-N3.
    :return: Dictionary containing the data
    """
    # OPC N2 method
    T = 0  # attemt varaible

    while True:
        log = "get hist"
        logger.debug(log)

        if initiate_transmission(0x30):
            log = "Reading Hist data"
            logger.debug(log)

            for i in range(86):  # Send the whole stream of bytes at once.
                spi.writebytes([0x61, 0x01])
                time.sleep(0.000001)

            # ans=bytearray(ser.read(1))
            #    print("ans=",ans,"len",len(ans))
            time.sleep(wait_10_micro)  # delay
            ans = bytearray(ser.readall())
            print("ans=", ans, "len", len(ans))
            ans = filter_data(ans)  # get the wanted data bytes
            # ans=bytearray(test)

            log = "ans = " + str(ans) + ", len = " + str(len(ans))
            logger.info(log)
            # print("test=",test,'len',len(test))
            data = Histdata(ans)

            return data


def getmeasurement():
    """
    Start the fan_status, the laser, get measurement, stop the laser and stop de fan_status.
    :return: Measurements
    """
    initiate()
    initiate_transmission()
    time.sleep(1)
    fan_on()
    time.sleep(5)
    laser_on()
    for x in range(0, 1):
        print(getData())
        time.sleep(1)
        print(getHist())
        time.sleep(5)
    fan_off()
    time.sleep(.1)
    laser_off()
    time.sleep(.1)
    ser.close()
    return


if __name__ == '__main__':
    fan_on()
    time.sleep(2)
    laser_on()

    read_histogram(5)

    laser_off()
    fan_off()
