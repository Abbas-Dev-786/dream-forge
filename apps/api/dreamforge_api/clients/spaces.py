from __future__ import annotations

import mimetypes
from urllib.parse import urlparse

import boto3
import httpx

from dreamforge_api.config import Settings


class SpacesClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = bool(
            settings.spaces_access_key_id
            and settings.spaces_secret_access_key
            and settings.spaces_bucket
        )
        self.client = None
        if self.enabled:
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.spaces_endpoint_url,
                aws_access_key_id=settings.spaces_access_key_id,
                aws_secret_access_key=settings.spaces_secret_access_key,
            )

    def normalize_remote_asset(self, provider_url: str, key: str) -> str:
        if not self.enabled or self.client is None:
            return provider_url
        response = httpx.get(provider_url, timeout=60.0)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type")
        if not content_type:
            content_type = mimetypes.guess_type(urlparse(provider_url).path)[0] or "application/octet-stream"
        self.client.put_object(
            Bucket=self.settings.spaces_bucket,
            Key=key,
            Body=response.content,
            ContentType=content_type,
            ACL="public-read",
        )
        if self.settings.spaces_public_base_url:
            return f"{self.settings.spaces_public_base_url}/{key}"
        return provider_url

