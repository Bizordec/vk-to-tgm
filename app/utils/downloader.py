import asyncio
import cgi
import logging
import os
import re
import tempfile
from mimetypes import guess_extension
from secrets import randbelow
from typing import List, Optional
from urllib.parse import urlparse

import aiofiles
import eyed3
import ffmpeg
from aiofiles.tempfile import NamedTemporaryFile
from aiohttp import ClientSession
from vkbottle.api.api import API
from vkbottle_types.objects import AudioAudio

from app.schemas.vk import VttVideo

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self) -> None:
        self.session = ClientSession()
        self.file_paths: List[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def close(self):
        await self.session.close()
        for path in self.file_paths:
            os.remove(path)

    async def download_media(self, url: str) -> str:
        logger.info(f"Downloading document from URL: {url}")
        filepath = ""
        await asyncio.sleep(randbelow(3))
        async with self.session.get(url, timeout=3600) as response:
            temp_path = os.path.join(tempfile.gettempdir(), os.path.basename(response.url.path))
            async with aiofiles.open(temp_path, "w+b") as file:
                async for chunk, _ in response.content.iter_chunks():
                    await file.write(chunk)
            filepath = temp_path
        return filepath

    async def download_video(self, url: str, title: str) -> str:
        logger.info(f'Downloading video "{title}" from URL: {url}')
        filepath = ""
        await asyncio.sleep(randbelow(3))
        async with self.session.get(url, timeout=3600) as response:
            if not title:
                header = response.headers.get("Content-Disposition")
                _, opts = cgi.parse_header(header)
                filename = opts["filename"]
            else:
                name = title.strip().replace(" ", "_")
                name = re.sub(r"(?u)[^-\w.]", "", name)
                extension = guess_extension(response.headers.get("content-type"))
                filename = name + extension
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            async with aiofiles.open(temp_path, "w+b") as file:
                async for chunk, _ in response.content.iter_chunks():
                    await file.write(chunk)
            filepath = temp_path
        return filepath

    async def download_audio(
        self,
        audio: AudioAudio,
        fallback_vk_api: Optional[API] = None,
        try_fallback: bool = True,
    ) -> str:
        url = audio.url
        audio_full_id = f"{audio.owner_id}_{audio.id}_{audio.access_key}"
        audio_full_title = f"{audio.artist} - {audio.title}"
        logger.info(f"Downloading audio [{audio_full_id}] from URL: {url}")
        filepath = ""
        await asyncio.sleep(randbelow(3))
        async with NamedTemporaryFile(suffix=".mp3", delete=False) as temp:
            if not urlparse(url).path.endswith("m3u8"):
                logger.info("Downloading audio by http...")
                async with self.session.get(url, timeout=3600) as response:
                    async for chunk, _ in response.content.iter_chunks():
                        await temp.write(chunk)
            else:
                logger.info("Downloading audio by ffmpeg...")
                stream = ffmpeg.input(url, http_persistent=False)
                stream = ffmpeg.output(stream, "-", c="copy", f="mp3")
                out, _ = ffmpeg.run(stream, capture_stdout=True, quiet=True)
                await temp.write(out)
            filepath = temp.name

        # Setting audio metadata
        audiofile = eyed3.load(filepath)
        if audiofile:
            audiofile.tag.artist = audio.artist
            audiofile.tag.title = audio.title
            audiofile.tag.save()
        elif fallback_vk_api and try_fallback:
            logger.warning(f"Broken audio [{audio_full_id}] [{audio_full_title}], trying with another token...")
            audios: List[dict] = (
                await fallback_vk_api.request(
                    "audio.getById",
                    {
                        "audios": audio_full_id,
                    },
                )
            )["response"]
            fb_audio = next(iter(audios), None)
            if fb_audio and fb_audio.get("url"):
                audio = AudioAudio(**fb_audio)
                filepath = await self.download_audio(audio, fallback_vk_api, try_fallback=False)

        logger.info(f"Audio succesfully downloaded: [{audio_full_id}] [{audio_full_title}]")
        return filepath

    async def download_medias(self, media_urls: List[str]):
        media_paths = await asyncio.gather(*[self.download_media(url) for url in media_urls])
        self.file_paths += media_paths
        return media_paths

    async def download_videos(self, videos: List[VttVideo]):
        video_paths = await asyncio.gather(*[self.download_video(video.url, video.title) for video in videos])
        self.file_paths += video_paths
        return video_paths

    async def download_audios(self, audios: List[AudioAudio], fallback_vk_api: Optional[API] = None):
        audio_paths = await asyncio.gather(*[self.download_audio(audio, fallback_vk_api) for audio in audios])
        self.file_paths += audio_paths
        return audio_paths
