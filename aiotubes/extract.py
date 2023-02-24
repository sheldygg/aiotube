import re
from typing import Dict, List, Tuple, Union
from urllib.parse import parse_qs


def extract_video_id(url: str) -> str:
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    result = re.search(pattern=pattern, string=url)
    return result.group(1)


def apply_descrambler(stream_data: Dict) -> Union[List, None]:
    if "url" in stream_data:
        return None
    formats = []
    if "formats" in stream_data.keys():
        formats.extend(stream_data["formats"])
    if "adaptiveFormats" in stream_data.keys():
        formats.extend(stream_data["adaptiveFormats"])
    for data in formats:
        if "url" not in data:
            if "signatureCipher" in data:
                cipher_url = parse_qs(data["signatureCipher"])
                data["url"] = cipher_url["url"][0]
                data["s"] = cipher_url["s"][0]
        data["is_otf"] = data.get("type") == "FORMAT_STREAM_TYPE_OTF"

    return formats


def mime_type_codec(mime_type_codec: str) -> Tuple[str, List[str]]:
    pattern = r"(\w+\/\w+)\;\scodecs=\"([a-zA-Z-0-9.,\s]*)\""
    regex = re.compile(pattern)
    results = regex.search(mime_type_codec)
    mime_type, codecs = results.groups()
    return mime_type, [c.strip() for c in codecs.split(",")]
