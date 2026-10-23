"""Strips secret values from anything the scan returns."""
import re

R = "[redacted]"
# Values under these keys are never shown; for env-like maps the names stay, the values go.
SECRET_KEYS = {"env", "headers", "apikey", "api_key", "token", "password", "secret", "authorization",
               "oauthaccount", "primaryapikey", "customapikey"}
PATTERNS = re.compile("|".join([
    r"sk-ant-[A-Za-z0-9_\-]{8,}",
    r"sk-[A-Za-z0-9]{20,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"xox[abprs]-[A-Za-z0-9\-]{10,}",
    r"AKIA[0-9A-Z]{16}",
    r"AIza[0-9A-Za-z_\-]{30,}",
    r"[Bb]earer\s+[A-Za-z0-9._\-]{8,}",
    r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}",
]))


def scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if str(k).lower() in SECRET_KEYS:
                out[k] = {n: R for n in v} if isinstance(v, dict) else R
            else:
                out[k] = scrub(v)
        return out
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    if isinstance(obj, str):
        return PATTERNS.sub(R, obj)
    return obj
