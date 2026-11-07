"""Verify a declared English presentation against the original frozen evidence.

This does not change the historic freeze, any model input, or any trajectory hash.
The English files have separate hashes and are never claimed to be the originals.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_localized_freeze(root, freeze):
    root = Path(root).resolve()
    project = root.parents[1]
    marker = project / "LOCALIZATION.json"
    if not marker.is_file():
        return False
    record = json.loads(marker.read_text())
    if (record.get("revision") != "EN1" or
            root != (project / record["study"]).resolve()):
        raise ValueError("Unexpected localization scope")
    archive = project / record["original_archive"]
    if sha(archive.read_bytes()) != record["original_archive_sha256"]:
        raise ValueError("Original evidence archive changed")
    prefix = record["original_archive_prefix"] + "/" + record["study"] + "/"
    with ZipFile(archive) as z:
        original_bytes = z.read(prefix + "data/formal_freeze_v0.6.0.json")
        if (json.loads(original_bytes) != freeze or
                (root / "data/formal_freeze_v0.6.0.json").read_bytes() != original_bytes):
            raise ValueError("Historic freeze changed")
        if set(record["frozen_file_mapping"]) != set(freeze["files"]):
            raise ValueError("Incomplete localized frozen-file mapping")
        for original_name, original_hash in freeze["files"].items():
            entry = record["frozen_file_mapping"][original_name]
            original = z.read(prefix + original_name)
            local = root / entry["localized_path"]
            if not local.resolve().is_relative_to(root):
                raise ValueError("Localized path escapes study")
            if (sha(original) != original_hash or
                    entry["original_sha256"] != original_hash or
                    sha(local.read_bytes()) != entry["localized_sha256"]):
                raise ValueError("Original or English source differs from declared mapping: " + original_name)
    return True
