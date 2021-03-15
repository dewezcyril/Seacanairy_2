"""
Library for the use and operation of Alphasense OPC-N3 sensor.
Inspired and adapted from the library of JarvisSan22 available on Github: https://github.com/JarvisSan22/OPC-N3_python

Submitted to LICENCE due to the Git Clone
"""

from serial import Serial
import time
import struct
import datetime
import sys
import os.path

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
import logging

log_file = './log/OPC-N3.log'

if __name__ == '__main__':
    message_level = logging.DEBUG
    # If you run the code from this file directly, it will show all the DEBUG messages

else:
    message_level = logging.INFO
    # If you run this code from another file (using this one as a library), it will only print INFO messages

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

logger = logging.getLogger('OPC-N3')

# ----------------------------------------------
# SPI config
# ----------------------------------------------

logfile = "OPC-N3"
SPI_address_RPI = "/dev/ttyAMA0"  # name of the SPI of the RPI
wait = 1e-06

# ----------------------------------------------
# VARIABLE
# ----------------------------------------------


ser = Serial(
    port=SPI_address_RPI,
    baudrate=9600,
    parity='N',
    stopbits=1,
    bytesize=8,
    xonxoff=False,
    timeout=wait
)

print("Serial port used is: ", ser.name)

power = 0x03
histogram = 0x30


def initiate():
    """
    Initiate the SPI communication to the OPC-N3 sensor.
    :return: nothing
    """

    log = "Initiate the SPI communication of the OPC-N3"
    logger.debug(log)

    time.sleep(1)
    log = "Sending bytes to the sensor..."
    logger.debug(log)
    ser.write(bytearray([0x5A, 0x01]))
    reading = ser.read(3)
    log = "Data read after sending bytes are: " + str(reading)
    logger.debug(log)
    time.sleep(wait)

    log = "Sending bytes to the sensor..."
    logger.debug(log)
    ser.write(bytearray([0x5A, 0x03]))
    reading = ser.read(9)
    log = "Bytes read after sending bytes are: " + str(reading)
    logger.debug(log)
    time.sleep(wait)

    # SPI conncetion
    log = "Sending bytes to the sensor..."
    logger.debug(log)
    ser.write(bytearray([0x5A, 0x02, 0x92, 0x07]))
    reading = ser.read(2)
    log = "Bytes read after sending bytes are: " + str(reading)
    logger.debug(log)
    time.sleep(wait)

    return


def initiate_transmission(write=0x03):
    """
    First step of the OPC-N3 SPI communication
    :return: TRUE when power state has been initiated
    """
    attempts = 0  # Flowchart time reset

    log = "Initiate transmission"
    logger.debug(log)

    while True:
        log = "Sending " + str(write) + " bytes"
        logger.debug(log)
        ser.write(bytearray([0x61, write]))  # Initiate control of power state
        reading = ser.read(2)
        log = "Reading is: " + str(reading)
        # print(reading)
        attempts += 1  # increment of attempts

        if reading == (b'\xff\xf3' or b'xf3\xff'):
            log = "Acknowledge byte received"
            logger.debug(log)
            time.sleep(wait)
            return True

        elif attempts > 20:
            log = "Failed to initiate power control. Wiring may not be correct."
            logger.error(log)
            time.sleep(3)  # time for spi buffer to reset
            # reset SPI  connection
            # initOPC(ser)
            attempts = 0
            return False

        else:
            time.sleep(wait * 10)  # wait 1e-05 before next command
            log = "Wait before initiating new attempt"
            logger.debug(log)


def fanOff():
    """
    Turn OFF the fan_status of the OPC-N3.
    :return: FALSE
    """
    log = "Turning fan_status OFF"
    logger.debug(log)

    if initiate_transmission():
        ser.write(bytearray([0x61, 0x02]))
        reading = ser.read(2)
        #      print(reading)
        time.sleep(2)
        log = "Fan off"
        logger.info(log)
        return False


def fanOn():
    """
    Turn fan_status of the OPC-N3 ON.
    :return: TRUE
    """
    log = "Turning fan_status on"
    logger.debug(log)

    if initiate_transmission():
        ser.write(bytearray([0x61, 0x03]))
        nl = ser.read(2)
        #        print(nl)
        time.sleep(2)
        log = "Fan is On"
        logger.info(log)
        return True


def LaserOn():
    """
    Turn the laser of the OPC-N3 ON.
    :return: TRUE
    """
    log = "Turning laser ON"
    logger.debug(log)

    if initiate_transmission():
        # Lazer on
        ser.write(bytearray([0x61, 0x07]))
        nl = ser.read(2)
        #          print(nl)
        time.sleep(wait)
        log = "Laser is ON"
        logger.info(log)
        return True


def LaserOff():
    """
    Turn the laser of the OPC-N3 OFF.
    :return: FALSE
    """
    print("Laser Off")

    if initiate_transmission():
        ser.write(bytearray([0x61, 0x06]))
        nl = ser.read(2)
        #            print(nl)
        time.sleep(wait)
        log = "Laser is Off"
        logger.info(log)
        return False


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
    if not port.timeout:
        raise TypeError('Port needs to have a timeout set!')

    read_buffer = b''

    while True:
        # Read in chunks. Each chunk will wait as long as specified by
        # timeout. Increase chunk_size to fail quicker
        byte_chunk = port.read(size=chunk_size)
        read_buffer += byte_chunk
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
                ser.write([0x61, 0x01])
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
                ser.write([0x61, 0x01])
                time.sleep(0.000001)

            # ans=bytearray(ser.read(1))
            #    print("ans=",ans,"len",len(ans))
            time.sleep(wait)  # delay
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
    time.sleep(1)
    fanOn()
    time.sleep(5)
    LaserOn()
    for x in range(0, 1):
        print(getData())
        time.sleep(1)
        print(getHist())
        time.sleep(5)
    fanOff()
    time.sleep(.1)
    LaserOff()
    time.sleep(.1)
    ser.close()
    return


if __name__ == "__main__":
    while True:
        getmeasurement()
        time.sleep(5)
