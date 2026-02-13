"""Async HTTP client for GitHub API with retry/backoff."""

import asyncio
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import MCCError

logger = logging.getLogger(__name__)


class GitHubClient:
    """Wraps httpx.AsyncClient for GitHub API calls.

    Auth override point: swap ``_get_auth_headers`` for GitHub App tokens.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.GITHUB_API_BASE_URL,
            headers={
                **self._get_auth_headers(),
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    @staticmethod
    def _get_auth_headers() -> dict[str, str]:
        """Return auth headers. Override point for GitHub App auth."""
        if not settings.GITHUB_TOKEN:
            return {}
        return {"Authorization": f"Bearer {settings.GITHUB_TOKEN}"}

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        max_retries: int = 3,
    ) -> dict | list:
        """Execute a GitHub API request with retry on rate-limit (403/429)."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                resp = await self._client.request(method, path, params=params, json=json_body)

                if resp.status_code in (403, 429):
                    retry_after = float(resp.headers.get("Retry-After", 2**attempt))
                    logger.warning(
                        "GitHub rate limited (%s), retrying after %.1fs",
                        resp.status_code,
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 404:
                    raise MCCError(
                        code="GITHUB_NOT_FOUND",
                        message=f"GitHub resource not found: {path}",
                        status_code=404,
                    )

                resp.raise_for_status()
                if resp.status_code == 204:
                    return {}
                return resp.json()

            except MCCError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "GitHub HTTP %s on attempt %d/%d: %s",
                    exc.response.status_code,
                    attempt + 1,
                    max_retries,
                    path,
                )
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "GitHub request error on attempt %d/%d: %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)

        raise MCCError(
            code="GITHUB_API_ERROR",
            message=f"GitHub API request failed after {max_retries} attempts",
            status_code=502,
        ) from last_error

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------
    async def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        labels: str | None = None,
        per_page: int = 100,
    ) -> list[dict]:
        params: dict = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = labels
        result = await self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)
        return result if isinstance(result, list) else []

    async def get_issue(self, owner: str, repo: str, number: int) -> dict:
        result = await self._request("GET", f"/repos/{owner}/{repo}/issues/{number}")
        return result if isinstance(result, dict) else {}

    async def add_issue_comment(self, owner: str, repo: str, number: int, body: str) -> dict:
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            json_body={"body": body},
        )
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Pull Requests
    # ------------------------------------------------------------------
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        per_page: int = 100,
    ) -> list[dict]:
        params: dict = {"state": state, "per_page": per_page}
        result = await self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
        return result if isinstance(result, list) else []

    async def get_pull_request(self, owner: str, repo: str, number: int) -> dict:
        result = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")
        return result if isinstance(result, dict) else {}

    async def create_review(
        self,
        owner: str,
        repo: str,
        number: int,
        *,
        event: str,
        body: str = "",
    ) -> dict:
        """Submit a PR review. event: APPROVE | REQUEST_CHANGES | COMMENT."""
        json_body: dict = {"event": event}
        if body:
            json_body["body"] = body
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json_body=json_body,
        )
        return result if isinstance(result, dict) else {}

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        number: int,
        *,
        merge_method: str = "squash",
    ) -> dict:
        result = await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/pulls/{number}/merge",
            json_body={"merge_method": merge_method},
        )
        return result if isinstance(result, dict) else {}
