import serial  # install libraries
import time
import yaml
import logging

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------

with open('/home/pi/seacanairy_project/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

store_debug_messages = settings['GPS']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
# all the settings and other code for the logging
# logging = tak a trace of some messages in a file to be reviewed afterward (check for errors fe)

if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    log_file = '/home/pi/seacanairy_project/log/GPS-debug.log'  # complete file location required for the Raspberry
    print("GPS DEBUG messages will be shown and stored in '" + str(log_file) + "'")

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

logger = logging.getLogger('GPS')  # name of the logger


# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as 'ROOT' and NOT 'GPS'


def get_raw_reading():
    """
    Get raw GPS reading via UART
    :return:
    """
    try:
        ser = serial.Serial("/dev/serial0", 9600)
        time.sleep(1)
        ser.flush()
        try:
            reading = ser.read_all()
            reading = str(reading, 'utf-8')  # convert the text sent in b'...' format into readable format...
            # it will also skip the line where the GPS propose it
            logger.debug("Raw reading is:")
            logger.debug(reading)
            ser.close()  # close the UART port to avoid problem and unecessary buffer filling
            return reading
        except:
            logger.critical("Failed to read GPS data on UART port")
            return False
    except:
        logger.critical("Failed to initiate UART port for GPS")
        return False


def lat_long_decode(raw_position, compas):
    """
    Decode longitude and latitude data
    :param raw_position: raw longitude/latitude word
    :param compas: compas (N/S/W/E)
    :return: decoded latitude/longitude
    """
    position = raw_position.split(".")
    min = position[0][-2:]
    min_dec = position[1]
    deg = position[0][0:-2]
    position = deg + "°" + min + "." + min_dec + "' " + compas
    return position


def clean_data(data):
    """
    Clean the data returned by the GPS and extract useful data
    :param data: whole string returned by the GPS
    :return: dictionary
    """
    data = data.split("\r\n")  # create a list of lines (\r\n is sent by the sensor at the end of each line)
    to_return = {
        "fix time": "error",
        "latitude": "error",
        "longitude": "error",
        "SOG": "error",
        "COG": "error",
        "status": "error",
        "horizontal precision": "error",
        "altitude": "error",
        "WGS84 correction": "error"
    }  # you must return all those items to avoid bugs in seacanairy.py (f-e looking for an item which doesn't exist)
    for i in range(len(data)):  # don't know at which line data will be send, so it will search for the good line
        if data[i][0:6] == "$GPRMC":
            if check(data[i]):
                GPRMC = data[i].split(",")
                if GPRMC[2] == "V":  # indicate that GPS is not working good
                    logger.warning("GPS does not receive signal")
                    return False
                elif GPRMC[2] == "A":  # indicate that GPS is working fine
                    fix_time = GPRMC[1][0:2] + ":" + GPRMC[1][2:4] + ":" + GPRMC[1][4:6] + " GMT"
                    status = GPRMC[2]
                    latitude = lat_long_decode(GPRMC[3], GPRMC[4])
                    longitude = lat_long_decode(GPRMC[5], GPRMC[6])
                    SOG = GPRMC[7]
                    COG = GPRMC[8]

                    to_return.update({
                        "fix time": fix_time,
                        "latitude": latitude,
                        "longitude": longitude,
                        "SOG": SOG,
                        "COG": COG,
                        "status": status
                    })

                    logger.debug("GPRMC data is:")
                    logger.debug(str(to_return))

                else:
                    logger.critical("Something wrong with the GPRMC data, GPS satus returned is: " + str(GPRMC[2]))

        elif data[i][0:6] == "&GPGSA":
            if check(data[i]):
                GPGSA = data[i].split(",")
                horizontal_precision = GPGSA[-1]

                to_return.update({
                    "horizontal precision": horizontal_precision
                })

        elif data[i][0:6] == "$GPGGA":
            if check(data[i]):
                GPGGA = data[i].split(",")
                altitude = GPGGA[9] + " " + GPGGA[10]
                WGS84_correction = GPGGA[11] + " " + GPGGA[12]

                to_return.update({
                    "altitude": altitude,
                    "WGS84 correction": WGS84_correction
                })
    logger.debug("GPS reading is:" + str(to_return))
    return to_return


def digest(string_line):
    """
    Calculate the checksum based on the transmitted data
    COPY-PASTED AND ADAPTED FROM WIKIPEDIA
    :param NMEAstring: line of data transmitted by the GPS
    :return:
    """
    calc_cksum = 0
    NMEAstring = string_line[1:-3]
    for s in NMEAstring:
        # it is XOR of ech Unicode integer representation
        calc_cksum ^= ord(s)

    calc_cksum = str(hex(calc_cksum))[2:]  # get hex representation
    calc_cksum = calc_cksum.upper()
    return calc_cksum


def check(NMEAstring):
    """
    Check that the data transmitted are correct
    :param NMEAstring: line of data transmitted by the GPS
    :param checksum: checksum returned by the
    :return: True (data are corrects), False (data are not corrects)
    """
    calc = digest(NMEAstring)
    checksum = NMEAstring[-2:]
    if calc == checksum:
        logger.debug("Checksum is correct")
        return True
    else:
        logger.debug("Checksum is not correct")
        logger.debug("Calculation is" + str(calc) + "| sensor's checksum is" + str(checksum))
        return False


def get_position():
    """
    Get position and all other data from the GPS
    :return:
    """
    logger.debug("Get position")
    reading = get_raw_reading()
    data = clean_data(reading)  # if GPS does not receive signal,
    logger.debug(data)
    return data


while True:
    pos = get_position()
    print(pos)
    time.sleep(5)
