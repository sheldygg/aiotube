from typing import Dict, List, Optional

from .constants import default_clients
from .exceptions import (AgeRestrictedError, LiveStreamError, MembersOnly,
                         RecordingUnavailable, VideoPrivate, VideoUnavailable)
from .extractors import apply_descrambler, extract_video_id, playability_status
from .request import RequestClient
from .streams import Stream, StreamQuery


class Video(RequestClient):
    def __init__(self, url: str, client: str = "ANDROID") -> None:
        self.video_id = extract_video_id(url)
        self.api_key = default_clients[client]["api_key"]
        self.context = default_clients[client]["context"]
        self.base_url = "https://www.youtube.com/youtubei/v1"
        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self._video_info: Optional[Dict] = None
        self._fmt_streams: Optional[List[Stream]] = None
        self._html = None

    @property
    def base_params(self) -> Dict:
        return {"key": self.api_key, "contentCheckOk": True, "racyCheckOk": True}

    @property
    def base_data(self) -> Dict:
        return {"context": self.context}

    async def html(self):
        if self._html:
            return self._html
        return (await self.request(method="GET", url=self.watch_url)).get("response")

    async def video_info(self) -> Dict:
        if self._video_info:
            return self._video_info
        endpoint = f"{self.base_url}/player"
        query = {
            "videoId": self.video_id,
        }
        query.update(self.base_params)
        headers = {"Content-Type": "application/json"}
        result = await self.request(
            method="POST",
            url=endpoint,
            params=query,
            headers=headers,
            data=self.base_data,
        )
        self._video_info = result.get("response")
        return self._video_info

    async def streaming_data(self) -> Dict:
        await self.check_availability()
        data = await self.video_info()
        if "streamingData" in data:
            return data["streamingData"]
        else:
            return await self.bypass_age_gate()

    async def fmt_streams(self) -> List[Stream]:
        await self.check_availability()
        if self._fmt_streams:
            return self._fmt_streams
        self._fmt_streams = []
        stream_manifest = apply_descrambler(await self.streaming_data())
        video_title = await self.title()
        video_author = await self.author()
        for stream in stream_manifest:
            video = Stream(title=video_title, author=video_author, **stream)
            self._fmt_streams.append(video)
        return self._fmt_streams

    async def streams(self) -> StreamQuery:
        return StreamQuery(await self.fmt_streams())

    async def length(self) -> int:
        """Get the video length in seconds."""
        return int(
            (await self.video_info()).get("videoDetails", {}).get("lengthSeconds")
        )

    async def title(self) -> int:
        """Get the video title."""
        await self.check_availability()
        return (await self.video_info()).get("videoDetails", {}).get("title")

    async def author(self) -> int:
        """Get the video author."""
        return (
            (await self.video_info()).get("videoDetails", {}).get("author", "unknown")
        )

    async def bypass_age_gate(self):
        self.api_key = default_clients["ANDROID_EMBED"]["api_key"]
        self.context = default_clients["ANDROID_EMBED"]["context"]
        data = await self.video_info()
        playability_status = data["playabilityStatus"].get("status", None)
        if playability_status == "UNPLAYABLE":
            raise AgeRestrictedError(self.video_id)

    async def check_availability(self):
        html = (await self.html()).decode()
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

    def __repr__(self):
        return f"<aiotubes.video.Video object: videoId={self.video_id}>"
