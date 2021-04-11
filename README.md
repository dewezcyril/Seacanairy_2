# Progression of my work
`CO2.py`, `OPCN3.py` and `GPS.py` are working good.
**Currently working on the whole `seacanairy.py` file

# Description of the different files

* **`CO2.py`**: retrieving the data from [E+E Elektronik EE894 CO2 sensor](https://www.epluse.com/en/products/co2-measurement/co2-sensor/ee894/)
* **`OPCN3.py`**: retrieving the data from the [Alphasense PM OPC-N3 sensor](http://www.alphasense.com/index.php/products/optical-particle-counter/)*
* **`Start_to_tshirp.py`**: code to retrieve the voltage of a [4 sensors AFE board from Alphasense](http://www.alphasense.com/index.php/products/support-circuits-air/), measured by a [Pi-16ADC](https://alchemy-power.com/pi-16adc/), made by another student
* **`AFE.py`**: adaptation of the previous code for use via functions
* **`seacanairy.py`**: final code launching the functions inside the other python files
* **`seacanairy_settings.yaml`**: file containing the settings for the other files
* **`GPS.py`**: code to get the position, time, speed, COG, from the [U-BLOX-7 GNSS module](https://www.u-blox.com/sites/default/files/products/documents/NEO-7_DataSheet_%28UBX-13003830%29.pdf).
 Convert the NMEA serial lines to longitude, latitude, time, date...
* _**`draft.py`**: draft document where ideas and non-used part of code are stored_

_Other files are no more used_
# Link to the official documentation
### E+E Elektronik EE894 CO2 sensor
Use an I2C interface
* [Utilising the E2 Interface for EE894 - AN1808-1 (296.53 kb)](https://www.epluse.com/fileadmin/data/product/ee894/Utilising_E2_Interface_EE894_AN1808-1.pdf)
* [E2 interface specification (223.84 kb)](https://www.epluse.com/fileadmin/data/sw/Specification_E2_Interface.pdf)
* [Protocol Description I²C (1252.75 kb)](https://www.epluse.com/fileadmin/data/product/ee894/TUG_EE894_I2C.pdf)
### OPC-N3 - Alphasense
Use a SPI interface (spidev)
* [Sensor description](https://www.alphasense.com/WEB1213/wp-content/uploads/2019/03/OPC-N3.pdf)
* [Operational manual (072-0502)](https://ivobruggeoffice-my.sharepoint.com/:b:/g/personal/cyril_dewez_365_academicoffice_be/EYyBUtyGxQ9DhEx4IhtOQtYBmjt7fF_uCiN_a-y78fQx6g?e=KNGjmR)
* [Supplemental SPI information (072-0503)](https://ivobruggeoffice-my.sharepoint.com/:b:/g/personal/cyril_dewez_365_academicoffice_be/EZ0sC9YRnJtDk1bBb0wdnWEBJRDpJhDoEhiawHT7dnBjEA?e=U0VCsF)
### U-BLOX-7 GNSS module
Use the UART interface (pyserial) 
* [Velleman GPS Board](https://www.velleman.eu/products/view?id=439218&country=us&lang=fr)
* [Datasheet](https://www.u-blox.com/sites/default/files/products/documents/NEO-6_DataSheet_(GPS.G6-HW-09005).pdf)
* [Receiver description, including protocol specifications](https://www.u-blox.com/en/ubx-viewer/view/u-blox7-V14_ReceiverDescriptionProtocolSpec_(GPS.G7-SW-12001)_Public?url=https%3A%2F%2Fwww.u-blox.com%2Fsites%2Fdefault%2Ffiles%2Fproducts%2Fdocuments%2Fu-blox7-V14_ReceiverDescriptionProtocolSpec_%2528GPS.G7-SW-12001%2529_Public.pdf)
# About me

Cyril Dewez,
21 years old,
Student in Master year at the Antwerp Maritime Academy (Belgium),
dewezcyril@gmail.com