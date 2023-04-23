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


class RequestClient:
    def __init__(self, client: str):
        self.context = default_clients[client]["context"]
        self.api_key = default_clients[client]["api_key"]
        self.base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}

    @property
    def base_params(self) -> dict:
        return {"key": self.api_key, "contentCheckOk": True, "racyCheckOk": True}

    @property
    def base_data(self) -> dict:
        return {"context": self.context}

    async def request(
        self,
        method: HttpMethod,
        url: str,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
    ):
        if params:
            params = urlencode(params)
        if headers:
            self.base_headers.update(headers)
        if data:
            data = json.dumps(data)
        async with ClientSession() as session:
            async with session.request(
                method=method.value,
                url=url,
                headers=self.base_headers,
                params=params,
                data=data,
            ) as response:
                headers = response.headers
                try:
                    response_data = await response.json()
                except ContentTypeError:
                    response_data = await response.read()
        return dict(response=response_data, headers=headers)
