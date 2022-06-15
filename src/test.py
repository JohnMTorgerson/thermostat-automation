# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import adafruit_dht
import datetime

# Initial the dht device, with data pin connected to:
# dhtDevice = adafruit_dht.DHT11(board.D4)

# you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
# This may be necessary on a Linux single board computer like the Raspberry Pi,
# but it will not work in CircuitPython.
dhtDevice = adafruit_dht.DHT11(board.D4, use_pulseio=False)

data_path = "../data.txt"

tryAgain = True

while tryAgain:
    try:
        now = datetime.datetime.now()
        #print(now)

        # Print the values to the serial port
        temperature_c = dhtDevice.temperature
        temperature_f = round(temperature_c * (9 / 5) + 32,1)
        humidity = round(dhtDevice.humidity,1)
        #print(
        #    "Temp: {:.1f} F / {:.1f} C    Humidity: {}% ".format(
        #        temperature_f, temperature_c, humidity
        #    )
        #)
        print(f"{now} temp: {temperature_f}° hum: {humidity}%")
        
        try:
            # check if new value is different from last recorded value
            with open(data_path, "r") as f:
                last_line = f.readlines()[-1].split()
        except Exception as error:
            last_line = [-1,-1,-1]
            print(f"Error: {error}")

        try:
            if float(last_line[1]) != temperature_f or abs(float(last_line[2]) - humidity) > 1:
                #print(last_line)
                #print(float(last_line[1]))
                #print(float(last_line[2]))
                print("different!!!!")

                with open(data_path, "a") as f:
                    f.write(f"{int(now.timestamp())} {temperature_f} {humidity} ({now})\n")
                
        except ValueError as error:
            # if a line doesn't follow the format, (we might have added a comment), then ignore that and write a new line
            with open(data_path, "a") as f:
                f.write(f"{int(now.timestamp())} {temperature_f} {humidity} ({now})\n")

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        time.sleep(1.0)
        continue
    except TypeError as error:
        print(f"No values: {error.args[0]}")
        time.sleep(3.0)
        continue
    except Exception as error:
        dhtDevice.exit()
        raise error

    tryAgain = False
