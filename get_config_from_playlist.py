
from src import log
from src import mediatailor as mt
from src import playlist_parser as pp
from src import utils
import argparse

logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")


def get_input_arguments():
    arg_desc = """
    Create configuration for MediaTailor from XML playlist
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc
    )
    parser.add_argument(
        "-i",
        "--inputfile(s)",
        required=True,
        nargs="*",
        help="the path to the inputfiles in cloudfront format",
        dest="inputfiles",
        action="store",
    )

    parser.add_argument(
        "-s",
        "--start",
        required=False,
        help="only return items that start on or after (yyyy-mm-dd).. UTC day-start for now ",
        dest="start_date",
        action="store",
    )

    parser.add_argument(
        "-e",
        "--end",
        required=False,
        help="only return items that start before (yyyy-mm-dd).. UTC day-start for now ",
        dest="end_date",
        action="store",
    )
    args = vars(parser.parse_args())
    logger.debug(f"received: {args=}")
    inputfiles = args["inputfiles"]
    start_date = args["start_date"]
    end_date = args["end_date"]
    return (inputfiles, start_date, end_date)


def program_in_target_range(start_of_range, end_of_range, program):
    start_ok = program.starttime >= start_of_range
    end_ok = program.starttime < end_of_range
    result = all([start_ok, end_ok])
    logger.debug(
        f"{program.wpk} has {program.starttime} within {start_of_range} and {end_of_range} is {result} for "
    )
    return result


if __name__ == "__main__":
    (inputfiles, start_date, end_date) = get_input_arguments()
    mt = mt.MediaTailor(channel_name="SBS6ClassicsVod", create_stack=False)
    playlist = pp.PlaylistParser()
    playlist.set_date_filter(start_date, end_date)

    for inputfile in inputfiles:
        playlist.add_xml(inputfile)

    for program in playlist.get_parsed_programs():
        print(program)
        mt.provision_vod_source(program)
