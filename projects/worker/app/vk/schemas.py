from pydantic import BaseModel


class AudioPlaylistPhoto(BaseModel):
    photo_1200: str


class AudioPlaylistMainArtist(BaseModel):
    name: str


class AudioPlaylist(BaseModel):
    id: int
    owner_id: int
    access_key: str
    title: str
    description: str
    count: int
    photo: AudioPlaylistPhoto | None = None
    thumbs: list[AudioPlaylistPhoto] | None = None
    main_artists: list[AudioPlaylistMainArtist] | None = None
