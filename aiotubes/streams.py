from datetime import datetime
from io import BytesIO
from typing import Callable, List, Optional
from aiohttp import ClientSession
from pydantic import BaseModel, HttpUrl

from .extract import mime_type_codec
from .itags import get_format_profile


class Stream(BaseModel):
    url: HttpUrl
    itag: int
    mimeType: str
    bitrate: int
    width: Optional[int]
    height: Optional[int]
    lastModifed: Optional[datetime]
    contentLength: Optional[str]
    quality: str
    fps: Optional[int]
    qualityLabel: Optional[str]
    projectionType: str
    averageBitrate: Optional[int]
    audioQuality: Optional[str]
    approxDurationMs: str
    audioSampleRate: Optional[str]
    audioChannels: Optional[int]
    is_otf: bool

    @property
    def itag_profile(self):
        return get_format_profile(self.itag)

    @property
    def abr(self):
        return self.itag_profile["abr"]

    @property
    def codecs(self):
        mime_type, codecs = mime_type_codec(self.mimeType)
        return codecs

    @property
    def type(self):
        return self.mimeType.split("/")[0]

    @property
    def subtype(self):
        return self.mimeType.split("/")[1]

    @property
    def is_adaptive(self) -> bool:
        """Whether the stream is DASH.

        :rtype: bool
        """
        return bool(len(self.codecs) % 2)

    @property
    def is_progressive(self) -> bool:
        """Whether the stream is progressive.

        :rtype: bool
        """
        return not self.is_adaptive

    @property
    def includes_audio_track(self) -> bool:
        """Whether the stream only contains audio.

        :rtype: bool
        """
        return self.is_progressive or self.type == "audio"

    @property
    def includes_video_track(self) -> bool:
        """Whether the stream only contains video.

        :rtype: bool
        """
        return self.is_progressive or self.type == "video"
    
    async def download_buffer(self, buffer: BytesIO = None) -> BytesIO:
        chunk_size = 16384
        if buffer:
            io = buffer
        else:
            io = BytesIO()
        async with ClientSession() as session:
            async with session.get(self.url) as response:
                async for data in response.content.iter_chunked(chunk_size):
                    io.write(data)
        io.seek(0)
        return io


class StreamQuery:
    def __init__(self, fmt_streams: List[Stream]) -> None:
        self.fmt_streams = fmt_streams

    def filter(self, only_audio=False, subtype=None):
        filters = []
        if only_audio:
            filters.append(
                lambda s: (s.includes_audio_track and not s.includes_video_track),
            )

        return self._filter(filters)

    def _filter(self, filters: List[Callable]) -> "StreamQuery":
        fmt_streams = self.fmt_streams
        for filter_lambda in filters:
            fmt_streams = filter(filter_lambda, fmt_streams)
        return StreamQuery(list(fmt_streams))

    def order_by(self, attribute_name: str) -> "StreamQuery":
        has_attribute = [
            s for s in self.fmt_streams if getattr(s, attribute_name) is not None
        ]
        if has_attribute and isinstance(getattr(has_attribute[0], attribute_name), str):
            try:
                return StreamQuery(
                    sorted(
                        has_attribute,
                        key=lambda s: int(
                            "".join(filter(str.isdigit, getattr(s, attribute_name)))
                        ),  # type: ignore  # noqa: E501
                    )
                )
            except ValueError:
                pass
        return StreamQuery(
            sorted(has_attribute, key=lambda s: getattr(s, attribute_name))
        )

    def last(self):
        try:
            return self.fmt_streams[-1]
        except IndexError:
            pass

    def get_audio_only(self, subtype: str = "mp4") -> Optional[Stream]:
        return self.filter(only_audio=True, subtype=subtype).order_by("abr").last()
