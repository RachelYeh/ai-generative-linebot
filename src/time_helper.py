from datetime import datetime
import pytz, logging


def generate_current_timestamp():
    current_datetime = datetime.now()
    timestamp = datetime_to_timestamp(current_datetime)
    return timestamp

def datetime_to_timestamp(dt_obj):
    timezoned_dt_obj = dt_obj.astimezone(pytz.timezone("Asia/Taipei"))
    target_timestamp = int(timezoned_dt_obj.timestamp() * 1000)
    return target_timestamp

def print_readable_datetime(timestamp):
    # check digit (need to be 10)
    if len(str(timestamp)) > 10:
        timestamp = int(timestamp)/1000.0
    dt_obj = datetime.fromtimestamp(float(timestamp)) #.isoformat()
    formatted_time = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"formatted_time: {formatted_time}")
    #logging.info(f"iso formatted_time: {dt_obj.isoformat()}")
