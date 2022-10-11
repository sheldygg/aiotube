import json

from aiohttp import ClientSession
from urllib import parse

class YouTube():
    def __init__(self):
        self.base_url = "https://www.youtube.com/youtubei/v1"
        self.api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        self.headers = {'User-Agent': 'Mozilla/5.0', 'accept-language': 'en-US,en', 'Content-Type': 'application/json'}
        self.data = b'{"context": {"client": {"clientName": "ANDROID", "clientVersion": "16.20"}}}'
    
    def base_params(self):
        return {
            'key': self.api_key,
            'contentCheckOk': True,
            'racyCheckOk': True
        }
    
    async def request(self, endpoint_url, headers, data):
        session = ClientSession()
        resp = await session.post(endpoint_url, headers=headers, data=data)
        datas = await resp.read()
        await session.close()
        return json.loads(datas)
    
    async def video_info(self, video_id):
        endpoint = f'{self.base_url}/player'
        query = {
            'videoId': video_id,
        }
        query.update(self.base_params())
        endpoint_url = f"{endpoint}?{parse.urlencode(query)}"
        return await self.request(endpoint_url, self.headers, self.data)
    
    async def get_data(self, url: str):
        video_id = url.split("/")[3]
        data = self.video_info(video_id)
        if 'streamingData' in data:
            return data
        return None