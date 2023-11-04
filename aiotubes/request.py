import json

from http import HTTPMethod
from urllib.parse import urlencode
from aiohttp import ClientSession
from aiohttp.client_exceptions import ContentTypeError

INNERTUBE_CLIENTS = {
    'web': {
        'INNERTUBE_API_KEY': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB',
                'clientVersion': '2.20220801.00.00',
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 1
    },
    'web_embedded': {
        'INNERTUBE_API_KEY': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_EMBEDDED_PLAYER',
                'clientVersion': '1.20220731.00.00',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 56
    },
    'web_music': {
        'INNERTUBE_API_KEY': 'AIzaSyC9XL3ZjWddXya6X74dJoCTL-WEYFDNX30',
        'INNERTUBE_HOST': 'music.youtube.com',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_REMIX',
                'clientVersion': '1.20220727.01.00',
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 67,
    },
    'web_creator': {
        'INNERTUBE_API_KEY': 'AIzaSyBUPetSUmoZL-OhlxA7wSac5XinrygCqMo',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'WEB_CREATOR',
                'clientVersion': '1.20220726.00.00',
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 62,
    },
    'android': {
        'INNERTUBE_API_KEY': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID',
                'clientVersion': '17.31.35',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip'
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 3,
        'REQUIRE_JS_PLAYER': False
    },
    'android_embedded': {
        'INNERTUBE_API_KEY': 'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_EMBEDDED_PLAYER',
                'clientVersion': '17.31.35',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.youtube/17.31.35 (Linux; U; Android 11) gzip'
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 55,
        'REQUIRE_JS_PLAYER': False
    },
    'android_music': {
        'INNERTUBE_API_KEY': 'AIzaSyAOghZGza2MQSZkY_zfZ370N-PUdXEo8AI',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_MUSIC',
                'clientVersion': '5.16.51',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.apps.youtube.music/5.16.51 (Linux; U; Android 11) gzip'
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 21,
        'REQUIRE_JS_PLAYER': False
    },
    'android_creator': {
        'INNERTUBE_API_KEY': 'AIzaSyD_qjV8zaaUMehtLkrKFgVeSX_Iqbtyws8',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'ANDROID_CREATOR',
                'clientVersion': '22.30.100',
                'androidSdkVersion': 30,
                'userAgent': 'com.google.android.apps.youtube.creator/22.30.100 (Linux; U; Android 11) gzip'
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 14,
        'REQUIRE_JS_PLAYER': False
    },
    'ios': {
        'INNERTUBE_API_KEY': 'AIzaSyB-63vPrdThhKuerbB2N_l7Kwwcxj6yUAc',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS',
                'clientVersion': '17.33.2',
                'deviceModel': 'iPhone14,3',
                'userAgent': 'com.google.ios.youtube/17.33.2 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 5,
        'REQUIRE_JS_PLAYER': False
    },
    'ios_embedded': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS_MESSAGES_EXTENSION',
                'clientVersion': '17.33.2',
                'deviceModel': 'iPhone14,3',
                'userAgent': 'com.google.ios.youtube/17.33.2 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 66,
        'REQUIRE_JS_PLAYER': False
    },
    'ios_music': {
        'INNERTUBE_API_KEY': 'AIzaSyBAETezhkwP0ZWA02RsqT1zu78Fpt0bC_s',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS_MUSIC',
                'clientVersion': '5.21',
                'deviceModel': 'iPhone14,3',
                'userAgent': 'com.google.ios.youtubemusic/5.21 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 26,
        'REQUIRE_JS_PLAYER': False
    },
    'ios_creator': {
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'IOS_CREATOR',
                'clientVersion': '22.33.101',
                'deviceModel': 'iPhone14,3',
                'userAgent': 'com.google.ios.ytcreator/22.33.101 (iPhone14,3; U; CPU iOS 15_6 like Mac OS X)'
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 15,
        'REQUIRE_JS_PLAYER': False
    },
    'mweb': {
        'INNERTUBE_API_KEY': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'MWEB',
                'clientVersion': '2.20220801.00.00',
            }
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 2
    },
    'tv_embedded': {
        'INNERTUBE_API_KEY': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
        'INNERTUBE_CONTEXT': {
            'client': {
                'clientName': 'TVHTML5_SIMPLY_EMBEDDED_PLAYER',
                'clientVersion': '2.0',
            },
        },
        'INNERTUBE_CONTEXT_CLIENT_NAME': 85
    },
}


class RequestClient:
    def __init__(self, client_name: str = "android_music"):
        self.client = INNERTUBE_CLIENTS[client_name]
        self.context = self.client["INNERTUBE_CONTEXT"]
        self.api_key = self.client["INNERTUBE_API_KEY"]

    def base_data(self) -> dict:
        data = {
            "context": self.context,
            "params": "8AEB",
            "playbackContext": {
                "contentPlaybackContext":
                    {"html5Preference": "HTML5_PREF_WANTS"}
            },
            "contentCheckOk": True,
            "racyCheckOk": True
        }
        return data

    def base_headers(self) -> dict:
        headers = {
            "User-Agent": self.context["client"].get("userAgent"),
            "accept-language": "en-US,en",
            "content-type": "application/json",
            "X-YouTube-Client-Name": "3",
            "X-YouTube-Client-Version": self.context["client"]["clientVersion"],
            "Origin": "https://www.youtube.com"
        }
        return headers

    async def request(
        self,
        method: HTTPMethod,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        data: dict | None = None
    ):
        base_headers = self.base_headers()
        if method == HTTPMethod.POST:
            base_data = self.base_data()
            if data:
                base_data.update(data)
            base_data = json.dumps(base_data).encode("utf-8")
        else:
            base_data = None
        if params:
            params = urlencode(params)
        if headers:
            base_headers.update(headers)
        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                data=base_data,
                params=params
            ) as resp:
                headers = resp.headers
                try:
                    response = await resp.json()
                except ContentTypeError:
                    response = await resp.read()
        return {"response": response, "headers": headers}
