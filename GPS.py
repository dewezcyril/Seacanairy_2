import serial  # install libraries
import time
import yaml
import logging
import RPi.GPIO as GPIO
import sys
import os.path

# --------------------------------------------------------
# YAML SETTINGS
# --------------------------------------------------------

# Get current directory
current_working_directory = str(os.getcwd())

with open(current_working_directory + '/seacanairy_settings.yaml') as file:
    settings = yaml.safe_load(file)
    file.close()

store_debug_messages = settings['GPS']['Store debug messages (important increase of logs)']

project_name = settings['Seacanairy settings']['Sampling session name']

# --------------------------------------------------------
# LOGGING SETTINGS
# --------------------------------------------------------
# all the settings and other code for the logging
# logging = tak a trace of some messages in a file to be reviewed afterward (check for errors fe)

def set_logger(message_level, log_file):
    # set up logging to file
    logging.basicConfig(level=message_level,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%d-%m %H:%M',
                        filename=log_file,
                        filemode='a')

    logger = logging.getLogger('GPS')  # name of the logger
    # all further logging must be called by logger.'level' and not logging.'level'
    # if not, the logging will be displayed as 'ROOT' and NOT 'OPC-N3'
    return logger


if __name__ == '__main__':  # if you run this code directly ($ python3 CO2.py)
    message_level = logging.DEBUG  # show ALL the logging messages
    # Create a file to store the log if it doesn't exist
    log_file = current_working_directory + "/log/GPS-debugging.log"
    if not os.path.isfile(log_file):
        os.mknod(log_file)
    print("GPS DEBUG messages will be shown and stored in '" + str(log_file) + "'")
    logger = set_logger(message_level, log_file)
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
    log_file = '/home/pi/seacanairy_project/log/' + project_name + '-log.log'  # complete location needed on the RPI
    # no need to add a handler, because there is already one in seacanairy.py
    logger = set_logger(message_level, log_file)


# all further logging must be called by logger.'level' and not logging.'level'
# if not, the logging will be displayed as 'ROOT' and NOT 'GPS'


# --------------------------------------------------------
# GPIO SETTINGS
# --------------------------------------------------------
#
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(25, GPIO.OUT, initial=GPIO.LOW, pull_up_down=GPIO.PUD_DOWN)
# GPIO.output(25, GPIO.LOW)


# def pulse():
# GPIO.output(25, GPIO.HIGH)
# time.sleep(.2)
# GPIO.output(25, GPIO.LOW)


def get_raw_reading():
    """
    Get raw GPS reading via UART
    :return:
    """
    port = '/dev/ttyAMA0'
    try:
        # USB = '/dev/ttyACM0'
        # PL011 = '/dev/serial0' == '/dev/ttyAMA0'
        logger.debug("Port used for UART communication is: " + str(port))
        ser = serial.Serial(port=port, baudrate=9600)
        print("Starting UART communication...", end='\r')
        time.sleep(1)
        ser.flush()
        try:
            ser.read_all()  # delete all corrupted data
            ser.flush()  # flush the buffer
            time.sleep(1)
            reading = ser.read_all()
            ser.close()
        except:
            logger.critical("Failed to read GPS data on UART port " + str(port) + " (" + str(sys.exc_info()) + ")")
            return False  # indicate error
    except:
        logger.critical("Failed to initiate UART port " + str(port) + " (" + str(sys.exc_info()) + ")")
        return False  # indicate error

    reading = str(reading, 'utf-8', errors='replace')  # convert the text sent in b'...' format into readable format...
    # it will also skip the line where the GPS propose it (see NMEA protocol)
    # 'replace' = replace the unencodable unicode to a question mark
    logger.debug("Raw reading is:\r" + str(reading[:-1]))
    return reading


def lat_long_decode(raw_position, compas):
    """
    Decode longitude and latitude data from NMEA
    :param raw_position: raw longitude/latitude word
    :param compas: compas (N/S/W/E)
    :return: decoded latitude/longitude
    """
    position = raw_position.split(".")
    min = position[0][-2:]
    min_dec = position[1]
    deg = position[0][0:-2]
    position = deg + '°' + min + "." + min_dec + "' " + compas
    return position


