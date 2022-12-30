# print("__package__, __name__ ==", __package__, __name__)
import logging
from datetime import datetime
import json

# create logger
therm_logger = logging.getLogger(f"main.{__name__}")


def run(client=None,plugs={}) :
    plugs_is_empty = True
    for list_of_plugs_by_controlling in plugs :
        if len(list_of_plugs_by_controlling) > 0 :
            plugs_is_empty = False
    if client == None or plugs_is_empty :
        return

    therm_logger.info("Running thermostat scene...")

    # get current values from sensor(s)
    values = get_current_values()
    temp = values["temp_f"]
    humidity = values["humidity"]

    # get target values set by user for both temp and humidity
    settings = get_user_settings()
    temp_hum_cutoff =   settings["temp_hum_cutoff"]
    temp_target =       settings["temp_target"]
    hum_max =           settings["hum_max"]
    hum_min =           settings["hum_min"]
    temp_hyst =         settings["temp_hyst"]
    hum_hyst =          settings["hum_hyst"]

    # if thermostat is set to off, turn plugs off and return
    if (settings["on"] == False) :
        therm_logger.info(f'************* THERMOSTAT IS SET TO OFF, (turning all devices off)')
        switchAC(value="off",client=client, plugs=plugs)
        switchHumidifier(value="off",client=client, plugs=plugs)
        return

    # turn A/C on or off based on temp and humidity targets vs current sensor values
    def run_AC() :
        if (temp <= temp_target - temp_hyst) and (humidity <= hum_max - hum_hyst or temp < temp_hum_cutoff):
            # turn off A/C
            therm_logger.info(f'Temp is {temp}, {(temp_target-temp):.1f}° below target; Humidity is {humidity}, {(hum_max-humidity):.1f} below max: TURNING A/C OFF')
            switchAC(value="off",client=client, plugs=plugs)
        elif (temp > temp_target) or (humidity > hum_max and temp >= temp_hum_cutoff):
            # turn on A/C
            therm_logger.info(f'Temp is {temp}, {(temp-temp_target):.1f}° above target; Humidity is {humidity}, {(humidity-hum_max):.1f} above max: TURNING A/C ON')
            switchAC(value="on",client=client, plugs=plugs)
        else :
            # within hysteresis range, so do nothing
            therm_logger.info(f"Temp and humidity are both below target or within hysteresis range ({(temp_target-temp):.1f}° below temp target, {(hum_max-humidity):.1f} %-pts below humidity target), not changing A/C state")

    # turn Humidifier on or off based on temp and humidity targets vs current sensor values
    def run_Humidifier() :
        # if above minimum turn humidifier off
        if (humidity >= hum_min):
            # turn off Humidifier
            therm_logger.info(f'Humidity is {humidity}, {(humidity-hum_min):.1f} above min: TURNING HUMIDIFIER OFF')
            switchHumidifier(value="off",client=client, plugs=plugs)
        # else if below minimum, minus hysteresis value, turn humidifier on
        elif (humidity < hum_min - hum_hyst):
            # turn on Humidifier
            therm_logger.info(f'Humidity is {humidity}, {(humidity-hum_min):.1f} below min: TURNING HUMIDIFIER ON')
            switchHumidifier(value="on",client=client, plugs=plugs)
        else :
            # within hysteresis range, so do nothing, do not change state
            therm_logger.info(f"Humidity is below minimum but within hysteresis range ({hum_min - hum_hyst}% <= {(humidity):.1f}% < {hum_min}%, not changing Humidifier state")

    # run A/C (if thresholds merit)
    run_AC()

    # run Humidifier (if thresholds merit)
    run_Humidifier()


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
        # default values designed to keep the A/C and Humidifier off until the problem is fixed
        settings = {
            "on" : False,
            "temp_hum_cutoff" : 100,
            "temp_target" : 212,
            "temp_hyst" : 1,
            "hum_max" : 100,
            "hum_min" : 0,
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

def switchAC(value="", client=None, plugs=[]) :
    previous_value = "off"

    therm_logger.debug(f"Turning {value} plugs:")
    try :
        for plug in plugs["A/C"] :
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
            log_switch(value, "A/C")
    except KeyError as e :
        therm_logger.debug(f"No A/C plugs found")

def switchHumidifier(value="", client=None, plugs=[]) :
    previous_value = "off"

    therm_logger.debug(f"Turning {value} plugs:")
    try :
        for plug in plugs["Humidifier"] :
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
            log_switch(value, "HUMIDIFIER")
    except KeyError as e :
        therm_logger.debug(f"No Humidifier plugs found")


def log_switch(value, deviceName) :
    data_path = "scenes/basic/thermostat/data/data.txt"
    now = datetime.now()
    therm_logger.debug(f"writing into {data_path} that we turned {deviceName} {value}...")
    try :
        with open(data_path, "a") as f:
            f.write(f"{int(now.timestamp()*1000)} [TURNED {deviceName} {value}] ({now})\n")
            therm_logger.debug("...successfully wrote to file!")
    except Exception as e :
        therm_logger.error(f"Error: unable to log switch action to data file: {e}")

    # run get_current_values() again, just to make sure we log the current sensor values into the data file right after we switch the A/C on/off
    get_current_values()


if __name__ == "__main__" :
    run()
