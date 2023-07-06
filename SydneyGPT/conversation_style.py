from enum import Enum

try:
    from typing import Literal, Union
except ImportError:
    from typing_extensions import Literal
from typing import Optional


class ConversationStyle(Enum):
    creative = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        # "responsible_ai_policy_235",
        "enablemm",
        "iycapbing",
        "iyxapbing",
        "enuaug",
        "dv3sugg",
        "iyoloxap",
        "iyoloneutral",
        "h3imaginative",
        "travelansgnd",
        "clgalileo",
        "responseos",
        "e2ecachewrite",
        "nodlcpcwrite",
        "cachewriteext",
        "gencontentv3",
        "nojbfedge"
    ]
    balanced = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "galileo",
        "dv3sugg",
        "responseos",
        "e2ecachewrite",
        "cachewriteext",
        "nodlcpcwrite",
        "travelansgnd",
    ]
    precise = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "galileo",
        "dv3sugg",
        "responseos",
        "e2ecachewrite",
        "cachewriteext",
        "nodlcpcwrite",
        "travelansgnd",
        "h3precise",
        "clgalileo",
    ]


CONVERSATION_STYLE_TYPE = Optional[
    Union[ConversationStyle, Literal["creative", "balanced", "precise"]]
]
