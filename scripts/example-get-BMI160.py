from time import sleep
from BMI160_i2c import Driver

print('Trying to initialize the sensor...')
sensor = Driver(0x69)  # change address if needed
print('Initialization done')

while True:
    data = sensor.getMotion6()
    # If all values are zero, assume something went wrong and try reinitializing.
    if all(val == 0 for val in data):
        print("Warning: Sensor returned all zeros. Reinitializing sensor...")
        sensor = Driver(0x69)
    else:
        print({
            'gx': data[0],
            'gy': data[1],
            'gz': data[2],
            'ax': data[3],
            'ay': data[4],
            'az': data[5]
        })
    # Increase the delay to at least 1 second to prevent I2C issues.
    sleep(0.01)
