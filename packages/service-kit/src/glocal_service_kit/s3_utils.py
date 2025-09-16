from __future__ import annotations

from urllib.parse import urlparse


def parse_s3_url(url: str) -> tuple[str, str]:
    if url.startswith("s3://"):
        without_scheme = url[5:]
    else:
        parsed = urlparse(url)
        without_scheme = parsed.netloc + parsed.path
    bucket, _, key = without_scheme.partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URL: {url}")
    return bucket, key.lstrip("/")
