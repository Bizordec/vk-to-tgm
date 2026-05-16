from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from secrets import randbelow
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import urlparse

import aiofiles
import ffmpeg
from aiohttp import ClientSession, ClientTimeout
from loguru import logger
from mutagen._util import MutagenError
from mutagen.easyid3 import EasyID3
from pathvalidate import sanitize_filename
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from app.exceptions import VttError

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from types import TracebackType

    from vkbottle_types.objects import AudioAudio

    from app.vtt.schemas import VttVideo


class Downloader:
    def __init__(self) -> None:
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

    async def download_video(self, video: VttVideo) -> Path | None:
        logger.info(f'Downloading video "{video.title}" from URL: {video.url}')

        name = sanitize_filename(video.title)
        outtmpl = str(Path(tempfile.gettempdir(), f"{name}.%(ext)s"))

        def download_by_ytdlp() -> str:
            with YoutubeDL(
                {
                    "quiet": True,
                    "no_warnings": True,
                    "noprogress": True,
                    "format": "best",
                    "outtmpl": outtmpl,
                },
            ) as ydl:
                info = ydl.extract_info(video.url, download=True)
                return info.get("ext") or "mp4"

        try:
            ext = await asyncio.to_thread(download_by_ytdlp)
        except DownloadError as error:
            logger.warning("yt-dlp failed for {}: {}", video.title, error)
            return None

        filepath = Path(outtmpl.rpartition("%(ext)s")[0] + ext)
        self.file_paths.append(filepath)
        return filepath

    async def download_audio(
        self,
        audio: AudioAudio,
    ) -> Path | None:
        url = audio.url
        audio_full_id = f"{audio.owner_id}_{audio.id}_{audio.access_key}"
        audio_full_title = f"{audio.artist} - {audio.title}"

        if not url:
            logger.warning(f"No URL for audio [{audio_full_id}]")
            return None

        logger.info(f"Downloading audio [{audio_full_id}] from URL: {url}")

        await asyncio.sleep(randbelow(3))

        safe_name = sanitize_filename(f"{audio_full_title}.mp3")
        filepath = Path(tempfile.gettempdir(), safe_name)
        counter = 1
        while await asyncio.to_thread(filepath.exists):
            filepath = Path(tempfile.gettempdir(), f"{safe_name.removesuffix('.mp3')}_{counter}.mp3")
            counter += 1

        async with aiofiles.open(filepath, "w+b") as temp:
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

        # Setting audio metadata
        try:
            audiofile = EasyID3(filepath)  # type: ignore[no-untyped-call]
            audiofile["artist"] = audio.artist
            audiofile["title"] = audio.title
            audiofile.save()
        except MutagenError:
            logger.warning(f"Broken audio [{audio_full_id}] [{audio_full_title}]")
            return None

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
            coros.extend(self.download_video(video) for video in videos)

        file_paths = [path for path in await asyncio.gather(*coros) if path is not None]
        if not file_paths:
            raise VttError("Failed to download files.")

        self.file_paths.extend(file_paths)

        return file_paths
