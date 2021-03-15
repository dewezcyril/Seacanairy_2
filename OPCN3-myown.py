import spidev
import time
import struct
import datetime

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
# SPI CONFIGURATION
# ----------------------------------------------

bus = 0  # name of the SPI bus on the Raspberry Pi 3B+
device = 0  # name of the SS (Ship Selection) pin used for the OPC-N3
spi = spidev.SpiDev()  # enable SPI
spi.open(bus, device)
spi.max_speed_hz = 300000  # 750 kHz
spi.mode = 0b01
# first bit (from right) = CPHA = 0 --> data are valid when clock is rising
# seco,d bit (from right) = CPOL = 0 --> clock is kept low when idle

delay_after_command_byte = 0.015  # 15 ms (> 10 ms and < 100 ms)
delay_between_communications = 0.000015  # 15 mus (> 10 mus and < 100 mus)

# ----------------------------------------------
# OPC-N3 variables
# ----------------------------------------------
SPI_OPC_ready = [0xF3]
SPI_OPC_busy = [0x31]


# ----------------------------------------------

def GetReadyResponse(SPIcommand):
    """Check that the OPC-N3 is ready to communicate via SPI"""
    response = spi.xfer(SPIcommand)  # try reading a byte to clear out anything remnant of SD Card activity
    time.sleep(0.001)  # wait 1 ms
    print("First response is", response)
    tries = 0
    while (response != SPI_OPC_ready):
        while (tries < 20) and (response != SPI_OPC_ready):
            response = spi.xfer(SPIcommand)
            print(response, end='')
            if response != SPI_OPC_ready:
                time.sleep(0.001)  # wait 1 ms
            tries += 1

        if response != SPI_OPC_ready:
            if response == SPI_OPC_busy:
                print("OPC-N3 busy, waiting 2 seconds")
                time.sleep(2)
            else:
                spi.close()
                time.sleep(6)
                spi.open(bus, device)

        if tries >= 20:
            print("failed")
            break

    time.sleep(0.01)  # wait 10 ms
    print("OPC is ready")


def initiate_power_state_control():
    """
    Send 0x03 to the sensor
    First step of the flow chart
    :return: True when the sensor is ready
    """
    log = "Initiate power control"
    logger.debug(log)
    msg = [0x61, 0x03]
    attempts = 0
    busy = 0
    while busy < 20 and attempts < 4:
        log = "Sending " + str(msg) + " via SPI"
        logger.debug(log)
        spi.xfer2(msg)  # does return nothing
        time.sleep(delay_between_communications)
        answer2 = spi.readbytes(10)
        if answer2[0] == 0xF3 or answer2[0] == 0xF3:
            time.sleep(delay_between_communications)
            return True
        elif answer2[0] == 0x31:
            print("Sensor is busy. Trying again in 1 second")
            busy += 1
            time.sleep(delay_after_command_byte)
        else:
            log = "Unknown error code returned: " + str(answer2) + ". Trying again in 3 seconds"
            logger.critical(log)
            attempts += 1
            time.sleep(3)  # wait minimum 2 seconds so that the OPC-N3 understand somethg is going wrong

        if attempts >= 3:
            log = "Failed 3 consecutive time to initiate power control"
            logger.critical(log)
            return False


GetReadyResponse([0x03])


# if initiate_power_state_control():
#     print("Power state initiation succeeded")
# else:
#     print("Failed to initiate control of power state")


spi.close()
print("SPI closed")
