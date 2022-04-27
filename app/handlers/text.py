import html
import re
from typing import List, Optional, Tuple

from telethon.tl.types import TypeMessageEntity
from vkbottle.api.api import API
from vkbottle_types.objects import GroupsGroupFull, WallPostType, WallWallpostFull

from app.config import _
from app.schemas.vk import Attachments, AudioPlaylist
from app.utils.telegram import get_html_link, split_text

link_pattern = re.compile(r"\[(?P<url>[^\[|]+)\|(?P<title>[^\]]+)\]")
vk_id_pattern = re.compile(r"(id|club)\d+")
vk_link_pattern = re.compile(r"(https?:\/\/)?(m\.)?vk\.com(\/[\w\-\.~:\/?#[\]@&()*+,;%=\"ёЁа-яА-Я]*)?")

SOURCE = _("SOURCE")
VK_POST = _("VK_POST")
VK_REPOST = _("VK_REPOST")
VK_PLAYLIST = _("VK_PLAYLIST")


class BaseTextHandler:
    def _convert_to_html_link(self, match: re.Match):
        groupdict = match.groupdict()
        url: str = groupdict.get("url")
        title: str = groupdict.get("title")

        if vk_id_pattern.fullmatch(url):
            url = "https://vk.com/" + url

        if vk_link_pattern.fullmatch(url):
            return f'<a href="{url}">{title}</a>'

        return f"[{url}|{title}]"

    def convert_vk_links(self, text: str):
        # Convert VK links to HTML links
        safe_text = html.escape(text.encode("raw_unicode_escape").decode("unicode_escape"))
        return link_pattern.sub(self._convert_to_html_link, safe_text)


class WallTextHandler(BaseTextHandler):
    def __init__(
        self,
        vk_api: API,
        wall: WallWallpostFull,
        attachments: Attachments,
        is_repost=False,
        groups: Optional[List[GroupsGroupFull]] = None,
    ) -> None:
        self._vk_api = vk_api
        self._wall = wall
        self._groups = groups or []
        self._attachments = attachments
        self._is_repost = is_repost

        self.header = ""
        self.footer = ""

        self._message = ""
        self._caption = ""

    async def process_text(self) -> None:
        wall = self._wall
        attachments = self._attachments

        header_text = ""
        footer_text = ""

        # Videos are at the top for the web page preview
        if attachments.videos:
            for video in attachments.videos:
                if video.platform or video.is_live:
                    header_text += f"\n📺 {get_html_link(video.url, video.title)}"

        if wall.text:
            processed_wall_text = self.convert_vk_links(wall.text)

            if header_text:
                header_text += "\n\n"
            header_text += processed_wall_text

        post_type = wall.post_type
        if post_type == WallPostType.REPLY:
            commentator_id = wall.from_id
            if commentator_id < 0:
                group_id = str(abs(commentator_id))
                commentator = (await self._vk_api.groups.get_by_id(group_id=group_id))[0]
                commentator_href = f"https://vk.com/public{group_id}"
                commentator_fullname = commentator.name
            else:
                commentator = (await self._vk_api.users.get(user_ids=[commentator_id]))[0]
                commentator_href = f"https://vk.com/id{commentator_id}"
                commentator_fullname = f"{commentator.first_name} {commentator.last_name}"
            footer_text += f"\n\n📝 {get_html_link(commentator_href, commentator_fullname)}"

        if attachments.market:
            att_market = attachments.market
            owner_id = att_market.owner_id
            market_link = f"https://vk.com/market{owner_id}?w=product{owner_id}_{att_market.id}"
            footer_text += f"\n\n🛍️ {get_html_link(market_link, att_market.title)}"

        if attachments.link:
            att_link = attachments.link
            footer_text += f"\n\n🔗 {get_html_link(att_link.url, att_link.caption)}"

        if wall.copyright:
            copyright = wall.copyright
            footer_text += f'\n\n📎 {get_html_link(copyright.link, f"{SOURCE}: {copyright.name}")}'

        if wall.signer_id:
            signer_id = wall.signer_id
            signer = (await self._vk_api.users.get(user_ids=[signer_id]))[0]
            signer_fullname = f"{signer.first_name} {signer.last_name}"
            footer_text += f'\n\n👤 {get_html_link(f"https://vk.com/id{signer_id}", signer_fullname)}'

        vk_link = ""
        post_href = f"https://vk.com/wall{wall.owner_id}_{wall.id}"
        if self._is_repost:
            if post_type == WallPostType.VIDEO:
                post_href = f"https://vk.com/video{wall.owner_id}_{wall.id}"
            elif post_type == WallPostType.PHOTO:
                post_href = f"https://vk.com/photo{wall.owner_id}_{wall.id}"

            repost_text = VK_REPOST
            group_name = next((group.name for group in self._groups if group.id == abs(wall.owner_id)), None)
            if group_name:
                repost_text += f": {group_name}"
            vk_link = f"\n\n🔁 {get_html_link(post_href, repost_text)}"
        else:
            vk_link = f"\n\n📌 {get_html_link(post_href, VK_POST)}"
        footer_text += vk_link

        self.header = header_text
        self.footer = footer_text

    @property
    def message(self) -> List[Tuple[str, List[TypeMessageEntity]]]:
        return split_text(self.header, self.footer)

    @property
    def caption(self) -> List[Tuple[str, List[TypeMessageEntity]]]:
        return split_text(self.header, self.footer, is_caption=True)


class PlaylistTextHandler(BaseTextHandler):
    def __init__(
        self,
        vk_api: API,
        playlist: AudioPlaylist,
    ) -> None:
        self._vk_api = vk_api
        self._playlist = playlist

        self.header = ""
        self.footer = ""

        self._caption = ""

    async def process_text(self) -> None:
        header = self._playlist.title
        if self._playlist.description:
            header += f"\n\n{self.convert_vk_links(self._playlist.description)}"

        post_href = f"https://vk.com/music/playlist/{self._playlist.owner_id}_{self._playlist.id}"
        if self._playlist.access_key:
            post_href += f"_{self._playlist.access_key}"
        vk_link = f"\n\n📌 {get_html_link(post_href, VK_PLAYLIST)}"

        self.header = header
        self.footer = vk_link

    @property
    def caption(self) -> List[Tuple[str, List[TypeMessageEntity]]]:
        return split_text(self.header, self.footer, is_caption=True)
