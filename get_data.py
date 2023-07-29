import logging
import os
import inspect
import pathlib
print(pathlib.Path().absolute())
import time
import json
import datetime
from pprint import pprint
import re
# import estimate_abs_hum

# create logger
logger = logging.getLogger(f"HA.{__name__}")

# actual path of the script's directory, regardless of where it's being called from
path_ = os.path.dirname(inspect.getabsfile(inspect.currentframe()))

weather_data_filepath = f"{path_}/data/weather_data.json"
sensor_data_filepath = f"{path_}/data/data.txt"

# get current temp and humidity values from sensors
def get_current(log=True) :
    import board

    # no longer using DHT11 sensor; using analog sensor for temp, and AHT20 for humidity, as they are both more accurate
    # # ========================================
    # # get values from DHT sensor (digital sensor, does both temp and humidity) ====== #
    # import board
    # import adafruit_dht

    # # Initial the dht device, with data pin connected to:
    # # dhtDevice = adafruit_dht.DHT11(board.D4)

    # # you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
    # # This may be necessary on a Linux single board computer like the Raspberry Pi,
    # # but it will not work in CircuitPython.
    # dhtDevice = adafruit_dht.DHT11(board.D4, use_pulseio=False)

    # tryAgain = True

    # while tryAgain:
    #     try:
    #         now = datetime.datetime.now()

    #         # temp_c = dhtDevice.temperature
    #         # temp_f = round(temp_c * (9 / 5) + 32,1)
    #         rel_hum = round(dhtDevice.humidity,1)

    #     except RuntimeError as error:
    #         # Errors happen fairly often, DHT's are hard to read, just keep going
    #         print(error.args[0])
    #         time.sleep(1.0)
    #         continue
    #     except TypeError as error:
    #         print(f"No values: {error.args[0]}")
    #         time.sleep(3.0)
    #         continue
    #     except Exception as error:
    #         dhtDevice.exit()
    #         raise error

    #     tryAgain = False

    # ========================================
    # get values from analog temp sensor (through ADS1115 analog-digital converter) ====== #
    # we'll use these temperature values instead of those from the DHT sensor, as they are more precise
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    ads = ADS.ADS1115(i2c)
    # you can specify an I2C adress instead of the default 0x48
    # ads = ADS.ADS1115(i2c, address=0x49)

    # Create single-ended input on channel 0
    chan = AnalogIn(ads, ADS.P0)

    # Create differential input between channel 0 and 1
    # chan = AnalogIn(ads, ADS.P0, ADS.P1)

    # print("{:>5}\t{:>5}".format("raw", "v"))

    temp = chan.voltage * 100

    temp_c = round(temp,1)
    temp_f = round(temp * 9/5 + 32,1)

    # ========================================
    # get values from AHT20 sensor
    import adafruit_ahtx0
    sensor = adafruit_ahtx0.AHTx0(i2c)
    # only get humidity for now, continue using analog temp sensor for temp
    # temp_c = sensor.temperature
    rel_hum = round(sensor.relative_humidity,1)


    # abs_hum = estimate_abs_hum.estimate(rel_hum,temp_c)


    # ====== store the values ====== #

    values = {
        "temp_c": temp_c,
        "temp_f": temp_f,
        "rel_hum": rel_hum,
        "abs_hum": 0#abs_hum
    }
    now = datetime.datetime.now()
    # print(f"{now} temp: {temp_f}° F ({temp_c}° C), rel_hum: {rel_hum}%")# abs_hum: {abs_hum}g/m³")


    # ====== save the values to file ====== #
    if log == True :
        new_record = f"{int(now.timestamp()*1000)} {temp_f} {rel_hum} ({now})\n"

        try:
            # check if new value is different from last recorded value
            with open(sensor_data_filepath, "r") as f:
                last_line = f.readlines()[-1].split()
        except Exception as e:
            last_line = [-1,-1,-1]
            logger.error(f"Unable to write sensor data to data.txt — {repr(e)}")

        try:
            time_diff = (int(now.timestamp()*1000) - int(last_line[0])) / 1000 / 60
            temp_diff = abs(float(last_line[1]) - temp_f)
            rel_hum_diff = abs(float(last_line[2]) - rel_hum)

            logger.debug(f"last sensor record: {last_line}")
            logger.debug(f'Differences:\ntime_diff: {time_diff}\ntemp_diff: {temp_diff}\nhum_diff: {rel_hum_diff}')

            # only log differences above the following thresholds
            if temp_diff >= 0.2 or rel_hum_diff > 0 or time_diff > 30:
                # print(last_line)
                # print(float(last_line[1]))
                # print(float(last_line[2]))
                # print("different!!!!")

                # and then only log every 10 minutes unless the following thresholds are met
                if time_diff > 10 or temp_diff >= 0.5 or rel_hum_diff > 1:

                    with open(sensor_data_filepath, "a") as f:
                        f.write(new_record)

        except (ValueError, IndexError) as error:
            # if a line doesn't follow the format, (we might have added a comment), then ignore that and write a new line
            with open(sensor_data_filepath, "a") as f:
                f.write(new_record)

    return values

