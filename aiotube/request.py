"""Implements a simple wrapper around urlopen."""
import json
import socket

from aiohttp import ClientSession

async def async_request(
    method,
    url,
    headers=None,
    data=None,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT
):
    base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}
    if headers:
        base_headers.update(headers)
    if data:
        if not isinstance(data, bytes):
            data = bytes(json.dumps(data), encoding="utf-8")
    if url.lower().startswith("http"):
        async with ClientSession() as session:
            async with session.request(method=method, url=url, headers=base_headers, data=data) as resp:
                return await resp.text(encoding="utf-8")


async def get(url, extra_headers=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    """Send an http GET request.

    :param str url:
        The URL to perform the GET request for.
    :param dict extra_headers:
        Extra headers to add to the request
    :rtype: str
    :returns:
        UTF-8 encoded string of response
    """
    if extra_headers is None:
        extra_headers = {}
    response = await async_request(method="GET", url=url, headers=extra_headers, timeout=timeout)
    return response


async def post(url, extra_headers=None, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    """Send an http POST request.

    :param str url:
        The URL to perform the POST request for.
    :param dict extra_headers:
        Extra headers to add to the request
    :param dict data:
        The data to send on the POST request
    :rtype: str
    :returns:
        UTF-8 encoded string of response
    """

    if extra_headers is None:
        extra_headers = {}
    if data is None:
        data = {}
    extra_headers.update({"Content-Type": "application/json"})
    response = await async_request(
        method="POST",
        url=url,
        headers=extra_headers,
        timeout=timeout
    )
    return response