import ftd2xx as ftd

device_serial = ftd.listDevices(0)
device_desc = ftd.listDevices(2)

print(device_serial)
print(device_desc)

filtered_serials = [serial.decode() for serial, desc in zip(device_serial, device_desc) if desc == b'Digilent USB Device A']

# 결과 출력
print(filtered_serials)