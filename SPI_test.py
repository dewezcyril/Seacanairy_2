import spidev
import time

bus = 0  # name of the SPI bus on the Raspberry Pi 3B+
device = 0  # name of the SS (Ship Selection) pin used for the OPC-N3
spi = spidev.SpiDev()  # enable SPI (SPI must be enable in the RPi settings beforehand)
spi.open(bus, device)
spi.max_speed_hz = 400000  # 750 kHz
spi.mode = 0b01  # bytes(0b01) = int(1) --> SPI mode 1

to_print = []

for i in range(200):
    to_print.append(i)


def test():
    print("testing SPI")
    spi.open(0, 0)  # open the serial port
    response = spi.xfer(to_print)
    print(response)
    spi.close()
    return response
