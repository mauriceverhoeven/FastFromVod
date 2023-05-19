from src import log
from src import utils
import xml.etree.ElementTree as ET

logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")


SLATE_AD_LENGTH = 190


class PlaylistParser:
    def __init__(self) -> None:
        self._programs = []
        self._root = None
        self._date_filter_start = None
        self._date_filter_end = None

    def __repr__(self) -> str:
        return f"<Playlist {self.root} >"

    def apply_date_filter(self, program) -> bool:
        start_ok = True
        end_ok = True
        if self._date_filter_start:
            start_ok = program.program_start >= self._date_filter_start
        if self._date_filter_end:
            end_ok = program.program_start < self._date_filter_end
        return all([start_ok, end_ok])

    def set_date_filter(self, start_date=None, end_date=None) -> None:
        logger.info(f"{start_date=} {end_date=}")
        if start_date:
            self._date_filter_start = utils.get_target_UTC_day(start_date)
        if end_date:
            self._date_filter_end = utils.get_target_UTC_day(end_date)

    def add_xml(self, fname: str):
        tree = ET.parse(fname)
        root = tree.getroot()
        for playlist_event in root:
            if playlist_event.tag == "scheduledItem":
                wpk = playlist_event.attrib["WPK"]
                current_program = self.get_current_playlist_program(wpk)
                for chaptermarker in playlist_event:
                    current_program.add_timeline_event(
                        Chapter(
                            starttime=playlist_event.attrib["StartTime"],
                            title=playlist_event.attrib["Title"],
                            media_starttime=chaptermarker.attrib["MediaStartTime"],
                        )
                    )
            else:
                current_program.add_timeline_event(
                    Adbreak(
                        starttime=playlist_event.attrib["StartTime"],
                        duration=int(playlist_event.attrib["Duration"]),
                    )
                )

    def get_current_playlist_program(self, wpk):
        try:
            if self._programs[-1].wpk != wpk:
                self._programs.append(Program(wpk=wpk))
        except IndexError:
            # empty list, add the first one to the list
            self._programs.append(Program(wpk=wpk))
            pass
        return self._programs[-1]

    def get_parsed_programs(self) -> list:
        self._programs.sort()
        return filter(self.apply_date_filter, self._programs)


class Program:
    def __init__(self, wpk) -> None:
        self._wpk = wpk
        self._timeline = []

    def __repr__(self) -> str:
        return f"<Program ({self.wpk}) starts at {self.program_start} >"

    def __lt__(self, obj):
        # magic method to allow sorting of Program objects
        return (self.program_start) < (obj.program_start)

    @property
    def wpk(self):
        return self._wpk

    @property
    def program_start(self):
        return self._timeline[0].starttime

    def add_timeline_event(self, timeline_event):
        self._timeline.append(timeline_event)

    @property
    def timeline(self):
        return self._timeline

    @classmethod
    def is_chapter(cls, timeline_event):
        return timeline_event.type == "Chapter"

    @classmethod
    def is_adbreak(cls, timeline_event):
        return not cls.is_chapter(timeline_event)

    @property
    def chapters(self):
        return filter(self.is_chapter, self.timeline)

    @property
    def adbreaks(self):
        return filter(self.is_adbreak, self.timeline)


class Chapter:
    def __init__(self, starttime, title, media_starttime) -> None:
        self._starttime = starttime
        self.type = "Chapter"
        self.title = title
        self._media_starttime = media_starttime

    def __repr__(self) -> str:
        return (
            f"<Chapter {utils.pretty_datetime(self.starttime)}, {self.media_starttime}>"
        )

    @property
    def starttime(self):
        return utils.datetime_from_isostring(self._starttime)

    @property
    def media_starttime(self):
        return utils.get_offset_from_timestamp(self._media_starttime)


class Adbreak:
    def __init__(self, starttime, duration) -> None:
        self._starttime = starttime
        self.type = "Adbreak"
        assert (
            duration == SLATE_AD_LENGTH
        ), f"Adbreaks have a fixed duration of {SLATE_AD_LENGTH}, got: {duration}"
        self._duration = SLATE_AD_LENGTH

    def __repr__(self) -> str:
        return (
            f"<Ad {utils.pretty_datetime(self.starttime)}, duration = {self.duration} >"
        )

    @property
    def title(self) -> str:
        return f"Adbreak {self.duration}"

    @property
    def duration(self):
        return utils.seconds_to_timedelta(self._duration)

    @property
    def starttime(self):
        return utils.datetime_from_isostring(self._starttime)
