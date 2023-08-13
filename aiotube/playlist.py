from typing import AsyncGenerator
from http import HTTPMethod

from .request import RequestClient
from .extractors import (extract_playlist_id, extract_playlist_info,
                         extract_video_id_from_playlist)
from .video import Video


class Playlist:
    def __init__(self, url: str) -> None:
        self.client = RequestClient()
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
            method=HTTPMethod.GET, url=self.playlist_url
        )
        self._html = request.get("response").decode("utf-8")
        return self._html

    async def playlist_info(self) -> dict:
        if not self._playlist_info:
            self._playlist_info = extract_playlist_info(await self.playlist_html())
        return self._playlist_info

    async def sidebar_info(self) -> dict:
        if not self._sidebar_info:
            self._sidebar_info = (await self.playlist_info())["sidebar"]["playlistSidebarRenderer"]["items"]
        return self._sidebar_info

    async def video_urls(self) -> list[str]:
        result = []
        for video_id in extract_video_id_from_playlist(await self.playlist_info()):
            result.append(self.create_url(video_id))
        return result

    async def video_generator(self) -> AsyncGenerator[Video, None]:
        for video in await self.video_urls():
            yield Video(video)

    @staticmethod
    def create_url(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"
