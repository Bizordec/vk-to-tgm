## v2.0.0 (2026-05-15)

### BREAKING CHANGE

- basic compose start without ssl now requires 'http' profile
- removed client ssl configs
- remove VK_OFFICIAL_TOKEN environment variable
- - Rename KATE_TOKEN to VK_KATE_TOKEN
- Rename VK_IGNORE_ADS to VTT_IGNORE_ADS
- Remove VK_API_LANGUAGE (this setting is deffered from VTT_LANGUAGE)
- Change Telethon SQLite sessions to string sessions

### Feat

- **worker**: use audio title as filename for downloaded audio
- **tgm_bot**: add Loguru structured logging across handlers
- migrate VK auth from Kate to Marusia, rename VK_KATE_TOKEN to VK_TOKEN, fix mypy errors
- **tgm_bot**: add more logging
- **env_validator**: add more logging for tgm settings validation
- add support for MTProto proxy
- add proxy environment variables for tgm
- **ssl**: use nginx-proxy and acme-companion for ssl configuration
- update telethon to 1.42.0 and crypth to 0.5.2
- update vkbottle to 4.6.2
- **worker**: return support for *vk.com links in attachments
- **ssl**: add ACME_HTTP_PORT env
- update vkbottle to 4.6.0
- **env_helper**: change validation for TGM_CLIENT_PHONE
- **env_validator**: require non-empty strings, add validator for TGM_CLIENT_PHONE
- **env_validator**: add NGINX_SERVER_NAME, NGINX_HTTPS_PORT and SSL_EMAIL
- **env_helper**: add NGINX_SERVER_NAME, NGINX_HTTPS_PORT and SSL_EMAIL envs for ssl setup
- update vkbottle and vkbottle-types
- **docker**: add NGINX_HTTP_PORT and NGINX_HTTPS_PORT env vars
- update vkbottle to 4.5.2
- **docker**: run all containers as user
- **env_helper**: add --env-file argument, run container as user
- **tgm_bot**: add tgm_bot
- **tgm_bot**: add initial tgm_bot project
- **worker**: add forward_playlist task
- **vscode**: add setting "files.insertFinalNewline": true
- **env_helper**: add dockerfile
- add docker-compose.local.yml
- **env_validator**: add dockerfile
- **cb_receiver**: add dockerfile
- **cb_receiver**: add cb_receiver
- **env_validator**: add env_validator
- **env_helper**: add env_helper

### Fix

- add commitizen config with version 1.2.1
- **env_helper**: change env_helper version
- fix venv target prerequisites and simplify uv sync
- explicitly pass AiohttpClient to VK API constructor
- properly close event loop in async_to_sync
- **worker**: remove nonexistent param, avoid pop(0) mutation, fix split_text HTML offset bug
- **worker**: add missing mtproto type in TGM_PROXY_TYPE
- remove mtproto proxy from tgm user client, add validators for TGM_PROXY_TYPE and TGM_PROXY_PORT
- change defaults for TGM_PROXY_RDNS and TGM_PROXY_MTPROTO_CONNECTION in docker-compose.yml
- fix docker build for env_validator
- remove docker warnings for empty proxy vars
- add missing python-socks[asyncio] packages
- **tgm_bot**: fix not working vk.ru links
- **worker**: fix _convert_to_html_link
- **ssl**: add missing VIRTUAL_PORT
- **docker**: fix volumes_from
- **docs**: fix compose commands
- **ssl**: add missing volumes
- remove cryptg from env_helper and env_validator
- **cb_receiver**: fix minor typing issue
- **worker**: fix usage of BasePropertyExists
- **env_validator**: change type of TGM_CLIENT_PHONE to str
- **worker**: pin vkbottle to v4.4.6 to temporarily fix bug with broken wall.getById method with extended=True
- **docker**: remove unused env_helper in compose file
- **ssl**: add missing busybox-suid apk package
- **docker**: remove VK_OFFICIAL_TOKEN env in docker compose file
- **worker**: change eyed3 to mutagen for mp3 tagging, fix possible case when no specified files was downloaded
- **worker**: add missing ffmpeg in dockerfile
- minor fixes in scripts and docs
- **cb_receiver**: disable vkbottle logs
- **cb_receiver**: fix vtt_common lib installation in docker
- **env_helper**: fix error handling
- **env_validator**: fix error handling

### Refactor

- migrate from uv workspace to path dependencies with per-project Docker context
- replace inline env vars with shared env_file anchor
- move common pytest packages into vtt_common
- migrate to UV workspace and consolidate shared dependencies
- **ssl**: remove client ssl setup
- **tgm_bot**: fix typing issues, remove VK_OFFICIAL_TOKEN
- **worker**: remove VK_OFFICIAL_TOKEN
- **env_validator**: refactor validation of env vars
- **env_helper**: refactor with async/await
- **env_helper**: update packages, refactor with pydantic v2, add test
- **env**: update .env.example, minor fixes in docs
- **ssl**: simplify SSL setup, refactor tunnel code, update README
- remove old files
- add methods for setting and getting tasks status
- **worker**: rename worker_wall to worker
- **worker_wall**: move worker that sends wall posts into separate service
- update makefiles
- **cb_receiver**: change localtunnel to tunnelmole
- update pre-commit
- **env_helper**: update packages and ruff rules, refactor main.py
- **env_validator**: change python dependancy to 3.11
- **docker**: change use of env vars, add healthchecks
- **cb_receiver**: change python dependency to 3.11
- **env_helper**: run main synchronously, add uvloop
- move pre-commit-config.yaml to the root
- **vtt_common**: move celery config to vtt_common

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
