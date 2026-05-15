from __future__ import annotations

import asyncio
import re
import tempfile
from email.message import EmailMessage
from mimetypes import guess_extension
from pathlib import Path
from secrets import randbelow
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import urlparse

import aiofiles
import ffmpeg
from aiofiles.tempfile import NamedTemporaryFile
from aiohttp import ClientSession, ClientTimeout
from loguru import logger
from mutagen.easyid3 import EasyID3

from app.exceptions import VttError

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from types import TracebackType

    from vkbottle_types.objects import AudioAudio

    from app.services.vk import VkService
    from app.vtt.schemas import VttVideo


class Downloader:
    def __init__(self, vk_service: VkService) -> None:
        self.vk_service = vk_service
        self.session = ClientSession(timeout=ClientTimeout(total=3600))
        self.file_paths: list[Path] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.session.close()

        for path in self.file_paths:
            path.unlink(missing_ok=True)

    async def download_media(self, url: str) -> Path:
        logger.info(f"Downloading document from URL: {url}")

        await asyncio.sleep(randbelow(3))
        async with self.session.get(url) as response:
            filepath = Path(tempfile.gettempdir(), Path(response.url.path).name)
            async with aiofiles.open(filepath, "w+b") as file:
                async for chunk, _ in response.content.iter_chunks():
                    await file.write(chunk)
        return filepath

    async def download_video(self, url: str, title: str) -> Path | None:
        logger.info(f'Downloading video "{title}" from URL: {url}')

        filepath = None

        await asyncio.sleep(randbelow(3))
        async with self.session.get(url) as response:
            if not title:
                content_disposition = response.headers.get("Content-Disposition")
                if not content_disposition:
                    logger.warning("Header 'Content-Disposition' not found.")
                    return None

                msg = EmailMessage()
                msg["Content-Disposition"] = content_disposition
                filename = msg.get_filename()
                if not filename:
                    logger.warning("Filename not found in Content-Disposition header.")
                    return None
            else:
                content_type = response.headers.get("content-type")
                if not content_type:
                    logger.warning("Header 'content-type' not found.")
                    return None

                extension = guess_extension(content_type)
                if not extension:
                    logger.warning(f"Unknown video extension for content-type '{content_type}'.")
                    return None

                name = title.strip().replace(" ", "_")
                name = re.sub(r"(?u)[^-\w.]", "", name)
                filename = name + extension

            filepath = Path(tempfile.gettempdir(), filename)
            async with aiofiles.open(filepath, "w+b") as file:
                async for chunk, _ in response.content.iter_chunks():
                    await file.write(chunk)

        return filepath

    async def download_audio(
        self,
        audio: AudioAudio,
        *,
        try_fallback: bool = True,
    ) -> Path | None:
        url = audio.url
        audio_full_id = f"{audio.owner_id}_{audio.id}_{audio.access_key}"
        audio_full_title = f"{audio.artist} - {audio.title}"

        if not url:
            logger.warning(f"No URL for audio [{audio_full_id}]")
            return None

        logger.info(f"Downloading audio [{audio_full_id}] from URL: {url}")

        filepath = None

        await asyncio.sleep(randbelow(3))
        async with NamedTemporaryFile(suffix=".mp3", delete=False) as temp:
            if not urlparse(url).path.endswith("m3u8"):
                logger.info("Downloading audio by http...")
                async with self.session.get(url) as response:
                    async for chunk, _ in response.content.iter_chunks():
                        await temp.write(chunk)
            else:
                logger.info("Downloading audio by ffmpeg...")
                stream = ffmpeg.input(url, http_persistent=False)
                stream = ffmpeg.output(stream, "-", c="copy", f="mp3")
                out, _ = ffmpeg.run(stream, capture_stdout=True, quiet=True)
                await temp.write(out)

            filepath = Path(str(temp.name))

        # Setting audio metadata
        audiofile = EasyID3(filepath)  # type: ignore[no-untyped-call]
        if audiofile is not None:
            audiofile["artist"] = audio.artist
            audiofile["title"] = audio.title
            audiofile.save()
        elif try_fallback:
            logger.warning(f"Broken audio [{audio_full_id}] [{audio_full_title}], trying with another token...")
            fallback_audio = next(
                iter(await self.vk_service.get_audio_by_ids(audio_ids=[audio_full_id])),
                None,
            )
            if not fallback_audio:
                logger.warning("Unable to get audio by fallback token.")
                return None
            filepath = await self.download_audio(fallback_audio, try_fallback=False)
        else:
            logger.warning("Unable to download audio.")
            return None

        if filepath:
            logger.info(f"Audio succesfully downloaded: [{audio_full_id}] [{audio_full_title}]")
        return filepath

    async def download_files(
        self,
        urls: list[str] | None = None,
        audios: list[AudioAudio] | None = None,
        videos: list[VttVideo] | None = None,
    ) -> list[Path]:
        coros: list[Coroutine[Any, Any, Path | None]] = []

        if urls:
            coros.extend(self.download_media(url) for url in urls)
        if audios:
            coros.extend(self.download_audio(audio) for audio in audios)
        if videos:
            coros.extend(self.download_video(video.url, video.title) for video in videos)

        file_paths = [path for path in await asyncio.gather(*coros) if path is not None]
        if not file_paths:
            raise VttError("Failed to download files.")

        self.file_paths.extend(file_paths)

        return file_paths
