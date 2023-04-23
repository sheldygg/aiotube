# AIOTUBE

**aiotube** Asynchronous YouTube API


### Example

```python
import asyncio

from aiotube import Video

async def main():
    client = Video("https://www.youtube.com/watch?v=MZ-cvXEvYI8")
    stream = (await client.streams()).get_audio_only()
    await stream.download_filepath(filename="yeat.mp3")
    
asyncio.run(main())

```