def decode_NMEA(data):
    """
    Decode the NMEA script and get useful data
    :param data: whole string returned by the GPS (all the lines of the NMEA)
    :return: dictionary (fix time, latitude, longitude, SOG, COG, status, horizontal precision, altitude,
    WGS84 correction, UTC, fix status)
    """
    data = data.split("\r\n")  # create a list of lines (\r\n is sent by the sensor at the end of each line)
    to_return = {
        "fix time": "unknown",
        "latitude": "unknown",
        "longitude": "unknown",
        "SOG": "unknown",
        "COG": "unknown",
        "status": "unknown",
        "horizontal precision": "unknown",
        "altitude": "unknown",
        "WGS84 correction": "unknown",
        "UTC": "unknown",
        "fix status": "unknown"
    }  # you must return all those items to avoid bugs in seacanairy.py (f-e looking for an item which doesn't exist)
    for i in range(len(data)):  # don't know at which line data will be send, so it will search for the good line
        print(data[i], end='              \r')
        time.sleep(.2)  # let a bit of time for the user to see the data returned by the GPS
        print("                                                                                          ", end='\r')
        if data[i][0:6] == "$GPRMC":
            if check(data[i]):
                GPRMC = data[i].split(",")
                if GPRMC[2] == "V":  # indicate that GPS is not working good
                    logger.warning("GPS does not receive signal")
                    status = "NOK"
                    to_return.update({"status": status})
                    return to_return
                if GPRMC[2] == "A":  # indicate that GPS is working fine
                    fix_time = GPRMC[1][0:2] + ":" + GPRMC[1][2:4] + ":" + GPRMC[1][4:6] + " UTC"
                    status = "OK"
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
                UTC = GPGGA[1][0:2] + ":" + GPGGA[1][2:4] + ":" + GPGGA[1][4:6] + " UTC"
                altitude = GPGGA[9] + " " + GPGGA[10]
                WGS84_correction = GPGGA[11] + " " + GPGGA[12]
                position_fix_status_indicator = GPGGA[6]
                if position_fix_status_indicator == '0':
                    fix_status = "No fix/invalid"
                elif position_fix_status_indicator == '1':
                    fix_status = "Standard GPS 2D/3D"
                elif position_fix_status_indicator == '2':
                    fix_status = "DGPS"
                elif position_fix_status_indicator == '6':
                    fix_status = "DR"
                else:
                    logger.error(
                        "Unknown position fix status indicator in GPGGA: " + str(position_fix_status_indicator))
                    fix_status = "Unknown: " + str(position_fix_status_indicator)

                to_return.update({
                    "altitude": altitude,
                    "WGS84 correction": WGS84_correction,
                    "fix status": fix_status,
                    "UTC": UTC
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
    :return:    Dictionary(fix time, latitude, longitude, SOG, COG, status,
                horizontal precision, altitude, WGS84 correction)
    """
    logger.debug("Get position")
    reading = get_raw_reading()

    if not reading:
        logger.critical("Failed to retrieve GPS data")
        to_return = {
            "fix time": "unknown",
            "latitude": "unknown",
            "longitude": "unknown",
            "SOG": "unknown",
            "COG": "unknown",
            "status": "unknown",
            "horizontal precision": "unknown",
            "altitude": "unknown",
            "WGS84 correction": "unknown",
            "UTC": "unknown",
            "fix status": "unknown"
        }
        return to_return

    data = decode_NMEA(reading)
    print("Current time:\t", data["UTC"])
    print("Latitude:\t", data["latitude"], "\t|\tLongitude:\t", data["longitude"])
    print("SOG:\t\t", data["SOG"], "\t\t|\tCOG:\t", end='')
    if data["COG"] == '':
        print("none")
    else:
        print(data["COG"])
    print("Status:\t", data["status"])
    return data


if __name__ == '__main__':
    pos = get_position()
    print(pos)
