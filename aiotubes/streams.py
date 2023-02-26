import os

from datetime import datetime
from io import BytesIO
from typing import Callable, List, Optional, AsyncGenerator
from pydantic import BaseModel, HttpUrl

from .request import RequestClient
from .extractors import mime_type_codec
from .itags import get_format_profile
from .helpers import target_directory, safe_filename


class Stream(BaseModel, RequestClient):
    title: str
    author: str
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
    def resolution(self):
        return self.itag_profile["resolution"]

    @property
    def mime_type(self):
        mime_types, codecs = mime_type_codec(self.mimeType)
        return mime_types

    @property
    def codecs(self):
        mime_type, codecs = mime_type_codec(self.mimeType)
        return codecs

    @property
    def type(self):
        return self.mimeType.split("/")[0]

    @property
    def subtype(self):
        return self.mime_type.split("/")[1]

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

    async def filesize(self) -> int:
        response = await self.request(method="HEAD", url=self.url)
        return int(response.get("headers", {}).get("Content-Length"))

    async def _download(self) -> AsyncGenerator[bytes, None]:
        default_range_size = 9437184
        file_size: int = default_range_size
        downloaded = 0
        while downloaded < file_size:
            stop_pos = min(downloaded + default_range_size, file_size) - 1
            range_header = f"bytes={downloaded}-{stop_pos}"
            request = await self.request(
                method="GET", url=self.url, headers={"Range": range_header}
            )
            headers = request.get("headers")
            chunk = request.get("response")
            if file_size == default_range_size:
                content_range = headers.get("Content-Range")
                file_size = int(content_range.split("/")[1])
            downloaded += len(chunk)
            yield chunk

    async def download_buffer(self) -> BytesIO:
        io = BytesIO()
        async for chunk in self._download():
            io.write(chunk)
        io.seek(0)
        return io

    async def download_filepath(self, filename: str = None, output_path: str = None):
        file_path = self.get_file_path(
            filename=filename,
            output_path=output_path,
        )
        with open(file_path, "wb") as file:
            async for chunk in self._download():
                file.write(chunk)
        return file_path

    @property
    def default_filename(self) -> str:
        """Generate filename based on the video title.

        :rtype: str
        :returns:
            An os file system compatible filename.
        """
        filename = safe_filename(self.title)
        return f"{filename}.{self.subtype}"

    def get_file_path(
        self,
        filename: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        if not filename:
            filename = self.default_filename
        return os.path.join(target_directory(output_path), filename)


class StreamQuery:
    def __init__(self, fmt_streams: List[Stream]) -> None:
        self.fmt_streams = fmt_streams

    def filter(
        self,
        fps=None,
        res=None,
        resolution=None,
        mime_type=None,
        type=None,
        subtype=None,
        file_extension=None,
        abr=None,
        bitrate=None,
        video_codec=None,
        audio_codec=None,
        only_audio=None,
        only_video=None,
        progressive=None,
        adaptive=None,
        is_dash=None,
        custom_filter_functions=None,
    ):
        filters = []
        if res or resolution:
            filters.append(lambda s: s.resolution == (res or resolution))

        if fps:
            filters.append(lambda s: s.fps == fps)

        if mime_type:
            filters.append(lambda s: s.mime_type == mime_type)

        if type:
            filters.append(lambda s: s.type == type)

        if subtype or file_extension:
            filters.append(lambda s: s.subtype == (subtype or file_extension))

        if abr or bitrate:
            filters.append(lambda s: s.abr == (abr or bitrate))

        if video_codec:
            filters.append(lambda s: s.video_codec == video_codec)

        if audio_codec:
            filters.append(lambda s: s.audio_codec == audio_codec)

        if only_audio:
            filters.append(
                lambda s: (s.includes_audio_track and not s.includes_video_track),
            )

        if only_video:
            filters.append(
                lambda s: (s.includes_video_track and not s.includes_audio_track),
            )

        if progressive:
            filters.append(lambda s: s.is_progressive)

        if adaptive:
            filters.append(lambda s: s.is_adaptive)

        if custom_filter_functions:
            filters.extend(custom_filter_functions)

        if is_dash is not None:
            filters.append(lambda s: s.is_dash == is_dash)

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

    def get_highest_resolution(self) -> Optional[Stream]:
        return self.filter(progressive=True).order_by("resolution").last()
