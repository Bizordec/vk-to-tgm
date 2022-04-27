import typing
from typing import Any, List, Optional

from pydantic.main import BaseModel
from telethon.tl.types import InputMediaPoll
from vkbottle_types.objects import AudioAudio, CallbackBase


class VkCallback(CallbackBase):
    object: Optional[Any] = None


class VkApiAudio(BaseModel):
    id: int
    owner_id: int
    track_covers: List[str]
    url: str
    artist: str
    title: str
    duration: int


class AudioPlaylistGenres(BaseModel):
    id: int
    name: str


class AudioPlaylistFollowed(BaseModel):
    playlist_id: int
    owner_id: int


class AudioPlaylistPhoto(BaseModel):
    width: int
    height: int
    photo_34: str
    photo_68: str
    photo_135: str
    photo_270: str
    photo_300: str
    photo_600: str
    photo_1200: str


class AudioPlaylistPermissions(BaseModel):
    play: bool
    share: bool
    edit: bool
    follow: bool
    delete: bool
    boom_download: bool


class AudioPlaylistMainArtist(BaseModel):
    name: str
    domain: str
    id: str


class VkApiAudioPlaylist(BaseModel):
    id: int
    owner_id: int
    type: int
    title: str
    description: str
    count: int
    followers: int
    plays: int
    create_time: int
    update_time: int
    genres: List[AudioPlaylistGenres]
    is_following: bool
    year: Optional[int] = None
    followed: Optional[AudioPlaylistFollowed] = None
    photo: Optional[AudioPlaylistPhoto] = None
    thumbs: Optional[List[AudioPlaylistPhoto]] = None
    permissions: AudioPlaylistPermissions
    subtitle_badge: bool
    play_button: bool
    access_key: str
    is_explicit: Optional[bool] = None
    main_artists: Optional[List[AudioPlaylistMainArtist]] = None
    album_type: str


class Document(BaseModel):
    url: str
    extension: str


class VttVideo(BaseModel):
    title: str
    url: str
    platform: Optional[str] = None
    is_live: bool = False


class AudioPlaylist(BaseModel):
    id: int
    owner_id: int
    access_key: Optional[str] = None
    full_id: str
    title: str
    description: str
    photo: Optional[str] = None
    audios: List[AudioAudio] = []


class VttMarket(BaseModel):
    id: int
    owner_id: int
    title: str


class VttLink(BaseModel):
    caption: str
    url: str


class Attachments:
    def __init__(self) -> None:
        self.audios: List[AudioAudio] = []
        self.audio_playlist: typing.Optional[AudioPlaylist] = None
        self.photos: List[str] = []
        self.documents: List[Document] = []
        self.videos: List[VttVideo] = []
        self.poll: typing.Optional[InputMediaPoll] = None
        self.market: typing.Optional[VttMarket] = None
        self.link: typing.Optional[VttLink] = None

    @property
    def length(self):
        return len(self.audios) + len(self.photos) + len(self.documents) + len(self.videos)
