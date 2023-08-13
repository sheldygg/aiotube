import os

from typing import AsyncGenerator, Callable
from dataclasses import dataclass
from io import BytesIO
from http import HTTPMethod

from .request import RequestClient
from .itags import get_format_profile
from .helpers import safe_filename, target_directory
from .extractors import mime_type_codec

DEFAULT_RANGE_SIZE = 9437184


@dataclass
class Stream:
    title: str
    author: str
    request_client: RequestClient
    url: str
    itag: int
    mimeType: str
    bitrate: int
    lastModified: int
    quality: str
    projectionType: str
    approxDurationMs: str
    is_otf: bool
    highReplication: bool | None = None
    loudnessDb: float | None = None
    initRange: dict | None = None
    indexRange: dict | None = None
    colorInfo: dict | None = None
    width: int | None = None
    height: int | None = None
    contentLength: str | None = None
    fps: int | None = None
    qualityLabel: str | None = None
    averageBitrate: int | None = None
    audioQuality: str | None = None
    audioSampleRate: str | None = None
    audioChannels: int | None = None

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
        return bool(len(self.codecs) % 2)

    @property
    def is_progressive(self) -> bool:
        return not self.is_adaptive

    @property
    def includes_audio_track(self) -> bool:
        return self.is_progressive or self.type == "audio"

    @property
    def includes_video_track(self) -> bool:
        return self.is_progressive or self.type == "video"

    async def filesize(self) -> int:
        response = await self.request_client.request(method=HTTPMethod.HEAD, url=self.url)
        return int(response["headers"].get("Content-Length"))

    async def _download(self) -> AsyncGenerator[bytes, None]:
        file_size = await self.filesize()
        downloaded = 0
        while downloaded < file_size:
            stop_pos = min(downloaded + DEFAULT_RANGE_SIZE, file_size) - 1
            range_header = f"bytes={downloaded}-{stop_pos}"
            request = await self.request_client.request(
                method=HTTPMethod.GET, url=self.url, headers={"Range": range_header}
            )
            chunk = request["response"]
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
        filename = safe_filename(self.title)
        return f"{filename}.{self.subtype}"

    def get_file_path(
        self,
        filename: str | None = None,
        output_path: str | None = None,
    ) -> str:
        if not filename:
            filename = self.default_filename
        return os.path.join(target_directory(output_path), filename)


class StreamQuery:
    def __init__(self, fmt_streams: list[Stream]):
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

    def _filter(self, filters: list[Callable]) -> "StreamQuery":
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

    def get_audio_only(self, subtype: str = "mp4") -> Stream | None:
        return self.filter(only_audio=True, subtype=subtype).order_by("abr").last()

    def get_highest_resolution(self) -> Stream | None:
        return self.filter(progressive=True).order_by("resolution").last()
