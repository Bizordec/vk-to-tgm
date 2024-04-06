from loguru import logger
from vkbottle_types.objects import AudioAudio

from app.services.vk import VkService
from app.vk.schemas import AudioPlaylist
from app.vtt.factories.text import VttPlaylistTextFactory
from app.vtt.schemas import VttAudioPlaylist, VttText


class VttPlaylistFactory:
    def __init__(self, vk_service: VkService) -> None:
        self.vk_service = vk_service

    def _get_title(self, playlist: AudioPlaylist) -> str:
        full_title = playlist.title
        if playlist.main_artists:
            artists = ", ".join(artist.name for artist in playlist.main_artists)
            full_title = f"{artists} - {playlist.title}"
        return full_title

    def _get_photo(self, playlist: AudioPlaylist) -> str | None:
        photo = None

        if playlist.photo:
            photo = playlist.photo.photo_1200
        elif playlist.thumbs:
            photo = playlist.thumbs[0].photo_1200

        return photo

    async def _get_text(
        self,
        playlist: AudioPlaylist,
    ) -> VttText:
        text_factory = VttPlaylistTextFactory(
            vk_api=self.vk_service.kate_user,
            playlist=playlist,
        )
        return await text_factory.create()

    async def _get_audios(self, playlist: AudioPlaylist) -> list[AudioAudio]:
        return await self.vk_service.get_audios_by_playlist_id(
            owner_id=playlist.owner_id,
            playlist_id=playlist.id,
            access_key=playlist.access_key,
            count=playlist.count,
        )

    async def create(
        self,
        owner_id: int,
        playlist_id: int,
        access_key: str | None = None,
        *,
        with_audios: bool = False,
    ) -> VttAudioPlaylist | None:
        vk_audio_playlist = await self.vk_service.get_audio_playlist(
            owner_id=owner_id,
            playlist_id=playlist_id,
            access_key=access_key,
        )
        if not vk_audio_playlist:
            logger.warning("Playlist not found.")
            return None

        playlist_title = self._get_title(playlist=vk_audio_playlist)
        playlist_photo = self._get_photo(playlist=vk_audio_playlist)
        playlist_text = await self._get_text(playlist=vk_audio_playlist)
        playlist_audios = await self._get_audios(playlist=vk_audio_playlist) if with_audios else None

        return VttAudioPlaylist(
            id=playlist_id,
            owner_id=owner_id,
            access_key=access_key,
            title=playlist_title,
            text=playlist_text,
            description=vk_audio_playlist.description,
            photo=playlist_photo,
            audios=playlist_audios,
        )
