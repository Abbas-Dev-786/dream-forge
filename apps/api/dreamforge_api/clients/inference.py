from __future__ import annotations

import httpx

from dreamforge_api.config import Settings


class GradientAsyncInferenceClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def submit_async(self, model_id: str, payload: dict[str, object]) -> dict[str, object]:
        response = httpx.post(
            f"{self.settings.inference_base_url}/v1/async-invoke",
            headers={
                "Authorization": f"Bearer {self.settings.gradient_model_access_key}",
                "Content-Type": "application/json",
            },
            json={"model_id": model_id, "input": payload},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

    def get_status(self, request_id: str) -> dict[str, object]:
        response = httpx.get(
            f"{self.settings.inference_base_url}/v1/async-invoke/{request_id}/status",
            headers={"Authorization": f"Bearer {self.settings.gradient_model_access_key}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def get_result(self, request_id: str) -> dict[str, object]:
        response = httpx.get(
            f"{self.settings.inference_base_url}/v1/async-invoke/{request_id}",
            headers={"Authorization": f"Bearer {self.settings.gradient_model_access_key}"},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()

