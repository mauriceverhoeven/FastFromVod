from collections import namedtuple
from src import log
import json
import requests

logger = log.setup_custom_logger(__name__, loglevel="info")
logger.info(f"initiated module: {__name__}")


def get_query():
    return """query GetVideoDetails($videoId: [String], $programTypes: [ProgramType], $limit: Int, $skip: Int) {
            programs(
                guid: $videoId
                programTypes: $programTypes
                limit: $limit
                skip: $skip
            ) {
                items {
                guid
                duration
                slug
                media {
                    cuePoints {
                        time
                        title
                        }
                }
                availableRegion
                sources{
                    file
                    type
                    drm
                }
                }
            }
            }"""


def get_video_info(wpk):
    url = "https://api.prd.video.talpa.network/graphql"
    params = {}
    params["query"] = get_query()
    params["variables"] = json.dumps({"videoId": [wpk]})

    headers = {
        "content-type": "application/json",
        "x-client-id": "kijk",
    }
    r = requests.get(url=url, params=params, headers=headers)
    logger.debug(f"response = {r.json()}")
    return r.json()


Stream_Matcher = namedtuple(
    "Stream_Matcher",
    ["name", "protocol", "drm", "segment_pattern", "non_drm_segment_pattern"],
)

Stream_Matchers = [
    Stream_Matcher(
        name="HLS_NON_DRM",
        protocol="HLS",
        drm="NON_DRM",
        segment_pattern="/c883bd72608347a89339ec1f2f00caff/eb961633ca3b4ca8b910f99144cd30c4/",
        non_drm_segment_pattern="/c883bd72608347a89339ec1f2f00caff/eb961633ca3b4ca8b910f99144cd30c4/",
    ),
    Stream_Matcher(
        name="HLS_FAIRPLAY",
        protocol="HLS",
        drm="FAIRPLAY",
        segment_pattern="/d6640161dc6742f9a8d3dd909deea8ea/8090c2be20294a89b811fc891eff4801/",
        non_drm_segment_pattern="/c883bd72608347a89339ec1f2f00caff/eb961633ca3b4ca8b910f99144cd30c4/",
    ),
    Stream_Matcher(
        name="DASH_NON_DRM",
        protocol="DASH",
        drm="NON_DRM",
        segment_pattern="/88fd84e732ed401ba41634486678683b/b7dfd16bc86c483c9628d33798ac5e4f/",
        non_drm_segment_pattern="/88fd84e732ed401ba41634486678683b/b7dfd16bc86c483c9628d33798ac5e4f/",
    ),
    Stream_Matcher(
        name="DASH_WIDEVINE",
        protocol="DASH",
        drm="WIDEVINE",
        segment_pattern="/ba94badf69954f2b80c8016e0ccaad3d/f04bf2ba4ada4d28b0267d65f574f32e/",
        non_drm_segment_pattern="/88fd84e732ed401ba41634486678683b/b7dfd16bc86c483c9628d33798ac5e4f/",
    ),
    Stream_Matcher(
        name="DASH_PLAYREADY",
        protocol="DASH",
        drm="PLAYREADY",
        segment_pattern="/7116009110a0461a954ba1bec9b1f119/10c83c391917456d9e85c12dc4234641/",
        non_drm_segment_pattern="/88fd84e732ed401ba41634486678683b/b7dfd16bc86c483c9628d33798ac5e4f/",
    ),
    Stream_Matcher(
        name="SMOOTH_NON_DRM",
        protocol="SMOOTH",
        drm="NON_DRM",
        segment_pattern="/a250b5b07c2047d4af6fed6a91b7601f/87b5d98d0a0a491797215c0362fb10f3/",
        non_drm_segment_pattern="/a250b5b07c2047d4af6fed6a91b7601f/87b5d98d0a0a491797215c0362fb10f3/",
    ),
    Stream_Matcher(
        name="SMOOTH_PLAYREADY",
        protocol="SMOOTH",
        drm="PLAYREADY",
        segment_pattern="/680f243beaa341d98558ab1035ca111f/f54559bc544a4ede9bab1e61404a1e87/",
        non_drm_segment_pattern="/a250b5b07c2047d4af6fed6a91b7601f/87b5d98d0a0a491797215c0362fb10f3/",
    ),
]

# MANIFEST_SPLITTER = re.compile(
#     "#EXT-X-STREAM-INF:BANDWIDTH=(?P<BANDWIDTH>[\d]+).+\n(?P<url>.+m3u8)",
#     re.MULTILINE,
# )


def find_stream_matcher(streaming_url):
    for Stream_Matcher in Stream_Matchers:
        if Stream_Matcher.segment_pattern in streaming_url:
            return Stream_Matcher


def get_non_ww_url(streaming_url):
    (url, _) = streaming_url.split("?")
    return url.replace("vod-ww.prd1", "vod.prd1")


def get_path(steaming_url):
    chunks = steaming_url.split("/")
    if "kijk" in chunks:
        return "/".join(steaming_url.split("/")[5::])
    else:
        return "/".join(steaming_url.split("/")[3::])


def to_non_drm_streaming_url(streaming_url, stream_matcher):
    return get_path(
        get_non_ww_url(
            streaming_url.replace(
                stream_matcher.segment_pattern, stream_matcher.non_drm_segment_pattern
            )
        )
    )


class VideoAsset:
    def __init__(self, wpk) -> None:
        self.wpk = wpk
        self._api_response = None
        self._is_available = None
        pass

    def __repr__(self) -> str:
        return f"<VideoAsset {self.wpk}, duration {self.duration}, {self.cuepoints}, {self.title}  >"

    @property
    def is_available(self):
        if not self._is_available:
            self.api_response
        return self._is_available

    @property
    def api_response(self):
        if not self._api_response:
            self._is_available = False
            api_response = get_video_info(self.wpk)
            logger.debug(f"{self.wpk} {api_response}")
            for item in api_response["data"]["programs"]["items"]:
                if item["guid"] == self.wpk:
                    self._api_response = item
                    self._is_available = True
        return self._api_response

    @property
    def duration(self):
        return self.api_response["duration"]

    @property
    def cuepoints(self):
        return [
            cuePoint["time"] for cuePoint in self.api_response["media"][0]["cuePoints"]
        ]

    @property
    def title(self):
        return self.api_response["slug"].replace("empty_episode-", "")

    def sources(self):
        return self.api_response["sources"]

    def get_non_drm_streaming_url_by_protocol(self, streaming_protocol):
        for streaming_config in self.sources():
            stream_matcher = find_stream_matcher(streaming_config["file"])
            if stream_matcher.protocol == streaming_protocol:
                return to_non_drm_streaming_url(
                    streaming_config["file"], stream_matcher
                )
