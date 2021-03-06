"""
Translation from C++ to Python of the CRC8 example from TUG_EE894_I2C.pdf page 7 and 8
Pure Python
"""

POLY = 0x31
START = 0xFF


def calc_CRC8(*data):
    buf = list(data)
    print(buf)
    crcVal = START
    _from = 0  # the first item in a list is named 0
    _to = len(buf)  # if there are two items in the list, then len() return 1 --> range(0, 1) = 2 loops

    for i in range(_from, _to):
        curVal = buf[i]
        print("[i loop] Step", i, "with data", hex(curVal))  # to check that the loop is ok

        for j in range(0, 8):  # C++ stops when J is not < 8 --> same for python in range
            if ((crcVal ^ curVal) & 0x80) != 0:
                crcVal = (crcVal << 1) ^ POLY
                print("* [j loop] Step", j, "\if")

            else:
                crcVal = (crcVal << 1)
                print("* [j LOOP] Step", j, "\else")

            curVal = (curVal << 1)  # this line is in the "for j" loop, not in the "for i" loop

    return crcVal


answer = calc_CRC8(0x03, 0xFF, 0x22, 0x80, 0x00, 0x00, 0x00, 0x27, 0x94) & 0xff
print("CRC8 calculation is:", hex(answer))
