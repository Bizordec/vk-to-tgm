import re
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlparse

from loguru import logger
from vkbottle_types.objects import (
    PhotosPhotoSizes,
    PhotosPhotoSizesType,
    WallWallpostAttachment,
    WallWallpostAttachmentType,
)

from app.config import settings
from app.vtt.schemas import VttAttachments, VttAudioPlaylistId, VttDocument, VttLink, VttMarket, VttPoll


class AttachmentHandler(ABC):
    def __init__(self, attachment: WallWallpostAttachment) -> None:
        self.attachment = attachment

    @abstractmethod
    def add_to_message(self, vtt_attachments: VttAttachments) -> None: ...


# Filter cropped photo sizes
PHOTO_SIZES = [
    size
    for size in PhotosPhotoSizesType
    if size
    not in (
        PhotosPhotoSizesType.O,
        PhotosPhotoSizesType.P,
        PhotosPhotoSizesType.Q,
        PhotosPhotoSizesType.R,
    )
]


class PhotoHandler(AttachmentHandler):
    def _get_photo_url(self, sizes: list[PhotosPhotoSizes] | None) -> str | None:
        if not sizes:
            return None

        max_photo = (None, None)
        for size in sizes:
            try:
                current_index = PHOTO_SIZES.index(size.type)
            except ValueError:
                continue
            if not max_photo[0] or (current_index > PHOTO_SIZES.index(max_photo[0])):
                max_photo = (size.type, size.url)
        return max_photo[1]

    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        photo = self.attachment.photo
        if not photo:
            return

        photo_url = self._get_photo_url(photo.sizes)
        if not photo_url:
            return

        vtt_attachments.photos.append(photo_url)


class AudioHandler(AttachmentHandler):
    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        audio = self.attachment.audio
        if not audio:
            return

        vtt_attachments.audio_ids.append(f"{audio.owner_id}_{audio.id}_{audio.access_key}")


class VideoHandler(AttachmentHandler):
    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        video = self.attachment.video
        if not video:
            return

        vtt_attachments.video_ids.append(f"{video.owner_id}_{video.id}_{video.access_key}")


class DocumentHandler(AttachmentHandler):
    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        document = self.attachment.doc
        if not (document and document.url):
            return

        vtt_attachments.documents.append(
            VttDocument(
                url=document.url,
                extension=document.ext,
            ),
        )


class MarketHandler(AttachmentHandler):
    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        market = self.attachment.market
        if not market:
            return

        vtt_attachments.market = VttMarket(
            id=market.id,
            owner_id=market.owner_id,
            title=market.title,
        )


class PollHandler(AttachmentHandler):
    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        poll = self.attachment.poll
        if not poll:
            return

        vtt_attachments.poll = VttPoll(
            question=poll.question,
            answers=[answer.text for answer in poll.answers],
            multiple_choice=poll.multiple,
        )


AUDIO_PLAYLIST_PATTERN = re.compile(r"(?P<owner_id>-?\d+)_(?P<playlist_id>\d+)")


class LinkHandler(AttachmentHandler):
    def _add_audio_playlist(self, link_query: dict[str, list[str]], vtt_attachments: VttAttachments) -> None:
        match = AUDIO_PLAYLIST_PATTERN.search(link_query["act"][0])
        if not match:
            return

        owner_id = match.group("owner_id")
        if not owner_id:
            return
        owner_id = int(owner_id)

        playlist_id = match.group("playlist_id")
        if not playlist_id:
            return
        playlist_id = int(playlist_id)

        access_key = None
        if "access_hash" in link_query:
            access_key = link_query["access_hash"][0]

        vtt_attachments.audio_playlist_id = VttAudioPlaylistId(
            owner_id=owner_id,
            playlist_id=playlist_id,
            access_key=access_key,
        )

    def add_to_message(self, vtt_attachments: VttAttachments) -> None:
        link = self.attachment.link
        if not link:
            return

        parsed_link = urlparse(link.url)

        # Not a VK link
        if parsed_link.netloc not in {"vk.com", "m.vk.com"}:
            vtt_attachments.link = VttLink(
                caption=link.caption or parsed_link.netloc,
                url=link.url,
            )
            return

        if parsed_link.netloc == "m.vk.com":
            parsed_link = parsed_link._replace(netloc="vk.com")

        # Playlist
        link_query = parse_qs(parsed_link.query)
        if settings.TGM_PL_CHANNEL_ID and "act" in link_query and link_query["act"][0].startswith("audio_playlist"):
            self._add_audio_playlist(link_query=link_query, vtt_attachments=vtt_attachments)
            return

        # Everything else
        vtt_attachments.link = VttLink(
            caption=parsed_link.netloc,
            url=parsed_link.geturl(),
        )


class DefaultHandler(AttachmentHandler):
    def add_to_message(self, _vtt_attachments: VttAttachments) -> None:
        logger.warning(f"Unknown attachment: {self.attachment}")


ATTACHMENT_HANDLERS: dict[WallWallpostAttachmentType, type[AttachmentHandler]] = {
    WallWallpostAttachmentType.PHOTO: PhotoHandler,
    WallWallpostAttachmentType.AUDIO: AudioHandler,
    WallWallpostAttachmentType.VIDEO: VideoHandler,
    WallWallpostAttachmentType.DOC: DocumentHandler,
    WallWallpostAttachmentType.MARKET: MarketHandler,
    WallWallpostAttachmentType.POLL: PollHandler,
    WallWallpostAttachmentType.LINK: LinkHandler,
}


def get_attachment_handler(attachment: WallWallpostAttachment) -> AttachmentHandler:
    return ATTACHMENT_HANDLERS.get(attachment.type, DefaultHandler)(attachment)
