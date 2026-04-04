from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import pytest
import requests

from engine.upstream import (
    FIJI_WINDOWS_ARCHIVE_URL,
    _download_file,
    download_and_stage_figshare_assets,
    extract_fiji_archive,
    stage_assets_from_source,
)


def build_zip(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_stage_assets_from_source_copies_macros_and_trial_inputs(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    (source_root / "data" / "Trial" / "Trial" / "01_input").mkdir(parents=True)
    (source_root / "golden" / "full_image").mkdir(parents=True)
    (source_root / "data" / "Fameles_v2_Full_image.ijm").write_text("full", encoding="utf-8")
    (source_root / "data" / "Fameles_v2_Thumbnails.ijm").write_text("thumb", encoding="utf-8")
    (source_root / "data" / "Trial" / "Trial" / "01_input" / "sample.png").write_text(
        "leaf",
        encoding="utf-8",
    )
    (source_root / "golden" / "full_image" / "results_full.csv").write_text(
        "Label,Area\nleaf,1\n",
        encoding="utf-8",
    )

    destination_root = tmp_path / "staged"
    stage_assets_from_source(source_root, destination_root)

    assert (
        destination_root / "macros" / "original" / "Fameles_v2_Full_image.ijm"
    ).read_text(encoding="utf-8") == "full"
    assert (
        destination_root / "macros" / "original" / "Fameles_v2_Thumbnails.ijm"
    ).read_text(encoding="utf-8") == "thumb"
    assert (destination_root / "fixtures" / "trial_input" / "sample.png").exists()
    assert (destination_root / "golden" / "full_image" / "results_full.csv").exists()


class FakeResponse:
    def __init__(self, *, json_data=None, content: bytes = b"") -> None:
        self._json_data = json_data
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._json_data

    def iter_content(self, chunk_size: int = 65536):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


class FakeSession:
    def __init__(self, routes: dict[str, FakeResponse]) -> None:
        self.routes = routes

    def get(self, url: str, *, timeout: int = 60, stream: bool = False):
        try:
            return self.routes[url]
        except KeyError as exc:
            raise AssertionError(f"Unexpected URL: {url}") from exc


class FailingThenSuccessfulResponse:
    def __init__(self, *, content: bytes, fail_once: bool = False) -> None:
        self.content = content
        self.fail_once = fail_once
        self._attempts = 0

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 65536):
        self._attempts += 1
        if self.fail_once and self._attempts == 1:
            raise requests.exceptions.ChunkedEncodingError("transient read failure")
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]


class SequenceSession:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get(self, url: str, *, timeout: int = 60, stream: bool = False):
        self.calls += 1
        if not self.responses:
            raise AssertionError(f"Unexpected extra request for {url}")
        return self.responses.pop(0)


def test_download_and_stage_figshare_assets_fetches_macros_and_trial_zip(tmp_path: Path) -> None:
    trial_zip = build_zip(
        {
            "Trial/01_input/example.tif": b"trial-image",
        }
    )
    files_payload = [
        {
            "name": "Trial.zip",
            "download_url": "https://download.example/trial",
        },
        {
            "name": "Fameles_v2_Full_image.ijm",
            "download_url": "https://download.example/full",
        },
        {
            "name": "Fameles_v2_Thumbnails.ijm",
            "download_url": "https://download.example/thumb",
        },
    ]
    session = FakeSession(
        {
            "https://api.figshare.com/v2/articles/22354405/files": FakeResponse(
                json_data=files_payload
            ),
            "https://download.example/trial": FakeResponse(content=trial_zip),
            "https://download.example/full": FakeResponse(content=b"full-macro"),
            "https://download.example/thumb": FakeResponse(content=b"thumb-macro"),
        }
    )

    destination_root = tmp_path / "assets"
    stage_root = download_and_stage_figshare_assets(destination_root, session=session)

    assert stage_root == destination_root
    assert (
        destination_root / "macros" / "original" / "Fameles_v2_Full_image.ijm"
    ).read_bytes() == b"full-macro"
    assert (
        destination_root / "macros" / "original" / "Fameles_v2_Thumbnails.ijm"
    ).read_bytes() == b"thumb-macro"
    assert (destination_root / "fixtures" / "trial_input" / "example.tif").read_bytes() == b"trial-image"


def test_download_file_retries_after_transient_chunked_failure(tmp_path: Path) -> None:
    destination = tmp_path / "fiji.zip"
    session = SequenceSession(
        [
            FailingThenSuccessfulResponse(content=b"bad-partial", fail_once=True),
            FailingThenSuccessfulResponse(content=b"good-archive"),
        ]
    )

    downloaded = _download_file(
        "https://download.example/fiji.zip",
        destination,
        session=session,
    )

    assert downloaded == destination
    assert destination.read_bytes() == b"good-archive"
    assert session.calls == 2


def test_extract_fiji_archive_returns_launcher_directory(tmp_path: Path) -> None:
    archive_path = tmp_path / "fiji.zip"
    archive_path.write_bytes(
        build_zip(
            {
                "Fiji/fiji-windows-x64.exe": b"binary",
                "Fiji/jars/example.jar": b"jar",
            }
        )
    )

    extract_root = tmp_path / "extract"
    fiji_dir = extract_fiji_archive(archive_path, extract_root)

    assert fiji_dir == (extract_root / "Fiji").resolve()
    assert (fiji_dir / "fiji-windows-x64.exe").exists()


def test_fiji_windows_archive_url_points_to_official_download_host() -> None:
    assert FIJI_WINDOWS_ARCHIVE_URL.startswith("https://downloads.imagej.net/fiji/latest/")
