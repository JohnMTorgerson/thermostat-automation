# print("__package__, __name__ ==", __package__, __name__)
import logging
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
        therm_logger.info(f'Temp is {temp}, {target-temp} degrees below target: TURNING A/C OFF')
        switchAC(value="off",client=client, plugs=plugs)
    elif temp >= target + hysteresis :
        # turn on A/C
        therm_logger.info(f'Temp is {temp}, {temp-target} degrees above target: TURNING A/C ON')
        switchAC(value="on",client=client, plugs=plugs)
    else :
        # within hysteresis range, so do nothing
        therm_logger.info(f"Temp is within hysteresis range ({abs(temp-target)} degrees away from target), not changing A/C state")


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
    therm_logger.debug(f"Turning {value} plugs:")
    for plug in plugs :
        therm_logger.debug(plug.nickname)
        if value == "off" :
            client.plugs.turn_off(device_mac=plug.mac, device_model=plug.product.model)
        elif value == "on" :
            client.plugs.turn_on(device_mac=plug.mac, device_model=plug.product.model)

if __name__ == "__main__" :
    run()
