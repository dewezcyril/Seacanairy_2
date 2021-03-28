# Progression of my work
_CO2.py_ is working good and very accurate.

**Currently** working on the OPC-N3 sensor
# Description of the different files

* **CO2.py**: retrieving the data from [E+E Elektronik EE894 CO2 sensor](https://www.epluse.com/en/products/co2-measurement/co2-sensor/ee894/)
* **OPCN3.py**: code imported from an [online example](https://github.com/JarvisSan22/OPC-N3_python), to retrieve the data from the [Alphasense PM OPC-N3 sensor](http://www.alphasense.com/index.php/products/optical-particle-counter/)*
* **OPCN3-spidev**: adaptation of the previous file found on GitHub. Use of spidev function instead of Serial
* **Start_to_tshirp.py**: code to retrieve the voltage of a [4 sensors AFE board from Alphasense](http://www.alphasense.com/index.php/products/support-circuits-air/), measured by a [Pi-16ADC](https://alchemy-power.com/pi-16adc/)
* **ADC and 4-AFE Board.py**: adaptation of the previous code for use via functions
* **seacanairy.py**: final code launching the functions inside the other python files
* **seacanairy_settings.yaml**: file containing the settings for the other files
* _**draft.py**: draft document where ideas and non-used part of code are stored_
# Link to the official documentation
### E+E Elektronik EE894 CO2 sensor
* [Utilising the E2 Interface for EE894 - AN1808-1 (296.53 kb)](https://www.epluse.com/fileadmin/data/product/ee894/Utilising_E2_Interface_EE894_AN1808-1.pdf)
* [E2 interface specification (223.84 kb)](https://www.epluse.com/fileadmin/data/sw/Specification_E2_Interface.pdf)
* [Protocol Description I²C (1252.75 kb)](https://www.epluse.com/fileadmin/data/product/ee894/TUG_EE894_I2C.pdf)
### OPC-N3 - Alphasense
* [Sensor description](https://www.alphasense.com/WEB1213/wp-content/uploads/2019/03/OPC-N3.pdf)
* [Operational manual (072-0502)](https://ivobruggeoffice-my.sharepoint.com/:b:/g/personal/cyril_dewez_365_academicoffice_be/EYyBUtyGxQ9DhEx4IhtOQtYBmjt7fF_uCiN_a-y78fQx6g?e=KNGjmR)
* [Supplemental SPI information (072-0503)](https://ivobruggeoffice-my.sharepoint.com/:b:/g/personal/cyril_dewez_365_academicoffice_be/EZ0sC9YRnJtDk1bBb0wdnWEBJRDpJhDoEhiawHT7dnBjEA?e=U0VCsF)
# About me

Cyril Dewez,
21 years old,
Student in Master year at the Antwerp Maritime Academy (Belgium).
dewezcyril@gmail.com