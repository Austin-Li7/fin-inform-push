from __future__ import annotations

from dataclasses import dataclass
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ObsidianConfig:
    base_url: str
    api_key: str
    folder: str


class ObsidianPublishError(RuntimeError):
    pass


def _build_ssl_context(base_url: str) -> ssl.SSLContext | None:
    parsed = urlparse(base_url)
    if parsed.scheme == "https" and parsed.hostname in {"127.0.0.1", "localhost"}:
        return ssl._create_unverified_context()
    return None


def build_obsidian_note_path(date_label: str, note_slug: str, folder: str) -> str:
    normalized_folder = folder.strip().strip("/")
    return f"{normalized_folder}/{date_label}/{note_slug}.md"


def publish_markdown_to_obsidian(
    date_label: str,
    note_slug: str,
    markdown: str,
    config: ObsidianConfig,
    urlopen_fn=urlopen,
) -> str:
    base_url = config.base_url.strip().rstrip("/")
    api_key = config.api_key.strip()
    note_path = build_obsidian_note_path(date_label, note_slug, config.folder)
    encoded_path = quote(note_path, safe="/")
    ssl_context = _build_ssl_context(base_url)
    request = Request(
        url=f"{base_url}/vault/{encoded_path}",
        data=markdown.encode("utf-8"),
        method="PUT",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "text/markdown; charset=utf-8",
        },
    )
    try:
        with urlopen_fn(request, context=ssl_context):
            return note_path
    except HTTPError as exc:
        raise ObsidianPublishError(
            f"Obsidian push failed with HTTP {exc.code} for {note_path}."
        ) from exc
    except URLError as exc:
        raise ObsidianPublishError(
            f"Obsidian push failed for {note_path}: {exc.reason}."
        ) from exc
