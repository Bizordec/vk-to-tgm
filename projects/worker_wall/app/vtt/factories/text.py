from __future__ import annotations

import re
from typing import TYPE_CHECKING

from telethon.extensions import html
from vkbottle_types.objects import GroupsGroupFull, WallPostCopyright, WallPostType, WallWallpostFull

from app.config import _
from app.vtt.schemas import VttAttachments, VttLink, VttMarket, VttText

if TYPE_CHECKING:
    from vkbottle import ABCAPI

    from app.vk.schemas import AudioPlaylist


VK_BRACKETS_PATTERN = re.compile(r"\[(?P<url>[^\[|]+)\|(?P<title>[^\]]+)\]")
VK_ID_PATTERN = re.compile(r"(id|club)\d+")
VK_LINK_PATTERN = re.compile(r"(https?:\/\/)?(m\.)?vk\.com(\/[\w\-\.~:\/?#[\]@&()*+,;%=\"ёЁа-яА-Я]*)?")

SOURCE = _("SOURCE")
VK_POST = _("VK_POST")
VK_REPOST = _("VK_REPOST")
VK_PLAYLIST = _("VK_PLAYLIST")


def get_html_link(href: str, title: str) -> str:
    return f'<a href="{href}">{html.escape(title)}</a>'


def _convert_to_html_link(match: re.Match[str]) -> str:
    groupdict = match.groupdict()
    url = groupdict.get("url")
    if not url:
        return ""

    title = groupdict.get("title") or url

    if VK_ID_PATTERN.fullmatch(url):
        url = f"https://vk.com/{url}"

    if VK_LINK_PATTERN.fullmatch(url):
        return get_html_link(href=url, title=title)

    return f"[{url}|{title}]"


def convert_vk_links(text: str) -> str:
    """Convert VK links to HTML links."""
    safe_text = html.escape(text.encode("raw_unicode_escape").decode("unicode_escape"))
    return VK_BRACKETS_PATTERN.sub(_convert_to_html_link, safe_text)


class VttWallTextFactory:
    def __init__(
        self,
        vk_api: ABCAPI,
        wall: WallWallpostFull,
        attachments: VttAttachments,
        groups: list[GroupsGroupFull] | None = None,
        *,
        is_repost: bool = False,
    ) -> None:
        self._vk_api = vk_api
        self._wall = wall
        self._groups = groups or []
        self._attachments = attachments
        self._is_repost = is_repost

        self._message = ""
        self._caption = ""

    def _create_header_text(self) -> str:
        header_text = ""
        # Videos are at the top for the web page preview
        if self._attachments.videos:
            for video in self._attachments.videos:
                if video.platform or video.is_live:
                    header_text += f"\n📺 {get_html_link(href=video.url, title=video.title)}"

        if self._wall.text:
            processed_wall_text = convert_vk_links(self._wall.text)

            if header_text:
                header_text += "\n\n"
            header_text += processed_wall_text

        return header_text.lstrip()

    async def _get_commentator_link(self, commentator_id: int) -> str:
        if commentator_id < 0:
            group_id = str(abs(commentator_id))
            commentator = (await self._vk_api.groups.get_by_id(group_id=group_id))[0]
            commentator_href = f"https://vk.com/public{group_id}"
            commentator_fullname = commentator.name
        else:
            commentator = (await self._vk_api.users.get(user_ids=[commentator_id]))[0]
            commentator_href = f"https://vk.com/id{commentator_id}"
            commentator_fullname = f"{commentator.first_name} {commentator.last_name}"
        return f"\n\n📝 {get_html_link(commentator_href, commentator_fullname)}"

    def _get_market_link(self, market: VttMarket) -> str:
        owner_id = market.owner_id
        market_link = f"https://vk.com/market{owner_id}?w=product{owner_id}_{market.id}"
        return f"\n\n🛍️ {get_html_link(market_link, market.title)}"

    def _get_direct_link(self, link: VttLink) -> str:
        return f"\n\n🔗 {get_html_link(link.url, link.caption)}"

    def _get_copyright_link(self, wall_copyright: WallPostCopyright) -> str:
        return f'\n\n📎 {get_html_link(wall_copyright.link, f"{SOURCE}: {wall_copyright.name}")}'

    async def _get_signer_link(self, signer_id: int) -> str:
        signer = (await self._vk_api.users.get(user_ids=[signer_id]))[0]
        signer_fullname = f"{signer.first_name} {signer.last_name}"
        return f'\n\n👤 {get_html_link(f"https://vk.com/id{signer_id}", signer_fullname)}'

    async def _get_post_link(self, post_type: WallPostType) -> str:
        post_href = f"https://vk.com/wall{self._wall.owner_id}_{self._wall.id}"

        if not self._is_repost:
            return f"\n\n📌 {get_html_link(post_href, VK_POST)}"

        if post_type == WallPostType.VIDEO:
            post_href = f"https://vk.com/video{self._wall.owner_id}_{self._wall.id}"
        elif post_type == WallPostType.PHOTO:
            post_href = f"https://vk.com/photo{self._wall.owner_id}_{self._wall.id}"

        repost_text = VK_REPOST
        group_name = next((group.name for group in self._groups if group.id == abs(self._wall.owner_id)), None)
        if group_name:
            repost_text += f": {group_name}"
        return f"\n\n🔁 {get_html_link(post_href, repost_text)}"

    async def _create_footer_text(self) -> str:
        footer_text = ""

        post_type = self._wall.post_type
        if post_type == WallPostType.REPLY and self._wall.from_id:
            footer_text += await self._get_commentator_link(commentator_id=self._wall.from_id)

        if self._attachments.market:
            footer_text += self._get_market_link(market=self._attachments.market)

        if self._attachments.link:
            footer_text += self._get_direct_link(link=self._attachments.link)

        if self._wall.copyright:
            footer_text += self._get_copyright_link(wall_copyright=self._wall.copyright)

        if self._wall.signer_id:
            footer_text += await self._get_signer_link(signer_id=self._wall.signer_id)

        footer_text += await self._get_post_link(post_type=post_type)

        return footer_text

    async def create(self) -> VttText:
        return VttText(header=self._create_header_text(), footer=await self._create_footer_text())


class VttPlaylistTextFactory:
    def __init__(
        self,
        vk_api: ABCAPI,
        playlist: AudioPlaylist,
    ) -> None:
        self._vk_api = vk_api
        self._playlist = playlist

        self._message = ""
        self._caption = ""

    def _create_header_text(self) -> str:
        header_text = self._playlist.title
        if self._playlist.description:
            header_text += f"\n\n{convert_vk_links(self._playlist.description)}"

        return header_text

    async def _create_footer_text(self) -> str:
        post_href = f"https://vk.com/music/playlist/{self._playlist.owner_id}_{self._playlist.id}"
        if self._playlist.access_key:
            post_href += f"_{self._playlist.access_key}"
        return f"\n\n📌 {get_html_link(post_href, VK_PLAYLIST)}"

    async def create(self) -> VttText:
        return VttText(header=self._create_header_text(), footer=await self._create_footer_text())
