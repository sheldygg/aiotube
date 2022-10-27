"""
This module implements the core developer interface for pytube.

The problem domain of the :class:`YouTube <YouTube> class focuses almost
exclusively on the developer interface. Pytube offloads the heavy lifting to
smaller peripheral modules and functions.

"""
import logging
from typing import Any, Callable, Dict, List, Optional

import aiotube
import aiotube.exceptions as exceptions
from aiotube import extract, request
from aiotube import Stream, StreamQuery
from aiotube.helpers import install_proxy
from aiotube.innertube import InnerTube
from aiotube.metadata import YouTubeMetadata
from aiotube.monostate import Monostate

logger = logging.getLogger(__name__)


class YouTube:
    """Core developer interface for pytube."""

    def __init__(
        self,
        url: str,
        on_progress_callback: Optional[Callable[[Any, bytes, int], None]] = None,
        on_complete_callback: Optional[Callable[[Any, Optional[str]], None]] = None,
        proxies: Dict[str, str] = None,
        use_oauth: bool = False,
        allow_oauth_cache: bool = True
    ):
        """Construct a :class:`YouTube <YouTube>`.

        :param str url:
            A valid YouTube watch URL.
        :param func on_progress_callback:
            (Optional) User defined callback function for stream download
            progress events.
        :param func on_complete_callback:
            (Optional) User defined callback function for stream download
            complete events.
        :param dict proxies:
            (Optional) A dict mapping protocol to proxy address which will be used by pytube.
        :param bool use_oauth:
            (Optional) Prompt the user to authenticate to YouTube.
            If allow_oauth_cache is set to True, the user should only be prompted once.
        :param bool allow_oauth_cache:
            (Optional) Cache OAuth tokens locally on the machine. Defaults to True.
            These tokens are only generated if use_oauth is set to True as well.
        """
        self._js: Optional[str] = None  # js fetched by js_url
        self._js_url: Optional[str] = None  # the url to the js, parsed from watch html

        self._vid_info: Optional[Dict] = None  # content fetched from innertube/player

        self._watch_html: Optional[str] = None  # the html of /watch?v=<video_id>
        self._embed_html: Optional[str] = None
        self._player_config_args: Optional[Dict] = None  # inline js in the html containing
        self._age_restricted: Optional[bool] = None

        self._fmt_streams: Optional[List[Stream]] = None

        self._initial_data = None
        self._metadata: Optional[YouTubeMetadata] = None

        # video_id part of /watch?v=<video_id>
        self.video_id = extract.video_id(url)

        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"

        # Shared between all instances of `Stream` (Borg pattern).
        self.stream_monostate = Monostate(
            on_progress=on_progress_callback, on_complete=on_complete_callback
        )

        if proxies:
            install_proxy(proxies)

        self._author = None
        self._title = None
        self._publish_date = None

        self.use_oauth = use_oauth
        self.allow_oauth_cache = allow_oauth_cache

    def __repr__(self):
        return f'<pytube.__main__.YouTube object: videoId={self.video_id}>'

    def __eq__(self, o: object) -> bool:
        # Compare types and urls, if they're same return true, else return false.
        return type(o) == type(self) and o.watch_url == self.watch_url

    @property
    async def watch_html(self):
        if self._watch_html:
            return self._watch_html
        self._watch_html = await request.get(url=self.watch_url)
        return self._watch_html

    @property
    async def embed_html(self):
        if self._embed_html:
            return self._embed_html
        self._embed_html = await request.get(url=self.embed_url)
        return self._embed_html

    @property
    async def age_restricted(self):
        if self._age_restricted:
            return self._age_restricted
        self._age_restricted = extract.is_age_restricted(await self.watch_html)
        return self._age_restricted

    @property
    async def js_url(self):
        if self._js_url:
            return self._js_url

        if await self.age_restricted:
            self._js_url = extract.js_url(await self.embed_html)
        else:
            self._js_url = extract.js_url(await self.watch_html)

        return self._js_url

    @property
    async def js(self):
        if self._js:
            return self._js

        # If the js_url doesn't match the cached url, fetch the new js and update
        #  the cache; otherwise, load the cache.
        if aiotube.__js_url__ != await self.js_url:
            self._js = await request.get(await self.js_url)
            aiotube.__js__ = self._js
            aiotube.__js_url__ = await self.js_url
        else:
            self._js = aiotube.__js__

        return self._js

    @property
    async def initial_data(self):
        if self._initial_data:
            return self._initial_data
        self._initial_data = extract.initial_data(await self.watch_html)
        return self._initial_data

    @property
    async def streaming_data(self):
        """Return streamingData from video info."""
        if 'streamingData' in await self.vid_info:
            data = await self.vid_info
            return data["streamingData"]
        else:
            self.bypass_age_gate()
            return self.vid_info['streamingData']

    @property
    async def fmt_streams(self):
        """Returns a list of streams if they have been initialized.

        If the streams have not been initialized, finds all relevant
        streams and initializes them.
        """
        await self.check_availability()
        if self._fmt_streams:
            return self._fmt_streams

        self._fmt_streams = []

        stream_manifest = extract.apply_descrambler(await self.streaming_data)

        # If the cached js doesn't work, try fetching a new js file
        # https://github.com/pytube/pytube/issues/1054
        try:
            extract.apply_signature(stream_manifest, await self.vid_info, await self.js)
        except exceptions.ExtractError:
            # To force an update to the js file, we clear the cache and retry
            self._js = None
            self._js_url = None
            aiotube.__js__ = None
            aiotube.__js_url__ = None
            extract.apply_signature(stream_manifest, await self.vid_info, await self.js)

        # build instances of :class:`Stream <Stream>`
        # Initialize stream objects
        for stream in stream_manifest:
            video = Stream(
                stream=stream,
                monostate=self.stream_monostate,
            )
            self._fmt_streams.append(video)

        self.stream_monostate.title = await self.title
        self.stream_monostate.duration = await self.length

        return self._fmt_streams

    async def check_availability(self):
        """Check whether the video is available.

        Raises different exceptions based on why the video is unavailable,
        otherwise does nothing.
        """
        status, messages = extract.playability_status(await self.watch_html)

        for reason in messages:
            if status == 'UNPLAYABLE':
                if reason == (
                    'Join this channel to get access to members-only content '
                    'like this video, and other exclusive perks.'
                ):
                    raise exceptions.MembersOnly(video_id=self.video_id)
                elif reason == 'This live stream recording is not available.':
                    raise exceptions.RecordingUnavailable(video_id=self.video_id)
                else:
                    raise exceptions.VideoUnavailable(video_id=self.video_id)
            elif status == 'LOGIN_REQUIRED':
                if reason == (
                    'This is a private video. '
                    'Please sign in to verify that you may see it.'
                ):
                    raise exceptions.VideoPrivate(video_id=self.video_id)
            elif status == 'ERROR':
                if reason == 'Video unavailable':
                    raise exceptions.VideoUnavailable(video_id=self.video_id)
            elif status == 'LIVE_STREAM':
                raise exceptions.LiveStreamError(video_id=self.video_id)

    @property
    async def vid_info(self):
        """Parse the raw vid info and return the parsed result.

        :rtype: Dict[Any, Any]
        """
        if self._vid_info:
            return self._vid_info

        innertube = InnerTube(use_oauth=self.use_oauth, allow_cache=self.allow_oauth_cache)

        innertube_response = await innertube.player(self.video_id)
        self._vid_info = innertube_response
        return self._vid_info

    async def bypass_age_gate(self):
        """Attempt to update the vid_info by bypassing the age gate."""
        innertube = InnerTube(
            client='ANDROID_EMBED',
            use_oauth=self.use_oauth,
            allow_cache=self.allow_oauth_cache
        )
        innertube_response = innertube.player(self.video_id)

        playability_status = innertube_response['playabilityStatus'].get('status', None)

        # If we still can't access the video, raise an exception
        # (tier 3 age restriction)
        if playability_status == 'UNPLAYABLE':
            raise exceptions.AgeRestrictedError(self.video_id)

        self._vid_info = innertube_response

    @property
    async def caption_tracks(self) -> List[aiotube.Caption]:
        """Get a list of :class:`Caption <Caption>`.

        :rtype: List[Caption]
        """
        raw_tracks = (
            self.vid_info.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        return [aiotube.Caption(track) for track in raw_tracks]

    @property
    async def captions(self) -> aiotube.CaptionQuery:
        """Interface to query caption tracks.

        :rtype: :class:`CaptionQuery <CaptionQuery>`.
        """
        return aiotube.CaptionQuery(self.caption_tracks)

    @property
    async def streams(self) -> StreamQuery:
        """Interface to query both adaptive (DASH) and progressive streams.

        :rtype: :class:`StreamQuery <StreamQuery>`.
        """
        await self.check_availability()
        return StreamQuery(await self.fmt_streams)

    @property
    async def thumbnail_url(self) -> str:
        """Get the thumbnail url image.

        :rtype: str
        """
        data = await self.vid_info
        thumbnail_details = (
            data.get("videoDetails", {})
            .get("thumbnail", {})
            .get("thumbnails")
        )
        if thumbnail_details:
            thumbnail_details = thumbnail_details[-1]  # last item has max size
            return thumbnail_details["url"]

        return f"https://img.youtube.com/vi/{self.video_id}/maxresdefault.jpg"

    @property
    async def publish_date(self):
        """Get the publish date.

        :rtype: datetime
        """
        if self._publish_date:
            return self._publish_date
        self._publish_date = extract.publish_date(await self.watch_html)
        return self._publish_date

    @publish_date.setter
    async def publish_date(self, value):
        """Sets the publish date."""
        self._publish_date = value

    @property
    async def title(self) -> str:
        """Get the video title.

        :rtype: str
        """
        if self._title:
            return self._title
        try:
            data = await self.vid_info
            self._title = data["videoDetails"]["title"]
        except KeyError:
            # Check_availability will raise the correct exception in most cases
            #  if it doesn't, ask for a report.
            self.check_availability()
            raise exceptions.PytubeError(
                (
                    f'Exception while accessing title of {self.watch_url}. '
                    'Please file a bug report at https://github.com/pytube/pytube'
                )
            )

        return self._title

    @title.setter
    def title(self, value):
        """Sets the title value."""
        self._title = value

    @property
    def description(self) -> str:
        """Get the video description.

        :rtype: str
        """
        return self.vid_info.get("videoDetails", {}).get("shortDescription")

    @property
    async def rating(self) -> float:
        """Get the video average rating.

        :rtype: float

        """
        return self.vid_info.get("videoDetails", {}).get("averageRating")

    @property
    async def length(self) -> int:
        """Get the video length in seconds.

        :rtype: int
        """
        data = await self.vid_info
        return int(data.get("videoDetails", {}).get("lengthSeconds"))

    @property
    async def views(self) -> int:
        """Get the number of the times the video has been viewed.

        :rtype: int
        """
        return int(self.vid_info.get("videoDetails", {}).get("viewCount"))

    @property
    async def author(self) -> str:
        """Get the video author.
        :rtype: str
        """
        if self._author:
            return self._author
        self._author = self.vid_info.get("videoDetails", {}).get(
            "author", "unknown"
        )
        return self._author

    @author.setter
    async def author(self, value):
        """Set the video author."""
        self._author = value

    @property
    async def keywords(self) -> List[str]:
        """Get the video keywords.

        :rtype: List[str]
        """
        return self.vid_info.get('videoDetails', {}).get('keywords', [])

    @property
    async def channel_id(self) -> str:
        """Get the video poster's channel id.

        :rtype: str
        """
        return self.vid_info.get('videoDetails', {}).get('channelId', None)

    @property
    async def channel_url(self) -> str:
        """Construct the channel url for the video's poster from the channel id.

        :rtype: str
        """
        return f'https://www.youtube.com/channel/{self.channel_id}'

    @property
    async def metadata(self) -> Optional[YouTubeMetadata]:
        """Get the metadata for the video.

        :rtype: YouTubeMetadata
        """
        if self._metadata:
            return self._metadata
        else:
            self._metadata = extract.metadata(self.initial_data)
            return self._metadata

    def register_on_progress_callback(self, func: Callable[[Any, bytes, int], None]):
        """Register a download progress callback function post initialization.

        :param callable func:
            A callback function that takes ``stream``, ``chunk``,
             and ``bytes_remaining`` as parameters.

        :rtype: None

        """
        self.stream_monostate.on_progress = func

    def register_on_complete_callback(self, func: Callable[[Any, Optional[str]], None]):
        """Register a download complete callback function post initialization.

        :param callable func:
            A callback function that takes ``stream`` and  ``file_path``.

        :rtype: None

        """
        self.stream_monostate.on_complete = func
