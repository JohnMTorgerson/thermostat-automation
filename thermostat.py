def run() :
    hysteresis = 3

    temp = get_current_temp()
    target = get_temp_target()

    if temp <= target - hysteresis :
        # turn off A/C
        pass

    if temp >= target + hysteresis :
        # turn on A/C
        pass


def get_current_temp() :
    try :
        from . import log_temp
        values = log_temp.get_and_log()
    except ModuleNotFoundError as e :
        # if not running on raspberry pi with 'board' module, just try some test values
        values = {'temp_c': 24, 'temp_f': 75.2, 'humidity': 32}

    print(values)
    return values["temp_f"]

def get_temp_target() :
    return 75


if __name__ == "__main__" :
    run()
