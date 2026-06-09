# Changelog

## v2.1.5 (2026-06-09)

### Fix

- **cb_receiver**: add missing types in WallPostType

## v2.1.4 (2026-05-29)

### Perf

- **cb_receiver**: remove vkbottle to reduce memory consumption

## v2.1.3 (2026-05-24)

### Fix

- sync uv.lock ruff specifier with vtt_common across all sub-projects

## v2.1.2 (2026-05-17)

### Fix

- **cb_receiver**: add missing mock and skip integration tests without docker
- **env_validator**: add missing mock side_effect values in tests

## v2.1.1 (2026-05-17)

### Fix

- **vtt_common**: allow tuple proxy type for mtproto connections
- **tgm_bot**: add type annotation for level variable

## v2.1.0 (2026-05-16)

### Feat

- **worker**: enable streaming playback for video sends

### Fix

- **env_helper**: reject non-channel entities in is_channel_valid
- **tgm_bot**: ensure vk_api.http_client is closed on exception
- **env_helper**: use playlist channel defaults in prompt_tgm_playlist_channel
- **worker**: handle None access_key in VttAudioPlaylist.full_id
- **worker**: make AudioPlaylistPhoto.photo_1200 optional
- **vtt_common**: warn and skip mtproto proxy when secret is missing
- **cb_receiver**: await set_callback_settings instead of fire-and-forget
- **env_helper**: save partial config on interrupt with clear warning
- **worker**: handle VttError in forward_playlist
- **env_validator**: fix inverted channel validation and unsafe .result() call
- **tgm_bot**: correct playlist queue and celery kwarg typo
- **worker**: correctly forward VK polls to Telegram
- **worker**: use yt-dlp for video downloads

### Refactor

- **worker**: remove unused audio fallback

## v2.0.0 (2026-05-15)

### BREAKING CHANGE

- basic compose start without ssl now requires 'http' profile
- removed client ssl configs
- remove VK_OFFICIAL_TOKEN environment variable
- migrate VK auth from Kate to Marusia, rename KATE_TOKEN to VK_TOKEN
- Rename VK_IGNORE_ADS to VTT_IGNORE_ADS
- Remove VK_API_LANGUAGE (this setting is deffered from VTT_LANGUAGE)
- Change Telethon SQLite sessions to string sessions

### Feat

- **worker**: use audio title as filename for downloaded audio
- add support for MTProto proxy
- **ssl**: use nginx-proxy and acme-companion for ssl configuration
- add NGINX_SERVER_NAME, NGINX_HTTPS_PORT and SSL_EMAIL envs for ssl setup
- **docker**: run all containers as user
- update telethon to 1.42.0 and cryptg to 0.5.2
- update vkbottle to 4.6.2
- add docker-compose.local.yml
- **tgm_bot**: add tgm_bot
- **cb_receiver**: add cb_receiver
- **env_validator**: add env_validator
- **env_helper**: add env_helper

### Fix

- **worker**: remove nonexistent param, avoid pop(0) mutation, fix split_text HTML offset bug
- **worker**: fix _convert_to_html_link
- **worker**: change eyed3 to mutagen for mp3 tagging, fix missing files edge case
- **tgm_bot**: fix not working vk.ru links

### Refactor

- replace inline env vars with shared env_file anchor
- move common pytest packages into vtt_common
- **ssl**: remove client ssl setup
- **ssl**: simplify SSL setup, refactor tunnel code, update README
- **env_validator**: refactor validation of env vars
- **env_helper**: refactor with async/await
- **cb_receiver**: change localtunnel to tunnelmole
- **docker**: change use of env vars, add healthchecks

## v1.2.1 (2023-08-10)

### Fix

- **docker**: Fix docker image build error caused by old poetry

## v1.2.0 (2023-08-06)

### Feat

- **cb-receiver**: add option to skip ad posts (true by default)

## v1.1.3 (2023-01-14)

## v1.1.2 (2022-07-15)

## v1.1.1 (2022-07-03)

## v1.1.0 (2022-06-13)

## v1.0.2 (2022-05-07)

## v1.0.1 (2022-04-30)

## v1.0.0 (2022-04-27)
