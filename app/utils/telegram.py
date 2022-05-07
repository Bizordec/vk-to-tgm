import logging
from typing import List, Tuple, Union

from telethon.client.telegramclient import TelegramClient
from telethon.extensions import html
from telethon.hints import Entity
from telethon.tl.types import Chat, TypeInputPeer, TypeMessageEntity
from telethon.utils import split_text as telethon_split_text

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024


def split_text(header_text: str, footer_text: str = "", is_caption=False) -> List[Tuple[str, List[TypeMessageEntity]]]:
    tgm_limit = MAX_CAPTION_LENGTH if is_caption else MAX_MESSAGE_LENGTH

    p_header_text, p_header_entities = html.parse(header_text)
    p_footer_text, _ = html.parse(footer_text)
    main_text = header_text
    rest_texts = []

    newline_offset = 0
    if footer_text.startswith("\n\n"):
        newline_offset = 2

    strip_len = tgm_limit - newline_offset - len(p_footer_text)
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
    all_text = [html.parse(main_text)] + rest_texts
    return all_text


def get_html_link(href: str, title: str):
    return f'<a href="{href}">{html.escape(title)}</a>'


def get_message_link(entity: Entity, message_id) -> str:
    if isinstance(entity, Chat):
        return ""
    channel = entity.username
    if channel is None:
        channel = f"c/{entity.id}"
    message_link = f"https://t.me/{channel}/{message_id}"
    return message_link


async def get_entity_by_username(
    client: TelegramClient,
    channel_username: str,
) -> Union[TypeInputPeer, None]:
    entity = None
    try:
        entity = await client.get_input_entity(channel_username)
    except ValueError:
        logger.critical("Failed to get entity! If your channel is private, you can only use the id.")
    return entity


async def get_entity_by_id(
    client: TelegramClient,
    channel_id: int,
) -> Union[TypeInputPeer, None]:
    entity = None
    try:
        entity = await client.get_input_entity(channel_id)
    except ValueError:
        logger.critical("Failed to get entity! Add bot to your channel as an admin and try again.")
    return entity
