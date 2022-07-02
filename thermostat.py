# print("__package__, __name__ ==", __package__, __name__)
import logging
from datetime import datetime

# create logger
therm_logger = logging.getLogger(f"main.{__name__}")


def run(client=None,plugs=[]) :
    if client == None or len(plugs) == 0 :
        return

    therm_logger.info("Running thermostat scene...")
    temp = get_current_temp()
    target = get_temp_target()
    hysteresis = get_hysteresis()


    if temp <= target - hysteresis :
        # turn off A/C
        therm_logger.info(f'Temp is {temp}, {(target-temp):.1f} degrees below target: TURNING A/C OFF')
        prev_val = switchAC(value="off",client=client, plugs=plugs)
        # only log that we turned it off if it was previously on
        if prev_val == "on" :
            log_switch("OFF")
    elif temp >= target + hysteresis :
        # turn on A/C
        therm_logger.info(f'Temp is {temp}, {(temp-target):.1f} degrees above target: TURNING A/C ON')
        prev_val = switchAC(value="on",client=client, plugs=plugs)
        # only log that we turned it on if it was previously off
        if prev_val == "off" :
            log_switch("ON")
    else :
        # within hysteresis range, so do nothing
        therm_logger.info(f"Temp is within hysteresis range ({abs(temp-target):.1f} degrees away from target), not changing A/C state")


def get_current_temp() :
    try :
        from . import log_temp
        values = log_temp.get_and_log()
        therm_logger.info(f"CURRENT VALUES ==== temp_c:{values['temp_c']}, temp_f:{values['temp_f']}, humidity:{values['humidity']}")
    except ModuleNotFoundError as e :
        # if not running on raspberry pi with 'board' module, just try some test values
        values = {'temp_c': 24, 'temp_f': 70, 'humidity': 32}
        therm_logger.error(f"Error: not running on raspberry pi, using test values: temp_c:{values['temp_c']}, temp_f:{values['temp_f']}, humidity:{values['humidity']}")
    except Exception as e :
        therm_logger.error(f"Other error getting temp/humidity values: {e}")
        raise e

    return values["temp_f"]

def get_temp_target() :
    target = 82
    therm_logger.info(f"Target temp is {target} degrees F")
    return target

def get_hysteresis() :
    hyst = 2
    therm_logger.info(f"Hysteresis value is +/- {hyst} degrees F")
    return hyst


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

    return previous_value

def log_switch(value) :
    data_path = "scenes/basic/thermostat/data/data.txt"
    now = datetime.now()
    therm_logger.debug(f"writing into {data_path} that we turned A/C {value}...")
    try :
        with open(data_path, "a") as f:
            f.write(f"{int(now.timestamp())} [TURNED A/C {value}] ({now})\n")
            therm_logger.debug("...successfully wrote to file!")
    except Exception as e :
        therm_logger.error(f"Error: unable to log switch action to data file: {e}")


if __name__ == "__main__" :
    run()
