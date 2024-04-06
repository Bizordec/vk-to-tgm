from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from telethon.extensions import html
from telethon.utils import split_text as telethon_split_text

if TYPE_CHECKING:
    from telethon.tl.types import InputMediaPoll, TypeMessageEntity
    from vkbottle_types.objects import AudioAudio, WallGeo


MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024


def split_text(
    header_text: str,
    footer_text: str = "",
    *,
    is_caption: bool = False,
) -> list[tuple[str, list[TypeMessageEntity]]]:
    """Split `header_text` into multiple Telegram messages and add `footer_text` at the end of the first message.

    If `is_caption` is specified, smaller message length is used.

    Returns a list of a tuples consisting of (clean message, [message entities]).
    """
    tgm_limit = MAX_CAPTION_LENGTH if is_caption else MAX_MESSAGE_LENGTH

    p_header_text, p_header_entities = html.parse(header_text)
    p_footer_text, _ = html.parse(footer_text)
    main_text = header_text
    rest_texts = []

    strip_len = tgm_limit - len(p_footer_text)
    if len(p_header_text) > strip_len:
        s_header_text, s_header_entities = next(
            telethon_split_text(p_header_text, p_header_entities, limit=strip_len),
            ("", None),
        )
        if s_header_text and s_header_entities is not None:
            main_text = html.unparse(s_header_text, s_header_entities)
            main_text_offset = len(main_text)
            p_rest_text, p_rest_entities = html.parse(header_text[main_text_offset:])
            rest_texts = list(telethon_split_text(p_rest_text, p_rest_entities))

    main_text += footer_text
    return [html.parse(main_text), *rest_texts]


@dataclass
class VttDocument:
    url: str
    extension: str


@dataclass
class VttMarket:
    id: int
    owner_id: int
    title: str


@dataclass
class VttPoll:
    question: str
    answers: list[str]
    multiple_choice: bool


@dataclass
class VttLink:
    caption: str
    url: str


@dataclass
class VttAudioPlaylistId:
    owner_id: int
    playlist_id: int
    access_key: str | None = None


@dataclass
class VttText:
    header: str
    footer: str

    @property
    def message(self) -> list[tuple[str, list[TypeMessageEntity]]]:
        return split_text(header_text=self.header, footer_text=self.footer)

    @property
    def caption(self) -> list[tuple[str, list[TypeMessageEntity]]]:
        return split_text(header_text=self.header, footer_text=self.footer, is_caption=True)


@dataclass
class VttAudioPlaylist:
    id: int
    owner_id: int
    title: str
    text: VttText
    description: str
    access_key: str | None = None
    photo: str | None = None
    audios: list[AudioAudio] | None = None

    @property
    def full_id(self) -> str:
        return f"{self.owner_id}_{self.id}_{self.access_key}"


@dataclass
class VttVideo:
    title: str
    url: str
    platform: str | None = None
    is_live: bool = False


@dataclass
class VttAttachments:
    photos: list[str] = field(default_factory=list)
    audio_ids: list[str] = field(default_factory=list)
    audios: list[AudioAudio] = field(default_factory=list)
    audio_playlist_id: VttAudioPlaylistId | None = None
    audio_playlist: VttAudioPlaylist | None = None
    video_ids: list[str] = field(default_factory=list)
    videos: list[VttVideo] = field(default_factory=list)
    documents: list[VttDocument] = field(default_factory=list)
    poll: InputMediaPoll | None = None
    market: VttMarket | None = None
    link: VttLink | None = None
    geo: WallGeo | None = None


@dataclass
class VttMessage:
    text: VttText
    attachments: VttAttachments
    copy_history: list[VttMessage] = field(default_factory=list)
