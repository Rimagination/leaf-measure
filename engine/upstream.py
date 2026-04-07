from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import zipfile

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError
from urllib3.util.retry import Retry

from engine.fiji import resolve_fiji_installation


FIGSHARE_ARTICLE_ID = "22354405"
FIGSHARE_FILES_URL = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}/files"
FIGSHARE_REQUIRED_FILES = (
    "Trial.zip",
    "Fameles_v2_Full_image.ijm",
    "Fameles_v2_Thumbnails.ijm",
)
FIJI_WINDOWS_ARCHIVE_URL = "https://downloads.imagej.net/fiji/latest/fiji-latest-win64-jdk.zip"


def _copy_visible_children(source_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for child in source_dir.iterdir():
        if child.name.startswith("."):
            continue
        target = destination_dir / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def stage_assets_from_source(source_root: Path, destination_root: Path) -> Path:
    source_root = source_root.resolve()
    destination_root = destination_root.resolve()

    full_candidates = [
        source_root / "data" / "Fameles_v2_Full_image.ijm",
        source_root / "Fameles_v2_Full_image.ijm",
    ]
    thumbnail_candidates = [
        source_root / "data" / "Fameles_v2_Thumbnails.ijm",
        source_root / "Fameles_v2_Thumbnails.ijm",
    ]
    trial_candidates = [
        source_root / "data" / "Trial" / "Trial" / "01_input",
        source_root / "Trial" / "Trial" / "01_input",
        source_root / "Trial" / "01_input",
    ]
    golden_candidates = [
        source_root / "golden",
        source_root / "data" / "golden",
    ]

    full_macro = next((path for path in full_candidates if path.exists()), None)
    thumbnail_macro = next((path for path in thumbnail_candidates if path.exists()), None)
    if full_macro is None or thumbnail_macro is None:
        raise FileNotFoundError(f"Could not find FAMeLeS macro files under {source_root}")

    macros_root = destination_root / "macros" / "original"
    macros_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full_macro, macros_root / "Fameles_v2_Full_image.ijm")
    shutil.copy2(thumbnail_macro, macros_root / "Fameles_v2_Thumbnails.ijm")

    trial_dir = next((path for path in trial_candidates if path.exists()), None)
    if trial_dir is not None:
        _copy_visible_children(trial_dir, destination_root / "fixtures" / "trial_input")

    golden_dir = next((path for path in golden_candidates if path.exists()), None)
    if golden_dir is not None:
        target = destination_root / "golden"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(golden_dir, target)

    return destination_root


def _download_file(url: str, destination: Path, *, session: requests.Session, attempts: int = 3) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, timeout=120, stream=True)
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        handle.write(chunk)
            return destination
        except (ChunkedEncodingError, RequestsConnectionError) as error:
            last_error = error
            if destination.exists():
                destination.unlink()
            if attempt == attempts:
                raise

    assert last_error is not None
    raise last_error


def build_http_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def download_and_stage_figshare_assets(
    destination_root: Path,
    *,
    article_id: str = FIGSHARE_ARTICLE_ID,
    session: requests.Session | None = None,
) -> Path:
    destination_root = destination_root.resolve()
    files_url = f"https://api.figshare.com/v2/articles/{article_id}/files"
    metadata_session = session or requests.Session()
    download_session = session or build_http_session()
    response = metadata_session.get(files_url, timeout=60)
    response.raise_for_status()
    files = response.json()
    by_name = {entry["name"]: entry for entry in files}
    missing = [name for name in FIGSHARE_REQUIRED_FILES if name not in by_name]
    if missing:
        raise FileNotFoundError(
            f"Figshare article {article_id} is missing required file(s): {', '.join(missing)}"
        )

    with tempfile.TemporaryDirectory(prefix="leaf-measure-assets-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        source_root = temp_dir / "source"
        source_root.mkdir(parents=True, exist_ok=True)

        _download_file(
            by_name["Fameles_v2_Full_image.ijm"]["download_url"],
            source_root / "Fameles_v2_Full_image.ijm",
            session=download_session,
        )
        _download_file(
            by_name["Fameles_v2_Thumbnails.ijm"]["download_url"],
            source_root / "Fameles_v2_Thumbnails.ijm",
            session=download_session,
        )
        trial_zip = _download_file(
            by_name["Trial.zip"]["download_url"],
            temp_dir / "Trial.zip",
            session=download_session,
        )
        with zipfile.ZipFile(trial_zip) as archive:
            archive.extractall(source_root)

        return stage_assets_from_source(source_root, destination_root)


def extract_fiji_archive(archive_path: Path, extract_root: Path) -> Path:
    archive_path = archive_path.resolve()
    extract_root = extract_root.resolve()
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_root)

    candidates = [extract_root, *extract_root.glob("*")]
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        resolved = resolve_fiji_installation(candidate)
        if resolved is None:
            continue
        return resolved.root_dir
    raise FileNotFoundError(f"Could not find a Fiji launcher after extracting {archive_path}")


def download_and_extract_fiji(
    destination_root: Path,
    *,
    archive_url: str = FIJI_WINDOWS_ARCHIVE_URL,
    session: requests.Session | None = None,
) -> Path:
    destination_root = destination_root.resolve()
    if destination_root.exists():
        resolved = resolve_fiji_installation(destination_root / "Fiji")
        if resolved is not None:
            return resolved.root_dir
        resolved = resolve_fiji_installation(destination_root)
        if resolved is not None:
            return resolved.root_dir

    session = session or build_http_session()
    with tempfile.TemporaryDirectory(prefix="leaf-measure-fiji-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_path = _download_file(archive_url, temp_dir / "fiji.zip", session=session)
        return extract_fiji_archive(archive_path, destination_root)
