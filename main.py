from Start_to_tshirp import AFE_reading as ADC

# ----------------------------------------------------------------------------------------------------------------------
# logging
# ----------------------------------------------------------------------------------------------------------------------
log_file = './log/seacanairy2.log'
logging.basicConfig(filename=log_file, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)





#data file location
fdel = open("/home/pi/Desktop/Tshirp.odt", "w")
# om file mee te beginnen
fdel.write(" ")

#open condition to keep the system running
while (True):
    #open the file to write the data
    f = open("Tshirp.rtf", "a")

