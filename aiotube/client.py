import json
from enum import Enum
from urllib.parse import urlencode

from aiohttp import ClientSession
from aiohttp.client_exceptions import ContentTypeError

from aiotube.constants import default_clients


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    HEAD = "HEAD"


class RequestClient:
    def __init__(self, client: str):
        self.context = default_clients[client]["context"]
        self.api_key = default_clients[client]["api_key"]
        self.client_data = default_clients[client]

    @property
    def base_params(self) -> dict:
        return {"key": self.api_key, "contentCheckOk": True, "racyCheckOk": True}

    @property
    def base_data(self) -> dict:
        self.context.update(
            {
                "androidSdkVersion": 30,
                "userAgent": self.client_data.get("useragent"),
                "hl": "en",
                "timeZone": "UTC",
                "utcOffsetMinutes": 0
            }
        )
        data = {"context": self.context}
        data.update(
            {
                "params": "8AEB",
                "playbackContext": {
                    "contentPlaybackContext":
                        {"html5Preference": "HTML5_PREF_WANTS"}
                    },
                "contentCheckOk": True,
                "racyCheckOk": True}
        )
        return data

    @property
    def base_headers(self) -> dict:
        client_version = self.context.get("client").get("clientVersion")
        headers = {
            "User-Agent": self.client_data.get("useragent"),
            "accept-language": "en-US,en",
            "content-type": "application/json"
        }
        headers.update(
            {
                "X-YouTube-Client-Name": "3",
                "X-YouTube-Client-Version": client_version,
                "Origin": "https://www.youtube.com"
            }
        )
        return headers

    async def request(
        self,
        method: HttpMethod,
        url: str,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
    ):
        base_headers = self.base_headers
        if params:
            params = urlencode(params)
        if headers:
            base_headers.update(headers)
        if data:
            data = json.dumps(data).encode("utf-8")
        async with ClientSession() as session:
            async with session.request(
                method=method.value,
                url=url,
                headers=headers,
                params=params,
                data=data,
            ) as response:
                headers = response.headers
                try:
                    response_data = await response.json()
                except ContentTypeError:
                    response_data = await response.read()
        return dict(response=response_data, headers=headers)
