from http import HTTPMethod

from .request import RequestClient
from .extractors import extract_video_id, playability_status, apply_descrambler
from .exceptions import VideoPrivate, VideoUnavailable, LiveStreamError, MembersOnly, RecordingUnavailable
from .streams import Stream, StreamQuery


class Video:
    def __init__(self, video_url: str):
        self.request_client = RequestClient()
        self.video_id = extract_video_id(video_url)
        self.base_api_url = "https://www.youtube.com/youtubei/v1"
        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self._html: str | None = None
        self._video_data: dict | None = None
        self._fmt_streams: list | None = None

    async def html(self):
        if self._html is None:
            self._html = (await self.request_client.request(
                method=HTTPMethod.GET,
                url=self.watch_url
            ))["response"].decode()
        return self._html

    async def _player(self, request_client: RequestClient):
        endpoint = f"{self.base_api_url}/player"
        query = {"videoId": self.video_id}
        data = query
        return (await request_client.request(
            method=HTTPMethod.POST, url=endpoint, params=query, data=data
        ))["response"]

    async def video_info(self):
        if self._video_data is None:
            self._video_data = await self._player(self.request_client)
        return self._video_data

    async def streaming_data(self):
        data = await self.video_info()
        if streaming_data := data.get("streamingData"):
            return streaming_data
        else:
            bypassed_data = await self.bypass_age_gate()
            return bypassed_data["streamingData"]

    async def fmt_streams(self):
        await self.check_availability()
        if self._fmt_streams:
            return self._fmt_streams
        self._fmt_streams = []
        stream_manifest = apply_descrambler(await self.streaming_data())
        video_title = await self.title()
        video_author = await self.author()
        for stream in stream_manifest:
            self._fmt_streams.append(
                Stream(title=video_title, author=video_author, request_client=self.request_client, **stream)
            )
        return self._fmt_streams

    async def streams(self) -> StreamQuery:
        return StreamQuery(await self.fmt_streams())

    async def bypass_age_gate(self):
        request_client = RequestClient("android_embedded")
        self._video_data = await self._player(request_client)
        return self._video_data

    async def check_availability(self):
        html = await self.html()
        status, messages = playability_status(html)
        for reason in messages:
            if status == "UNPLAYABLE":
                if reason == (
                    "Join this channel to get access to members-only content "
                    "like this video, and other exclusive perks."
                ):
                    raise MembersOnly(video_id=self.video_id)
                elif reason == "This live stream recording is not available.":
                    raise RecordingUnavailable(video_id=self.video_id)
                else:
                    raise VideoUnavailable(video_id=self.video_id)
            elif status == "LOGIN_REQUIRED":
                if reason == (
                    "This is a private video. "
                    "Please sign in to verify that you may see it."
                ):
                    raise VideoPrivate(video_id=self.video_id)
            elif status == "ERROR":
                if reason == "Video unavailable":
                    raise VideoUnavailable(video_id=self.video_id)
            elif status == "LIVE_STREAM":
                raise LiveStreamError(video_id=self.video_id)

    async def title(self) -> str:
        """Get the video title."""
        await self.check_availability()
        return (await self.video_info()).get("videoDetails", {}).get("title", "untitled")

    async def author(self) -> str:
        """Get the video author."""
        return (
            (await self.video_info()).get("videoDetails", {}).get("author", "unknown")
        )

    async def length(self) -> int:
        """Get the video length in seconds."""
        return int(
            (await self.video_info()).get("videoDetails", {}).get("lengthSeconds", 0)
        )

    async def thumbnail(self) -> str:
        thumbnails = (await self.video_info()).get("videoDetails", {}).get("thumbnail", {}).get("thumbnails")
        if thumbnails:
            return thumbnails[-1]["url"]
        return f"https://img.youtube.com/vi/{self.video_id}/maxresdefault.jpg"
