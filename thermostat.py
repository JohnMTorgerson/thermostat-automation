# print("__package__, __name__ ==", __package__, __name__)
import logging
from datetime import datetime
import json

# create logger
therm_logger = logging.getLogger(f"main.{__name__}")


def run(client=None,plugs=[]) :
    if client == None or len(plugs) == 0 :
        return

    therm_logger.info("Running thermostat scene...")

    # get current values from sensor(s)
    values = get_current_values()
    temp = values["temp_f"]
    humidity = values["humidity"]

    # get target values set by user for both temp and humidity
    settings = get_user_settings()
    temp_hum_cutoff = settings["temp_hum_cutoff"]
    temp_target = settings["temp_target"]
    hum_target = settings["hum_target"]
    temp_hyst = settings["temp_hyst"]
    hum_hyst = settings["hum_hyst"]

    # if thermostat is set to off, turn A/C off and return
    if (settings["on"] == False) :
        therm_logger.info(f'************* THERMOSTAT IS SET TO OFF, (turning A/C off)')
        switchAC(value="off",client=client, plugs=plugs)
        return

    # turn A/C on or off based on temp and humidity targets vs current sensor values
    if (temp <= temp_target - temp_hyst) and (humidity <= hum_target - hum_hyst or temp < temp_hum_cutoff):
        # turn off A/C
        therm_logger.info(f'Temp is {temp}, {(temp_target-temp):.1f}° below target; Humidity is {humidity}, {(hum_target-humidity):.1f} below target: TURNING A/C OFF')
        switchAC(value="off",client=client, plugs=plugs)
    elif (temp > temp_target) or (humidity > hum_target and temp >= temp_hum_cutoff):
        # turn on A/C
        therm_logger.info(f'Temp is {temp}, {(temp-temp_target):.1f}° above target; Humidity is {humidity}, {(humidity-hum_target):.1f} above target: TURNING A/C ON')
        switchAC(value="on",client=client, plugs=plugs)
    else :
        # within hysteresis range, so do nothing
        therm_logger.info(f"Temp and humidity are both below target or within hysteresis range ({(temp_target-temp):.1f}° below temp target, {(hum_target-humidity):.1f} %-pts below humidity target), not changing A/C state")


def get_current_values() :
    try :
        from . import get_data
        values = get_data.get_current() # gets current sensor values, but also logs them to ./data/data.txt
        therm_logger.info(f"CURRENT VALUES ==== temp_c:{values['temp_c']}, temp_f:{values['temp_f']}, humidity:{values['humidity']}")
    except ModuleNotFoundError as e :
        # if not running on raspberry pi with 'board' module, just try some test values
        values = {'temp_c': 24, 'temp_f': 80.6, 'humidity': 45}
        therm_logger.error(f"Error: not running on raspberry pi, using test values: temp_c:{values['temp_c']}, temp_f:{values['temp_f']}, humidity:{values['humidity']}")
    except Exception as e :
        therm_logger.error(f"Other error getting temp/humidity values: {e}")
        raise e

    return values

def get_user_settings() :
    try:
        with open("scenes/basic/thermostat/settings.json", "r") as f :
            settings = json.load(f)
    except Exception as e:
        therm_logger.error(f"Error: Unable to retrieve thermostat settings from file. Temporarily using defaults\n{e}")
        # values designed to keep the A/C off until the problem is fixed
        settings = {
            "on" : False,
            "temp_hum_cutoff" : 100,
            "temp_target" : 100,
            "temp_hyst" : 1,
            "hum_target" : 100,
            "hum_hyst" : 1
        }

    therm_logger.info(f"Thermostat settings: {settings}")

    return settings

# def get_temp_target() :
#     target = 82
#     therm_logger.info(f"Target temp is {target} degrees F")
#     return target
#
# def get_hum_target() :
#     target = 44
#     therm_logger.info(f"Target humidity is {target}%")
#     return target
#
#
# def get_hysteresis() :
#     hyst = 3
#     therm_logger.info(f"Hysteresis value is -{hyst} degrees F")
#     return hyst

def switchAC(value="",client=None, plugs=[]) :
    previous_value = "off"

    therm_logger.debug(f"Turning {value} plugs:")
    for plug in plugs :
        # if any of the plugs were on already, we return that to the calling function
        if client.plugs.info(device_mac=plug.mac).is_on :
            previous_value = "on"

        therm_logger.debug(plug.nickname)
        if value == "off" :
            client.plugs.turn_off(device_mac=plug.mac, device_model=plug.product.model)
        elif value == "on" :
            client.plugs.turn_on(device_mac=plug.mac, device_model=plug.product.model)

    # only log the change if it actually changed irl
    if previous_value != value:
        log_switch(value)


def log_switch(value) :
    data_path = "scenes/basic/thermostat/data/data.txt"
    now = datetime.now()
    therm_logger.debug(f"writing into {data_path} that we turned A/C {value}...")
    try :
        with open(data_path, "a") as f:
            f.write(f"{int(now.timestamp()*1000)} [TURNED A/C {value}] ({now})\n")
            therm_logger.debug("...successfully wrote to file!")
    except Exception as e :
        therm_logger.error(f"Error: unable to log switch action to data file: {e}")

    # run get_current_values() again, just to make sure we log the current sensor values into the data file right after we switch the A/C on/off
    get_current_values()


if __name__ == "__main__" :
    run()
