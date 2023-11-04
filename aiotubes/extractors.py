import ast
import json
import re
from urllib.parse import parse_qs, urlparse

from aiotube.exceptions import HTMLParseError, RegexMatchError


def extract_video_id(url: str):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    result = re.search(pattern=pattern, string=url)
    return result.group(1)


def find_object_from_startpoint(html, start_point):
    html = html[start_point:]
    if html[0] not in ["{", "["]:
        raise HTMLParseError(f"Invalid start point. Start of HTML:\n{html[:20]}")

    # First letter MUST be an open brace, so we put that in the stack,
    # and skip the first character.
    stack = [html[0]]
    i = 1

    context_closers = {"{": "}", "[": "]", '"': '"'}

    while i < len(html):
        if len(stack) == 0:
            break
        curr_char = html[i]
        curr_context = stack[-1]

        # If we've reached a context closer, we can remove an element off the stack
        if curr_char == context_closers[curr_context]:
            stack.pop()
            i += 1
            continue

        # Strings require special context handling because they can contain
        #  context openers *and* closers
        if curr_context == '"':
            # If there's a backslash in a string, we skip a character
            if curr_char == "\\":
                i += 2
                continue
        else:
            # Non-string contexts are when we need to look for context openers.
            if curr_char in context_closers.keys():
                stack.append(curr_char)

        i += 1

    full_obj = html[:i]
    return full_obj  # noqa: R504


def parse_for_object_from_startpoint(html, start_point):
    full_obj = find_object_from_startpoint(html, start_point)
    try:
        return json.loads(full_obj)
    except json.decoder.JSONDecodeError:
        try:
            return ast.literal_eval(full_obj)
        except (ValueError, SyntaxError):
            raise HTMLParseError("Could not parse object.")


def parse_for_object(html: str, preceding_regex: str):
    regex = re.compile(preceding_regex)
    result = regex.search(html)
    if not result:
        raise HTMLParseError(f"No matches for regex {preceding_regex}")

    start_index = result.end()
    return parse_for_object_from_startpoint(html, start_index)


def initial_player_response(watch_html: str) -> str | dict:
    patterns = [
        r"window\[['\"]ytInitialPlayerResponse['\"]]\s*=\s*",
        r"ytInitialPlayerResponse\s*=\s*",
    ]
    for pattern in patterns:
        try:
            return parse_for_object(watch_html, pattern)
        except HTMLParseError:
            pass

    raise RegexMatchError(
        caller="initial_player_response", pattern="initial_player_response_pattern"
    )


def playability_status(watch_html: str):
    player_response = initial_player_response(watch_html)
    status_dict = player_response.get("playabilityStatus", {})
    if "liveStreamability" in status_dict:
        return "LIVE_STREAM", "Video is a live stream."
    if "status" in status_dict:
        if "reason" in status_dict:
            return status_dict["status"], [status_dict["reason"]]
        if "messages" in status_dict:
            return status_dict["status"], status_dict["messages"]
    return None, [None]


def mime_type_codec(mime_type_codec: str) -> tuple[str, list[str]]:
    pattern = r"(\w+\/\w+)\;\scodecs=\"([a-zA-Z-0-9.,\s]*)\""
    regex = re.compile(pattern)
    results = regex.search(mime_type_codec)
    mime_type, codecs = results.groups()
    return mime_type, [c.strip() for c in codecs.split(",")]


def apply_descrambler(stream_data: dict) -> list | None:
    if "url" in stream_data:
        return None
    _formats = []
    if formats := stream_data.get("formats"):
        _formats.extend(formats)
    if avaptive_formats := stream_data.get("adaptiveFormats"):
        _formats.extend(avaptive_formats)
    for data in _formats:
        if not data.get("url"):
            if "signatureCipher" in data:
                cipher_url = parse_qs(data["signatureCipher"])
                data["url"] = cipher_url["url"][0]
                data["s"] = cipher_url["s"][0]
        data["is_otf"] = data.get("type") == "FORMAT_STREAM_TYPE_OTF"

    return _formats


def extract_playlist_id(url: str) -> str:
    parsed = urlparse(url)
    return parse_qs(parsed.query)["list"][0]


def extract_playlist_info(watch_html: str) -> str | dict:
    patterns = [r"window\[['\"]ytInitialData['\"]]\s*=\s*", r"ytInitialData\s*=\s*"]
    for pattern in patterns:
        try:
            return parse_for_object(watch_html, pattern)
        except HTMLParseError:
            pass

    raise RegexMatchError(
        caller="extract_playlist_info", pattern="extract_playlist_info_pattern"
    )


def extract_video_id_from_playlist(playlist_info: dict):
    section_contents = playlist_info["contents"]["twoColumnBrowseResultsRenderer"][
        "tabs"
    ][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
    important_content = section_contents[0]["itemSectionRenderer"]["contents"][0][
        "playlistVideoListRenderer"
    ]
    videos = important_content["contents"]
    video_ids = list(map(lambda x: x["playlistVideoRenderer"]["videoId"], videos))
    return video_ids
