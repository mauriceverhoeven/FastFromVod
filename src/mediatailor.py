import boto3
import json
from src import log
from src import streaminfo as si
from src import config



sys.exit()
logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")

VOD_SOURCE_LOCATION_ID = "VOD"
ADS_SOURCE_LOCATION_ID = "ADS"
SLATE_AD_NAME = "slate_ad_240s"


class StackConfigIncompleteExeption(Exception):
    def __init__(self, **kwargs):
        # Call the base class constructor with the parameters it needs
        super().__init__(kwargs)
        self.__dict__ = kwargs

    def __str__(self):
        return f"<StackConfigIncompleteExeption. Running with `create_stack=True` might fix this! Currently -> {self.message}>"


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
        DefaultSegmentDeliveryConfiguration={
            "BaseUrl": config.VOD_CDN
        },
        HttpConfiguration={
            "BaseUrl": config.VOD_MEDIAPACKAGE_URL
        },
        SourceLocationName=VOD_SOURCE_LOCATION_ID,
        # Tags={"string": "string"},
    )


def create_ads_source_location(client):
    # Create Source Location ADS
    return client.create_source_location(
        DefaultSegmentDeliveryConfiguration={
            "BaseUrl": config.ADS_CDN
        },
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


def create_channel(client, channel_name):
    # Create Channel
    return client.create_channel(
        ChannelName=channel_name,
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


def get_channel_by_channelname(client, channel_name):
    channels = client.list_channels()["Items"]
    for channel in channels:
        if channel["ChannelName"] == channel_name:
            return channel


class MediaTailor:
    def __init__(self, channel_name, create_stack=False) -> None:
        self._boto_client = None
        self._channel_name = channel_name
        if create_stack:
            self.create_stack_components()
        self.validate_config()
        self._available_wpks = set()
        self._unavailable_wpks = set()

    def __repr__(self) -> str:
        return f"<MediaTailor for {self._channel_name}>"

    @property
    def client(self):
        if not self._boto_client:
            self._boto_client = get_boto_client()
        return self._boto_client

    def create_stack_components(self):
        create_vod_source_location(self.client)
        create_ads_source_location(self.client)
        create_slate_ad(self.client)
        create_channel(self.client, self._channel_name)

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
        return get_channel_by_channelname(self.client, self._channel_name)[
            "ChannelName"
        ]

    def add_wpk_to_unavailable(self, wpk):
        self._unavailable_wpks.add(wpk)

    def add_wpk_to_available(self, wpk):
        self._available_wpks.add(wpk)

    @property
    def available_wpks(self):
        if not self._available_wpks:
            self._available_wpks.update(list_vod_wpks(self.client))
        return self._available_wpks


    def provision_vod_source(self, program):
        video_asset = si.VideoAsset(wpk=program.wpk)
        if program.wpk not in self.available_wpks:
            if video_asset.is_available:
                result = create_vod_item(
                    self.client,
                    wpk=video_asset.wpk,
                    hls_url=video_asset.get_non_drm_streaming_url_by_protocol("HLS"),
                    dash_url=video_asset.get_non_drm_streaming_url_by_protocol("DASH"),
                )
                self.add_wpk_to_available(program.wpk)
                logger.info(f"created {program.wpk} -> {result}")
            else:
                self.add_wpk_to_unavailable(program.wpk)
                logger.warning(f"{program.wpk} is not available!")
        else:
            logger.info(f"{program.wpk} already exists")
