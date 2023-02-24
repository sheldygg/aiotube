import re
import json

from io import BytesIO
from urllib.parse import urlencode
from aiohttp import ClientSession
from .constants import default_clients


def extract_video_id(url: str) -> str:
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    result = re.search(pattern=pattern, string=url)
    return result.group(1)


class Client:
    def __init__(self, url: str, client: str = "ANDROID") -> None:
        self.video_id = extract_video_id(url)
        self.api_key = default_clients[client]["api_key"]
        self.context = default_clients[client]["context"]
        self.base_url = "https://www.youtube.com/youtubei/v1"

    @property
    def base_params(self) -> dict:
        return {"key": self.api_key, "contentCheckOk": True, "racyCheckOk": True}

    @property
    def base_data(self) -> dict:
        return {"context": self.context}

    async def video_info(self) -> dict:
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
        return result

    async def streaming_data(self):
        return (await self.video_info())["streamingData"]

    async def request(
        self,
        method: str = "GET",
        url: str = "",
        headers: dict = None,
        params: dict = None,
        data: dict = None,
    ) -> dict:
        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=urlencode(params),
                data=json.dumps(data),
            ) as resp:
                response: dict = await resp.json()
        return response

    async def download_file(self, url: str) -> BytesIO:
        chunk_size = 16384
        io = BytesIO()
        async with ClientSession() as session:
            async with session.get(url) as response:
                async for data in response.content.iter_chunked(chunk_size):
                    io.write(data)
        io.seek(0)
        return io
