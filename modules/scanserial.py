import ftd2xx as ftd

serial = "210276BA00C3A"


device_serial = ftd.listDevices(0)
device_desc = ftd.listDevices(2)

print(device_serial)
print(device_desc)


serial = serial.encode('ascii')
filtered_serials = [serial.decode() for serial, desc in zip(device_serial, device_desc) if desc == b'Digilent USB Device A']

i = 0
for finds in device_serial:
    if serial in finds: break
    else: i+=1

print(i)
print(device_serial[i])
print(device_desc[i])
