from dataclasses import dataclass


@dataclass
class AuthParams:
    auth_code: str = "GET_CODE"
    captcha_sid: str = ""
    captcha_key: str = ""
    need_creds: bool = True
    token: str = ""
