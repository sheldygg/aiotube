import json
from urllib.parse import urlencode
from aiohttp import ClientSession


class RequestClient:
    async def request(
        self,
        method: str = "GET",
        url: str = "",
        headers: dict = None,
        params: dict = None,
        data: dict = None,
    ) -> dict:
        if params:
            params = urlencode(params)
        base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}
        if headers:
            base_headers.update(headers)
        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=base_headers,
                params=params,
                data=json.dumps(data),
            ) as resp:
                headers = resp.headers
                if headers.get("Content-Type") == "application/json; charset=UTF-8":
                    response: dict = await resp.json()
                else:
                    response = await resp.read()
        return dict(response=response, headers=headers)
