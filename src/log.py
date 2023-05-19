import logging, os, sys


def get_log_output_level(loglevel):
    levels = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }
    return levels[loglevel]


def setup_custom_logger(name, loglevel=None):
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    if not loglevel:
        loglevel = os.environ.get("LOGLEVEL", "info")
    log_output_level = get_log_output_level(loglevel)
    logger.setLevel(log_output_level)
    logger.addHandler(handler)
    return logger
