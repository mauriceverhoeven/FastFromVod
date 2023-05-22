from src import config
from src import log
from src import streaminfo as si
from src import utils
import boto3
import json

logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")

VOD_SOURCE_LOCATION_ID = "VOD"
ADS_SOURCE_LOCATION_ID = "ADS"
SLATE_AD_NAME = "slate_ad_240s"
CHANNEL_NAME = "SBS6ClassicsVod"


class StackConfigIncompleteExeption(Exception):
    def __init__(self, **kwargs):
        # Call the base class constructor with the parameters it needs
        super().__init__(kwargs)
        self.__dict__ = kwargs

    def __str__(self):
        return f"<StackConfigIncompleteExeption. Running with `create_stack=True` might fix this! Currently -> {self.message}>"


def get_adbreak_config(breakpoint_seconds):
    logger.info(f"creating breakpoint at {breakpoint_seconds}")
    # seconds = int(utils.get_offset_from_timestamp(breakpoint_seconds).total_seconds())
    # logger.info(f"creating breakpoint at {seconds}")

    return {
        "MessageType": "SPLICE_INSERT",
        "OffsetMillis": int(breakpoint_seconds * 1000),
        "Slate": {
            "SourceLocationName": ADS_SOURCE_LOCATION_ID,
            "VodSourceName": SLATE_AD_NAME,
        },
    }


def get_chapters_config(chapters):
    AdBreaks = []
    for chapter in chapters:
        AdBreaks.append(get_adbreak_config(breakpoint_seconds=chapter.media_starttime))
    return AdBreaks


def get_first_schedule_config(program_start_milliseconds):
    return {
        "Transition": {
            "RelativePosition": "AFTER_PROGRAM",
            "RelativeProgram": "",
            "Type": "ABSOLUTE",
            "ScheduledStartTimeMillis": program_start_milliseconds,
        },
    }


def get_next_schedule_config(previous_program_name):
    return {
        "Transition": {
            "Type": "RELATIVE",
            "RelativePosition": "AFTER_PROGRAM",
            "RelativeProgram": previous_program_name,
        },
    }


def get_schedule_config(previous_program_name, program_start_milliseconds):
    if previous_program_name:
        return get_next_schedule_config(previous_program_name)
    return get_first_schedule_config(program_start_milliseconds)


def schedule_program(
    client, wpk, program_name, program_start, chapters, previous_program_name
):
    program_start_milliseconds = utils.get_epoch_timestamp_milliseconds(program_start)
    schedule_config = get_schedule_config(
        previous_program_name, program_start_milliseconds
    )
    return client.create_program(
        AdBreaks=get_chapters_config(chapters),
        ChannelName=CHANNEL_NAME,
        ProgramName=program_name,
        ScheduleConfiguration=schedule_config,
        SourceLocationName=VOD_SOURCE_LOCATION_ID,
        VodSourceName=wpk,
    )


def get_program_info(client, wpk):
    return client.describe_program(ChannelName=CHANNEL_NAME, ProgramName=wpk)


def get_boto_client():
    return boto3.client("mediatailor", region_name="eu-west-1")


def find_source_location_name_by_id(client, source_location_id):
    for source_location in client.list_source_locations()["Items"]:
        logger.debug(f"{source_location=}")
        if source_location["SourceLocationName"] == source_location_id:
            return source_location["SourceLocationName"]


def delete_source_location_by_name(client, source_location_id):
    return client.delete_source_location(SourceLocationName=source_location_id)


def create_vod_source_location(client):
    # Create Source Location VOD
    return client.create_source_location(
        DefaultSegmentDeliveryConfiguration={"BaseUrl": config.VOD_CDN},
        HttpConfiguration={"BaseUrl": config.VOD_MEDIAPACKAGE_URL},
        SourceLocationName=VOD_SOURCE_LOCATION_ID,
        # Tags={"string": "string"},
    )


