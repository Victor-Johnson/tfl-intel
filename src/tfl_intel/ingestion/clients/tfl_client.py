"""Client for the TfL Line API endpoints used by V1 ingestion."""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from tfl_intel.common.logging import get_logger
from tfl_intel.config import Settings


def _is_retryable(exc: BaseException) -> bool:
    """Retry timeouts and server errors; client errors are permanent."""

    if isinstance(exc, httpx.TimeoutException):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code >= 500
    )


class TfLLineClient:
    """Thin HTTP client that fetches JSON from the TfL Line API."""

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_seconds: float = 20.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = settings.tfl_api_base_url.rstrip("/")
        self._app_key = settings.tfl_app_key
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._logger = get_logger(__name__, source="tfl_line_api")

    def close(self) -> None:
        """Close the underlying HTTP client when this instance owns it."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "TfLLineClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def get_severity_codes(self) -> list[dict[str, Any]]:
        """Fetch TfL line status severity code metadata."""

        return self._get_json_list("/Meta/Severity")

    def get_lines_by_mode(self, mode: str = "tube") -> list[dict[str, Any]]:
        """Fetch lines for a TfL mode."""

        return self._get_json_list(f"/Mode/{mode}")

    def get_line_status_by_mode(
        self,
        mode: str = "tube",
        detail: bool = False,
        severity_level: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch current line status records for a TfL mode."""

        params: dict[str, str] = {}
        if detail:
            params["detail"] = "true"
        if severity_level is not None:
            params["severityLevel"] = severity_level
        return self._get_json_list(f"/Mode/{mode}/Status", params=params)

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    def _send(self, url: str, params: dict[str, str]) -> httpx.Response:
        """Issue one GET, retrying timeouts and 5xx with exponential backoff."""

        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response

    def _get_json_list(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        request_params = dict(params or {})
        if self._app_key:
            request_params["app_key"] = self._app_key

        url = f"{self._base_url}{path}"
        try:
            response = self._send(url, request_params)
        except httpx.TimeoutException as exc:
            msg = f"TfL Line API request timed out for {path}"
            raise RuntimeError(msg) from exc
        except httpx.HTTPStatusError as exc:
            msg = (
                f"TfL Line API request failed for {path} "
                f"with HTTP {exc.response.status_code}"
            )
            raise RuntimeError(msg) from exc

        self._logger.info(
            "tfl_line_api_response",
            endpoint=path,
            status_code=response.status_code,
            using_app_key=bool(self._app_key),
        )

        payload = response.json()
        if not isinstance(payload, list):
            msg = f"TfL Line API response for {path} was not a list"
            raise ValueError(msg)
        return payload


TfLClient = TfLLineClient
