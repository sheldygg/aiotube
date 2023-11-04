from re import Pattern


class AiotubeError(BaseException):
    """Base Exception"""


class HTMLParseError(AiotubeError):
    pass


class RegexMatchError(AiotubeError):
    """Regex pattern did not return any matches."""

    def __init__(self, caller: str, pattern: str | Pattern):
        """
        :param str caller:
            Calling function
        :param str pattern:
            Pattern that failed to match
        """
        super().__init__(f"{caller}: could not find match for {pattern}")
        self.caller = caller
        self.pattern = pattern


class VideoUnavailable(AiotubeError):
    """Base video unavailable error."""

    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.error_string)

    @property
    def error_string(self):
        return f"{self.video_id} is unavailable"


class MembersOnly(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f"{self.video_id} is a members-only video"


class RecordingUnavailable(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f"{self.video_id} does not have a live stream recording available"


class LiveStreamError(VideoUnavailable):
    """Video is a live stream."""

    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f"{self.video_id} is streaming live and cannot be loaded"


class VideoPrivate(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f"{self.video_id} is a private video"