def create_ads_source_location(client):
    # Create Source Location ADS
    return client.create_source_location(
        DefaultSegmentDeliveryConfiguration={"BaseUrl": config.ADS_CDN},
        HttpConfiguration={"BaseUrl": config.ADS_CDN},
        SourceLocationName=ADS_SOURCE_LOCATION_ID,
        # Tags={"string": "string"},
    )


def create_source(client, hls_url, dash_url, source_location_name, source_name):
    return client.create_vod_source(
        HttpPackageConfigurations=[
            {"Path": hls_url, "SourceGroup": "HLS", "Type": "HLS"},
            {"Path": dash_url, "SourceGroup": "DASH", "Type": "DASH"},
        ],
        SourceLocationName=source_location_name,
        # Tags={"string": "string"},
        VodSourceName=source_name,
    )


def create_vod_item(client, wpk, hls_url, dash_url):
    return create_source(
        client=client,
        source_name=wpk,
        hls_url=hls_url,
        dash_url=dash_url,
        source_location_name=VOD_SOURCE_LOCATION_ID,
    )


def create_slate_ad(client):
    return create_source(
        client=client,
        hls_url="out/v1/53e113210a1a42d2af48d1b800dd847d/cc7cfd5fec77421b9be588ecb6ecdb9a/01f78d22f1294a3a8f0d5864f55a384b/index.m3u8",
        dash_url="/out/v1/53e113210a1a42d2af48d1b800dd847d/03c5f633270148bfa0eb85b279588241/b01cbbded8644e8e80dc0e899ce9edd7/index.mpd",
        source_location_name=ADS_SOURCE_LOCATION_ID,
        source_name=SLATE_AD_NAME,
    )


def list_source_names_by_location_id(client, source_location_name):
    return [
        source["VodSourceName"]
        for source in client.list_vod_sources(SourceLocationName=source_location_name)[
            "Items"
        ]
    ]


def list_vod_wpks(client):
    return list_source_names_by_location_id(
        client=client, source_location_name=VOD_SOURCE_LOCATION_ID
    )


def list_ads_names(client):
    return list_source_names_by_location_id(
        client=client, source_location_name=ADS_SOURCE_LOCATION_ID
    )


def create_channel(client):
    # Create Channel
    return client.create_channel(
        ChannelName=CHANNEL_NAME,
        FillerSlate={
            "SourceLocationName": ADS_SOURCE_LOCATION_ID,
            "VodSourceName": SLATE_AD_NAME,
        },
        Outputs=[
            {
                "HlsPlaylistSettings": {"ManifestWindowSeconds": 60},
                "ManifestName": "index_hls",
                "SourceGroup": "HLS",
            },
            {
                "DashPlaylistSettings": {
                    "ManifestWindowSeconds": 60,
                    "MinBufferTimeSeconds": 30,
                    "MinUpdatePeriodSeconds": 10,
                    "SuggestedPresentationDelaySeconds": 10,
                },
                "ManifestName": "index_dash",
                "SourceGroup": "DASH",
            },
        ],
        PlaybackMode="LINEAR",
        Tags={"string": "string"},
        Tier="STANDARD",
    )


def get_channel_by_channelname(client):
    channels = client.list_channels()["Items"]
    for channel in channels:
        if channel["ChannelName"] == CHANNEL_NAME:
            return channel


