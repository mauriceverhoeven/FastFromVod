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
        "-t",
        "--target",
        required=True,
        help="add programs that are planned on this target day (yyyy-mm-dd).. UTC day-start for now ",
        dest="target_date",
        action="store",
    )

    parser.add_argument(
        "-f",
        "--force",
        required=False,
        help="force the creation even if some wpks aren't available ",
        dest="force",
        action="store_true",  # stores when flag is present
    )
    args = vars(parser.parse_args())
    logger.info(f"received: {args=}")
    inputfiles = args["inputfiles"]
    target_date = args["target_date"]
    force = args["force"]
    return (inputfiles, target_date, force)


def program_in_target_range(start_of_range, end_of_range, program):
    start_ok = program.starttime >= start_of_range
    end_ok = program.starttime < end_of_range
    result = all([start_ok, end_ok])
    logger.debug(
        f"{program.wpk} has {program.starttime} within {start_of_range} and {end_of_range} is {result} for "
    )
    return result


if __name__ == "__main__":
    (inputfiles, target_date, force) = get_input_arguments()
    mt = mt.MediaTailor(create_stack=False)
    playlist = pp.PlaylistParser(target_date)

    for inputfile in inputfiles:
        playlist.add_xml(inputfile)

    for program in playlist.get_parsed_programs():
        print(program)
        mt.add_to_schedule(program)
    print(mt.schedule)
    mt.commit(force)
