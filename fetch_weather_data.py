import csv
import requests
from requests.exceptions import HTTPError
from pprint import pprint
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except:
    from backports.zoneinfo import ZoneInfo
import json


def fetch(save_filepath='scenes/basic/thermostat/data/weather_data.json'):
    num_days = 7 # unknown what the maximum allowed value is; the highest example on the website is 56 days
    data_url = f'https://weather.gladstonefamily.net/cgi-bin/wxobservations.pl?site=KMSP&days={num_days}'
    data = download(data_url)
    dict_data = convert_to_dict(data)
    save_to_file(dict_data, save_filepath)

# download data
def download(url):
    try:
        response = requests.get(url)

        # tell the response to raise an error if the request was not successful
        # If the response was successful, no Exception will be raised
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
    else:
        print('Success retrieving weather data')
        # print(response.text)
        return response.text

# open csv data
# and convert it to a dict object
def convert_to_dict(csv_data):
    dict_data_list = csv.DictReader(csv_data.splitlines())
    dict_data_keyval = {}
    for row in dict_data_list :
        # read the time data and convert to a datetime object
        try:
            time = datetime.strptime(row["Time (UTC)"], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).astimezone(tz=ZoneInfo('US/Central'))
        except ValueError as e:
            print(f'Skipping data point, could not parse date string: {row["Time (UTC)"]}\n{e}')
            continue

        # add row to dict_data_keyval using the Unix timestamp as a key
        dict_data_keyval[round(time.timestamp()*1000)] = row

    print("Success formatting data")

    # pprint(dict_data_keyval)
    return dict_data_keyval

# save the converted json data to a file for later access
# write json data to file at filepath, adding to existing data (overwriting any duplicate dates)
def save_to_file(new_data, filepath):
    # first open existing file and get old data
    try:
        with open(filepath,'r') as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError as e:
                print(f'Error loading data from {filepath}: {e}')

                if not f.read(1):
                    print('File exists but is empty')
                    data = {}
                else:
                    raise e

    except FileNotFoundError as e:
        print("No existing data file found; creating new one")
        data = {}

    # loop through the new data
    for timestamp in new_data:
        # and add it to the existing data, overwriting any duplicate entries
        # we have to convert the key to a string in order to match the json data from the file
        # or else, for any overlapping data, we'll end up with duplicate entries (some int keys and some string keys)
        data[str(timestamp)] = new_data[timestamp]

    # write the combined data back to the file
    with open(filepath,'w') as f:
        json.dump(data, f)

    print("Success writing to file")


if __name__ == "__main__" :
    fetch(save_filepath='data/weather_data.json')
