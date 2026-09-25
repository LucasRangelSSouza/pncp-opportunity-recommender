"""Resolve the pinned public PNCP Kaggle release and verify it byte for byte.

The Kaggle package flattens layer paths (`raw/records.parquet` becomes
`raw_records.parquet`), so verification maps manifest paths to package names.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class PinnedRelease:
    slug: str
    version: int
    manifest_sha256: str
    schema_version: str

    @property
    def handle(self) -> str:
        return f"{self.slug}/versions/{self.version}"


PNCP_RELEASE_V1 = PinnedRelease(
    slug="lucasrangelss/brazil-pncp-procurement-history",
    version=1,
    manifest_sha256="9301e83840fc575b841bcce31cff19a6b72bd37528a88fdee4b50c2fddb20c66",
    schema_version="1.1",
)


class ReleaseVerificationError(ValueError):
    """The local package differs from the approved release."""


@dataclass(frozen=True)
class VerifiedRelease:
    pin: PinnedRelease
    directory: Path
    manifest: dict

    def layer(self, name: str) -> Path:
        return self.directory / f"{name}_records.parquet"

    def lineage(self) -> dict[str, object]:
        return {
            "dataset": self.pin.slug,
            "dataset_version": self.pin.version,
            "manifest_sha256": self.pin.manifest_sha256,
            "schema_version": self.manifest["schema_version"],
            "source_build_commit": self.manifest["git_commit"],
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def package_name(manifest_path: str) -> str:
    return manifest_path.replace("/", "_")


def verify_release(directory: Path, pin: PinnedRelease = PNCP_RELEASE_V1) -> VerifiedRelease:
    manifest_path = directory / "release_manifest.json"
    if not manifest_path.is_file():
        raise ReleaseVerificationError("release_manifest.json is missing")
    actual = sha256_file(manifest_path)
    if actual != pin.manifest_sha256:
        raise ReleaseVerificationError(f"manifest hash {actual} is not the approved {pin.handle}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("privacy_gate") != "passed":
        raise ReleaseVerificationError("release privacy gate did not pass")
    if manifest.get("schema_version") != pin.schema_version:
        raise ReleaseVerificationError(f"unsupported schema version {manifest.get('schema_version')}")
    for entry in manifest["files"]:
        file_path = directory / package_name(entry["path"])
        if not file_path.is_file():
            raise ReleaseVerificationError(f"release file missing: {file_path.name}")
        if sha256_file(file_path) != entry["sha256"]:
            raise ReleaseVerificationError(f"release file hash mismatch: {file_path.name}")
    return VerifiedRelease(pin=pin, directory=directory, manifest=manifest)


def _kagglehub_download(handle: str) -> Path:
    import kagglehub

    return Path(kagglehub.dataset_download(handle))


def resolve_release(
    release_dir: Path | None = None,
    pin: PinnedRelease = PNCP_RELEASE_V1,
    downloader: Callable[[str], Path] = _kagglehub_download,
) -> VerifiedRelease:
    """Use a local copy when supplied, otherwise download the pinned Kaggle version.

    Public datasets download without a Kaggle credential.
    """
    directory = release_dir if release_dir is not None else downloader(pin.handle)
    return verify_release(Path(directory), pin)
