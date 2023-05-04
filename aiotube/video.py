from aiotube.client import HttpMethod, RequestClient
from aiotube.exceptions import (LiveStreamError, MembersOnly,
                                RecordingUnavailable, VideoPrivate,
                                VideoUnavailable)
from aiotube.extractors import (apply_descrambler, extract_video_id,
                                playability_status)
from aiotube.streams import Stream, StreamQuery
from aiotube.helpers import retry_if_none


class Video:
    def __init__(self, url: str):
        self.video_id = extract_video_id(url)
        self.base_url = "https://www.youtube.com/youtubei/v1"
        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self.client = RequestClient("ANDROID")
        self._html = None
        self._video_info = None
        self._fmt_streams = None

    def __repr__(self):
        return f"<aiotube.video.Video object: videoId={self.video_id}>"

    async def html(self):
        if self._html is None:
            self._html = (
                await self.client.request(method=HttpMethod.GET, url=self.watch_url)
            ).get("response")
        return self._html

    async def video_info(self):
        endpoint = f"{self.base_url}/player"
        query = {"videoId": self.video_id}
        query.update(self.client.base_params)
        data = self.client.base_data
        data.update(
            {"videoId": self.video_id}
        )
        response = await self.client.request(
            method=HttpMethod.POST,
            url=endpoint,
            params=query,
            data=data,
        )
        return response.get("response")

    @retry_if_none(max_retries=5)
    async def streaming_data(self):
        await self.check_availability()
        data = await self.video_info()
        if "streamingData" in data:
            return data["streamingData"]
        return await self.bypass_age_gate()

    async def fmt_streams(self):
        await self.check_availability()
        if self._fmt_streams:
            return self._fmt_streams
        self._fmt_streams = []
        stream_manifest = apply_descrambler(await self.streaming_data())
        video_title = await self.title()
        video_author = await self.author()
        for stream in stream_manifest:
            video = Stream(title=video_title, author=video_author, request_client=self.client, **stream)
            self._fmt_streams.append(video)
        return self._fmt_streams

    async def streams(self):
        return StreamQuery(await self.fmt_streams())

    async def bypass_age_gate(self):
        client = RequestClient("ANDROID_EMBED")
        endpoint = f"{self.base_url}/player"
        query = {"videoId": self.video_id}
        query.update(self.client.base_params)
        headers = {"Content-Type": "application/json"}
        response = await client.request(
            method=HttpMethod.POST,
            url=endpoint,
            params=query,
            headers=headers,
            data=self.client.base_data,
        )
        return response.get("response")

    async def title(self) -> str:
        """Get the video title."""
        await self.check_availability()
        return (await self.video_info()).get("videoDetails", {}).get("title")

    async def author(self) -> str:
        """Get the video author."""
        return (
            (await self.video_info()).get("videoDetails", {}).get("author", "unknown")
        )

    async def length(self) -> int:
        """Get the video length in seconds."""
        return int(
            (await self.video_info()).get("videoDetails", {}).get("lengthSeconds")
        )

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