# get weather data
def get_logged_weather_data(filepath=weather_data_filepath,day_range=0,hour_range=0) :
    if day_range > 0 and hour_range > 0 :
        raise ValueError("Must either pass day_range or hour_range (or neither), but not both")

    # open existing file and get old data
    try:
        with open(filepath,'r') as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as e:
                logger.error(f'Error loading weather data from {filepath}: {e}')

                if not f.read(1):
                    logger.warning('File exists but is empty')
                    data = {}
                else:
                    raise e

    except FileNotFoundError as e:
        logger.error("No existing file found for weather data")
        data = {}

    now = datetime.datetime.now()

    delta = datetime.timedelta(days=day_range)
    if hour_range > 0 :
        delta = datetime.timedelta(hours=hour_range)

    filtered_data = {}
    if day_range > 0 or hour_range > 0 :
        for key,value in data.items() :
            try :
                datapoint_time = datetime.datetime.fromtimestamp(int(key)/1000)
            except Exception as e:
                logger.debug(f'Unable to parse timestamp in line (skipping): {key} -- {e}')
                continue

            # if a day_range was given (an integer > 0), test if this datapoint is younger than that day range,
            # and if it is, save it to filtered_data
            if now - delta < datapoint_time :
                filtered_data[key] = value
    else :
        # if the day_range is 0, don't do any filtering
        filtered_data = data



    return filtered_data

def get_logged_sensor_data(filepath=sensor_data_filepath,day_range=0) :
    data = {}
    now = datetime.datetime.now()
    delta = datetime.timedelta(days=day_range)

    # open file and format data
    try:
        with open(filepath,'r') as f:
            for index,line in enumerate(f) :
                line_data = line.split()
                try :
                    key = int(line_data[0])
                    datapoint_time = datetime.datetime.fromtimestamp(key/1000)

                    # if a day_range was given (an integer > 0), test if this datapoint is older than that day range, and ignore if it is
                    if day_range > 0 and now - delta > datapoint_time :
                        continue
                except Exception as e:
                    logger.debug(f'Unable to parse timestamp in line {index+1} (skipping): {line} -- {e}')
                    continue

                try :
                    data[key] = {
                        "temp" : float(line_data[1]),
                        "rel_hum" : float(line_data[2])
                    }
                except IndexError as e:
                    logger.debug(f'Unable to parse line {index+1} (skipping): {line} -- {e}')
                except ValueError as e:
                    # logger.debug(f'Unable to parse temp/humidity in line {index+1}, assuming it contains a non-datapoint label: {line}')

                    match = re.search(r"\[.*\]", line)
                    result = match.group()
                    if (result) :
                        data[key] = {
                            "label" : result
                        }

    except FileNotFoundError as e:
        logger.error("No existing data file found")

    return data

if __name__ == "__main__" :
    get_current()
