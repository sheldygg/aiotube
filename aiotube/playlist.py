from typing import AsyncGenerator, List

from .client import HttpMethod, RequestClient
from .extractors import (extract_playlist_id, extract_playlist_info,
                         extract_video_id_from_playlist)
from .video import Video


class Playlist:
    def __init__(self, url: str) -> None:
        self.client = RequestClient("ANDROID")
        self._input_url = url
        self._playlist_id = None
        self._html = None
        self._playlist_info = None
        self._sidebar_info = None

    @property
    def playlist_id(self) -> str:
        if self._playlist_id:
            return self._playlist_id
        self._playlist_id = extract_playlist_id(self._input_url)
        return self._playlist_id

    @property
    def playlist_url(self) -> str:
        return f"https://www.youtube.com/playlist?list={self.playlist_id}"

    async def playlist_html(self) -> str:
        if self._html:
            return self._html
        request = await self.client.request(
            method=HttpMethod.GET, url=self.playlist_url
        )
        self._html = request.get("response").decode("utf-8")
        return self._html

    async def playlist_info(self) -> dict:
        if self._playlist_info:
            return self._playlist_info
        info = extract_playlist_info(await self.playlist_html())
        self._playlist_info = info
        return self._playlist_info

    async def sidebar_info(self) -> dict:
        if self._sidebar_info:
            return self._sidebar_info
        info = (await self.playlist_info())["sidebar"]["playlistSidebarRenderer"][
            "items"
        ]
        self._sidebar_info = info
        return self._sidebar_info

    async def video_urls(self) -> List[str]:
        result = []
        for video_id in extract_video_id_from_playlist(await self.playlist_info()):
            result.append(self.create_url(video_id))
        return result

    async def video_generator(self) -> AsyncGenerator[Video, None]:
        for video in await self.video_urls():
            yield Video(video)

    def create_url(self, video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"
