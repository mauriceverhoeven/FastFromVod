from src import log
import datetime


logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")


def get_UTC_now():
    return datetime.datetime.now(datetime.timezone.utc)


def datetime_from_isostring(iso_string):
    return datetime.datetime.fromisoformat(iso_string)


def get_target_UTC_day(datestring):
    return datetime_from_isostring(f"{datestring}T00:00:00Z")


def seconds_to_timedelta(seconds):
    return datetime.timedelta(seconds=seconds)


def get_offset_from_timestamp(timestamp):
    # logger.info(timestamp)
    start_of_time = datetime_from_isostring(f"1900-01-01T00:00:00Z")
    point_in_time = datetime_from_isostring(f"1900-01-01T{timestamp}Z")
    # logger.info(f"{start_of_time=}, {point_in_time=}")
    # logger.info(f"{point_in_time - start_of_time}")
    return (point_in_time - start_of_time).total_seconds()


def pretty_datetime(dateObj):
    return datetime.datetime.isoformat(dateObj)


def pretty_time(dateObj):
    return datetime.datetime.strftime(dateObj, "%H:%M:%S")


def get_epoch_utc():
    return datetime_from_isostring("1970-01-01T00:00:00Z")


def get_epoch_timestamp_milliseconds(dateObj):
    epoch = get_epoch_utc()
    return int((dateObj - epoch).total_seconds() * 1000)
