from dataclasses import dataclass


@dataclass
class AuthParams:
    auth_code: bool | str = True
    captcha_sid: str = ""
    captcha_key: str = ""
    need_creds: bool = True
    token: str = ""
