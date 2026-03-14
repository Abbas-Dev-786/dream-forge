from __future__ import annotations

import json
import math
import struct
import wave
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamforge_api.clients.inference import GradientAsyncInferenceClient
from dreamforge_api.clients.spaces import SpacesClient
from dreamforge_api.config import Settings
from dreamforge_api.models import MediaAssetRecord, MediaJobRecord, StoryNodeRecord


class MediaJobService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.inference = GradientAsyncInferenceClient(settings)
        self.spaces = SpacesClient(settings)

    def process_next_job(self) -> bool:
        job = self.db.scalar(
            select(MediaJobRecord)
            .where(MediaJobRecord.status == "queued")
            .order_by(MediaJobRecord.created_at.asc())
            .limit(1)
        )
        if not job:
            return False

        job.status = "processing"
        self.db.commit()

        try:
            if self.settings.use_mock_ai or not self.settings.gradient_model_access_key:
                media_url = self._mock_asset_url(job)
                self._mark_ready(job, media_url, None)
                return True
            self._process_remote_job(job)
            return True
        except Exception as exc:  # noqa: BLE001
            self._retry_or_fail(job, str(exc))
            return True

    def _process_remote_job(self, job: MediaJobRecord) -> None:
        payload = json.loads(job.payload_json)
        if not job.external_request_id:
            model_id = self.settings.image_model_id if job.job_type == "IMAGE_RENDER" else self.settings.audio_model_id
            submission = self.inference.submit_async(model_id, payload)
            job.external_request_id = str(submission["request_id"])
            job.status = "queued"
            self.db.commit()
            return

        status_result = self.inference.get_status(job.external_request_id)
        status_value = str(status_result.get("status", "")).upper()
        if status_value in {"QUEUED", "IN_PROGRESS", "PROCESSING"}:
            job.status = "queued"
            self.db.commit()
            return
        if status_value in {"FAILED", "ERROR"}:
            raise RuntimeError(str(status_result.get("error") or "Remote inference job failed."))

        result = self.inference.get_result(job.external_request_id)
        provider_url = self._extract_provider_url(job.job_type, result)
        normalized_url = self.spaces.normalize_remote_asset(provider_url, self._spaces_key(job, provider_url))
        self._mark_ready(job, normalized_url, provider_url)

    def _extract_provider_url(self, job_type: str, result: dict[str, object]) -> str:
        output = result.get("output") or {}
        if job_type == "IMAGE_RENDER":
            images = output.get("images") or []
            if images:
                return str(images[0]["url"])
        if job_type == "AUDIO_RENDER":
            audio = output.get("audio")
            if isinstance(audio, dict) and audio.get("url"):
                return str(audio["url"])
            if output.get("url"):
                return str(output["url"])
        raise RuntimeError("Inference result did not include a media URL.")

    def _mark_ready(self, job: MediaJobRecord, media_url: str, provider_url: str | None) -> None:
        node = self.db.get(StoryNodeRecord, job.node_id)
        asset_type = "image" if job.job_type == "IMAGE_RENDER" else "audio"
        if asset_type == "image":
            node.image_status = "ready"
            node.image_url = media_url
        else:
            node.audio_status = "ready"
            node.audio_url = media_url
        self.db.add(
            MediaAssetRecord(
                id=f"asset_{job.id}",
                session_id=job.session_id,
                node_id=job.node_id,
                asset_type=asset_type,
                url=media_url,
                provider_url=provider_url,
            )
        )
        job.status = "completed"
        job.error_message = None
        self.db.commit()

    def _retry_or_fail(self, job: MediaJobRecord, message: str) -> None:
        job.attempt_count += 1
        job.error_message = message
        if job.attempt_count >= job.max_attempts:
            job.status = "failed"
            node = self.db.get(StoryNodeRecord, job.node_id)
            if job.job_type == "IMAGE_RENDER":
                node.image_status = "failed"
            else:
                node.audio_status = "failed"
        else:
            job.status = "queued"
        self.db.commit()

    def _mock_asset_url(self, job: MediaJobRecord) -> str:
        asset_kind = "images" if job.job_type == "IMAGE_RENDER" else "audio"
        ext = "svg" if job.job_type == "IMAGE_RENDER" else "wav"
        return f"{self.settings.app_public_base_url}/api/v1/mock-assets/{asset_kind}/{job.id}.{ext}"

    def _spaces_key(self, job: MediaJobRecord, provider_url: str) -> str:
        ext = provider_url.rsplit(".", 1)[-1] if "." in provider_url else ("jpg" if job.job_type == "IMAGE_RENDER" else "mp3")
        kind = "images" if job.job_type == "IMAGE_RENDER" else "audio"
        return f"dreamforge/{kind}/{job.node_id}.{ext}"


def generate_mock_svg(label: str) -> str:
    escaped = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">
  <defs>
    <linearGradient id="sky" x1="0%" x2="100%" y1="0%" y2="100%">
      <stop offset="0%" stop-color="#0f2042"/>
      <stop offset="45%" stop-color="#33558b"/>
      <stop offset="100%" stop-color="#f2a65a"/>
    </linearGradient>
  </defs>
  <rect width="1600" height="1000" fill="url(#sky)"/>
  <circle cx="1200" cy="220" r="110" fill="#fff2c7" opacity="0.9"/>
  <path d="M0 790 C240 690 350 870 550 760 S950 650 1220 790 S1470 830 1600 720 L1600 1000 L0 1000 Z" fill="#fbe0a6"/>
  <path d="M0 870 C260 760 430 940 690 830 S1030 760 1280 860 S1470 930 1600 810 L1600 1000 L0 1000 Z" fill="#f9c06b"/>
  <text x="120" y="170" fill="#fff7e6" font-size="70" font-family="Georgia, serif">DreamForge Illustration</text>
  <text x="120" y="280" fill="#fff7e6" font-size="42" font-family="Verdana, sans-serif">{escaped}</text>
</svg>"""


def generate_mock_wav_bytes() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        frames = []
        duration_seconds = 1.0
        total_frames = int(22050 * duration_seconds)
        for i in range(total_frames):
            value = int(1400 * math.sin(2 * math.pi * 440 * i / 22050))
            frames.append(struct.pack("<h", value))
        wav_file.writeframes(b"".join(frames))
    return buffer.getvalue()