class MediaTailor:
    def __init__(self, create_stack=False) -> None:
        self._boto_client = None
        if create_stack:
            self.create_stack_components()
        self.validate_config()
        # print(json.dumps(get_program_info(self.client, wpk="objectname"), default=str))
        self._available_wpks = set()
        self._unavailable_wpks = set()
        self._program_schedule = []

    def __repr__(self) -> str:
        return f"<MediaTailor for {CHANNEL_NAME}>"

    @property
    def client(self):
        if not self._boto_client:
            self._boto_client = get_boto_client()
        return self._boto_client

    def create_stack_components(self):
        create_vod_source_location(self.client)
        create_ads_source_location(self.client)
        create_slate_ad(self.client)
        create_channel(self.client)

    def validate_config(self):
        has_vod_source = self.vod_source_name
        has_ads_source = self.ads_source_name
        has_slate_ad = self.has_slate_ad
        has_channel_name = self.channel_name
        ok = all([has_vod_source, has_ads_source, has_slate_ad, has_channel_name])
        if not ok:
            raise StackConfigIncompleteExeption(
                message=f"{has_vod_source=}, {has_ads_source=}, {has_slate_ad=}, {has_channel_name=}"
            )

    @property
    def vod_source_name(self):
        return find_source_location_name_by_id(self.client, VOD_SOURCE_LOCATION_ID)

    @property
    def ads_source_name(self):
        return find_source_location_name_by_id(self.client, ADS_SOURCE_LOCATION_ID)

    @property
    def has_slate_ad(self):
        logger.debug(list_ads_names(self.client))
        return SLATE_AD_NAME in list_ads_names(self.client)

    @property
    def channel_name(self):
        return get_channel_by_channelname(self.client)["ChannelName"]

    def add_wpk_to_unavailable(self, wpk):
        self._unavailable_wpks.add(wpk)

    def add_wpk_to_available(self, wpk):
        self._available_wpks.add(wpk)

    @property
    def available_wpks(self):
        if not self._available_wpks:
            self._available_wpks.update(list_vod_wpks(self.client))
        return self._available_wpks

    def add_to_schedule(self, program):
        if self.is_provisioned(program):
            self._program_schedule.append(program)

    @property
    def schedule(self):
        return self._program_schedule

    def commit(self, force):
        if self._unavailable_wpks:
            if force:
                print(
                    f"hese WPK's are not available {self._unavailable_wpks} but override due to {force=}"
                )
            else:
                print(
                    f"\n Exit.. as these WPK's are not available {self._unavailable_wpks}"
                )
                return
        previous_program_name = None
        item_counter = 0
        for program in self.schedule:
            item_counter += 1
            program_name = f"{program.wpk}-{item_counter}"
            logger.info(f"{program_name=}")
            schedule_program(
                client=self.client,
                wpk=program.wpk,
                program_name=program_name,
                program_start=program.program_start,
                chapters=program.chapters,
                previous_program_name=previous_program_name,
            )
            previous_program_name = program_name

    def is_provisioned(self, program):
        if program.wpk not in self.available_wpks:
            video_asset = si.VideoAsset(wpk=program.wpk)
            if video_asset.is_available:
                create_vod_item(
                    self.client,
                    wpk=video_asset.wpk,
                    hls_url=video_asset.get_non_drm_streaming_url_by_protocol("HLS"),
                    dash_url=video_asset.get_non_drm_streaming_url_by_protocol("DASH"),
                )
                self.add_wpk_to_available(program.wpk)
            else:
                self.add_wpk_to_unavailable(program.wpk)
                logger.warning(f"{program.wpk} is not available!")
        return program.wpk in self.available_wpks

    # def provision_vod_source(self, program):
    #     video_asset = si.VideoAsset(wpk=program.wpk)
    #     if program.wpk not in self.available_wpks:
    #         if video_asset.is_available:
    #             result = create_vod_item(
    #                 self.client,
    #                 wpk=video_asset.wpk,
    #                 hls_url=video_asset.get_non_drm_streaming_url_by_protocol("HLS"),
    #                 dash_url=video_asset.get_non_drm_streaming_url_by_protocol("DASH"),
    #             )
    #             self.add_wpk_to_available(program.wpk)
    #             logger.info(f"created {program.wpk} -> {result}")

    #         else:
    #             self.add_wpk_to_unavailable(program.wpk)
    #             logger.warning(f"{program.wpk} is not available!")
    #     else:
    #         self.add_to_schedule(program)
    #         logger.info(f"{program.wpk} already exists")
