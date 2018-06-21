import machine
from machine import I2C
from machine import ADC
from network import LoRa
import time
import binascii
import pycom
import socket

#MCP9808 High Accuracy I2C Temperature Sensor address
address = 24
reg = 5
adc = machine.ADC(0)
result = bytearray(2)


def temp_c(data):
    value = data[0] << 8 | data[1]
    temp = (value & 0xFFF) / 16.0
    if value & 0x1000:
        temp -= 256.0
    return temp

def battery():
    adcread  = adc.channel(attn=3, pin='P16')
    samplesADC = [0.0]*numADCreadings; meanADC = 0.0
    count = 0
    while (count < numADCreadings):
        adcint = adcread()
        samplesADC[count] = adcint
        meanADC += adcint
        count += 1
    meanADC /= numADCreadings
    varianceADC = 0.0
    for adcint in samplesADC:
        varianceADC += (adcint - meanADC)**2
    varianceADC /= (numADCreadings - 1)
    mV = meanADC*1400/1024
    return mV

pycom.heartbeat(False) #needs to be disabled for LED functions to work
pycom.rgbled(0x0f0000) #red

#Set AppEUI and AppKey - use your values from the device settings --> https://console.thethingsnetwork.org/
dev_eui = binascii.unhexlify('xxxxxxxxxxxxxxxx')
app_eui = binascii.unhexlify('xxxxxxxxxxxxxxxx')
app_key = binascii.unhexlify('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

#Set LoRa to Australia ready to reset the channels
lora = LoRa(mode=LoRa.LORAWAN, public=1,  adr=0, tx_retries=0, region=LoRa.AU915)

# Remove default channels
for index in range(0, 72):
    lora.remove_channel(index)

# Set  AU ISM 915 channel plan for TTN Australia
for index in range(0, 7):
    lora.add_channel(index, frequency=923300000+index*600000, dr_min=0, dr_max=3)

for index in range(8, 15):
    lora.add_channel(index, frequency=915200000+index*200000, dr_min=0, dr_max=3)

lora.add_channel(65, frequency=917500000,  dr_min=4,  dr_max=4)

#Join TTN Network via OTAA
lora.join(activation=LoRa.OTAA, auth=(dev_eui, app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    pycom.rgbled(0x0f0f00) #yellow
    time.sleep(5)
    print('Trying to join TTN Network!')
    pass

print('Network joined!')
pycom.rgbled(0x000f00) #green

#setup i2c internface
i2c = I2C(0, I2C.MASTER, baudrate=100000)

# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# set the LoRaWAN data rate
s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)

while lora.has_joined():
    pycom.rgbled(0x00000f) #blue
    i2c.readfrom_mem_into(address, reg, result) #Read I2C temperature
    temperature = temp_c(result)
    voltage = battery() #Read ADC battery voltage
    #Convert to HEX words
    tempbytes    = bytes(array.array('f', [temperature]))
    voltagebytes = bytes(array.array('f', [voltage]))
    print(temperature)
    print(voltage)
    time.sleep(1)
    pycom.heartbeat(False)
    time.sleep(5)
    s.setblocking(True)
    #Send both HEX words in one message
    s.send(bytes([tempbytes[0],tempbytes[1],tempbytes[2],tempbytes[3],voltagebytes[0],voltagebytes[1],voltagebytes[2],voltagebytes[3]]))
    s.setblocking(False)
    time.sleep(5)
