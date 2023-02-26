from typing import Dict, List, Optional
from .request import RequestClient
from .constants import default_clients
from .extractors import apply_descrambler, extract_video_id
from .streams import Stream, StreamQuery


class Video(RequestClient):
    def __init__(self, url: str, client: str = "ANDROID") -> None:
        self.video_id = extract_video_id(url)
        self.api_key = default_clients[client]["api_key"]
        self.context = default_clients[client]["context"]
        self.base_url = "https://www.youtube.com/youtubei/v1"
        self._video_info: Optional[Dict] = None
        self._fmt_streams: Optional[List[Stream]] = None

    @property
    def base_params(self) -> Dict:
        return {"key": self.api_key, "contentCheckOk": True, "racyCheckOk": True}

    @property
    def base_data(self) -> Dict:
        return {"context": self.context}

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
        return (await self.video_info())["streamingData"]

    async def fmt_streams(self) -> List[Stream]:
        if self._fmt_streams:
            return self._fmt_streams
        self._fmt_streams = []
        stream_manifest = apply_descrambler(await self.streaming_data())
        video_title = await self.title
        video_author = await self.author
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
        return (await self.video_info()).get("videoDetails", {}).get("title")

    async def author(self) -> int:
        """Get the video author."""
        return (
            (await self.video_info()).get("videoDetails", {}).get("author", "unknown")
        )

    def __repr__(self):
        return f"<aiotubes.video.Video object: videoId={self.video_id}>"
