from Start_to_tshirp import

#data file location
fdel = open("/home/pi/Desktop/Tshirp.odt", "w")
# om file mee te beginnen
fdel.write(" ")

#open condition to keep the system running
while (True):
    #open the file to write the data
    f = open("Tshirp.rtf", "a")