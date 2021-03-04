"""
Translation from C++ to Python of the CRC8 example from TUG_EE894_I2C.pdf page 7 and 8
"""

POLY = 0x31
START = 0xFF


def calc_CRC8(buf):
    crcVal = START
    _from = 0
    _to = len(buf)
    for i in range(_from, _to):
        curVal = buf[i]
        print(hex(curVal))

        for j in range(1, 8):
            if ((crcVal ^ curVal) & 0x80) != 0:
                crcVal = (crcVal << 1) ^ POLY

            else:
                crcVal = (crcVal << 1)
            curVal = (curVal << 1)

    return crcVal


answer = calc_CRC8([0x00, 0xC8])
print("CRC8 calculation is: ", hex(answer))
