"""Verify both immutable original evidence and the English offline replay.

Python 3.10+, macOS/Linux/WSL. No API credentials or model calls are used.
All executable checks and output generation run in temporary copies.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
STUDY = Path("experiments/120_fresh_v0.6")
OUT = STUDY / "outputs/fresh120_analysis"
HAN = re.compile(r"[\u3400-\u9fff]")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def safe(root, name):
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError("Expected relative path")
    p = root / name
    if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
        raise ValueError("Unsafe member: " + name)
    return p


def normalized_analysis(obj):
    obj = deepcopy(obj)
    obj.pop("created_utc", None)
    obj["costs"].pop("ledger_path", None)
    obj.pop("limitations_zh", None)
    obj.pop("limitations_en", None)
    return obj


def normalized_packet(obj):
    obj = deepcopy(obj)
    obj.pop("instructions_zh", None)
    obj.pop("instructions_en", None)
    return obj


def verify_files():
    manifest = load(ROOT / "PACKAGE_MANIFEST.json")
    if len({x["path"] for x in manifest["files"]}) != len(manifest["files"]):
        raise ValueError("Duplicate package paths")
    for item in manifest["files"]:
        p = safe(ROOT, item["path"])
        data = p.read_bytes()
        if len(data) != item["bytes"] or sha(data) != item["sha256"]:
            raise ValueError("Package member changed: " + item["path"])
        if HAN.search(item["path"]):
            raise ValueError("Untranslated visible filename")
        if p.suffix in (".py", ".cjs", ".command", ".html", ".txt") and HAN.search(data.decode("utf-8")):
            raise ValueError("Untranslated user-facing source or document: " + item["path"])
    localization = load(ROOT / "LOCALIZATION.json")
    archive = safe(ROOT, localization["original_archive"])
    if sha(archive.read_bytes()) != localization["original_archive_sha256"]:
        raise ValueError("Original archive differs")
    original = {}
    prefix = localization["original_archive_prefix"] + "/"
    with ZipFile(archive) as z:
        original_manifest = json.loads(z.read(prefix + "PACKAGE_MANIFEST.json"))
        for item in original_manifest["files"]:
            raw = z.read(prefix + item["path"])
            if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
                raise ValueError("Original archive member differs")
            original[item["path"]] = raw
        # Keep its manifest for the original verifier.
        original["PACKAGE_MANIFEST.json"] = z.read(prefix + "PACKAGE_MANIFEST.json")
    same = 0
    for name, raw in original.items():
        relative = name.removeprefix(str(STUDY) + "/")
        if (name.startswith("runs/") or
                name.startswith(str(STUDY) + "/") and
                (relative.startswith(("runs/", "data/public/", "data/private/", "data/schemas/", "config/")) or
                 relative in ("data/formal_freeze_v0.6.0.json", "data/formal_protocol_v0.6.0.json") or
                 relative.startswith("coprompt/") and relative != "coprompt/formal.py")):
            if safe(ROOT, name).read_bytes() != raw:
                raise ValueError("Original model/data/run evidence changed: " + name)
            same += 1
    # Derivative metadata may be translated; the metrics, IDs, order and records may not.
    old_out = str(STUDY) + "/outputs/" + "\u0031\u0032\u0030\u4f8b\u5168\u65b0\u5b9e\u9a8c\u5206\u6790/"
    old_analysis = json.loads(original[old_out + "analysis.json"])
    if normalized_analysis(old_analysis) != normalized_analysis(load(ROOT / OUT / "analysis.json")):
        raise ValueError("English analysis changes quantitative or provenance evidence")
    for slot in (1, 2):
        old_name = f"\u8bc4\u5ba1\u5458{slot}_\u72ec\u7acb\u8bc4\u5206\u8868.json"
        before = json.loads(original[old_out + old_name])
        after = load(ROOT / OUT / f"reviewer_{slot}_packet.json")
        if normalized_packet(before) != normalized_packet(after):
            raise ValueError("English reviewer packet changes source records, order, or ratings")
    active = load(ROOT / "experiments/ACTIVE_STUDY.json")
    for key in ("launch_file", "current_budget_note", "analysis_path", "interpretation_report"):
        path = safe(ROOT / "experiments", active[key])
        if not path.is_file() or HAN.search(active[key]):
            raise ValueError("Broken English study index reference: " + key)
    if sha((ROOT / "experiments" / active["analysis_path"]).read_bytes()) != active["analysis_sha256"]:
        raise ValueError("English study index analysis hash differs")
    reading = load(ROOT / STUDY / "data/protocol_reading_edition.json")
    if not safe(ROOT / STUDY, reading["value_policy"]["selection_result_file"]).is_file():
        raise ValueError("Broken selection reference in reading protocol")
    return manifest, localization, original, same


def run(cmd, cwd, timeout=180):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError("Offline check failed:\n" + result.stdout + result.stderr)
    return result.stdout, result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--node", help="Optional Node 18+ executable for reviewer interface checks")
    parser.add_argument("--export-analysis", type=Path, help="New external directory for recomputed English analysis")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise ValueError("Python 3.10 or newer is required")
    manifest, localization, originals, preserved = verify_files()
    manifest_hash = sha((ROOT / "PACKAGE_MANIFEST.json").read_bytes())
    receipt = {"status": "english_handoff_hashes_verified",
               "verified_utc": datetime.now(timezone.utc).isoformat(),
               "verified_manifest_sha256": manifest_hash,
               "files_verified": len(manifest["files"]),
               "unchanged_model_data_and_run_files": preserved,
               "revision": "EN1", "api_calls": 0, "original_package_modified": False,
               "english_user_facing_source_and_paths": True,
               "review_records_ids_order_ratings_unchanged": True}
    if args.manifest_only:
        print(json.dumps(receipt, indent=2))
        return
    if sys.platform == "win32":
        raise ValueError("Full replay requires macOS, Linux or Windows WSL (fcntl).")
    if args.export_analysis and args.export_analysis.exists():
        raise ValueError("Analysis export destination already exists")
    with tempfile.TemporaryDirectory(prefix="coprompt-en1-check-") as folder:
        base = Path(folder)
        original = base / "original"
        localized = base / "english"
        # Rebuild exact original package in isolation, never from unverified extras.
        for name, raw in originals.items():
            p = safe(original, name)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        for member in manifest["files"]:
            p = safe(localized, member["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(safe(ROOT, member["path"]), p)
        shutil.copy2(ROOT / "PACKAGE_MANIFEST.json", localized / "PACKAGE_MANIFEST.json")
        stdout, _ = run([sys.executable, "-B", "handoff/verify_fresh_handoff.py"], original)
        original_receipt = json.loads(stdout)
        if original_receipt["status"] != "complete_fresh120_handoff_verified":
            raise ValueError("Original replay did not complete")
        # Native English tools must work; the original analysis is not merely relabeled.
        study = localized / STUDY
        run([sys.executable, "-B", "tools/preflight_fresh.py"], study)
        stdout, _ = run([sys.executable, "-B", "tools/show_status.py"], study)
        if HAN.search(stdout):
            raise ValueError("Status output is not English")
        run([sys.executable, "-B", "tools/analyze_fresh.py"], study)
        recomputed = load(localized / OUT / "analysis.json")
        if normalized_analysis(recomputed) != normalized_analysis(load(ROOT / OUT / "analysis.json")):
            raise ValueError("English replay differs from packaged analysis")
        for slot in (1, 2):
            if load(localized / OUT / f"reviewer_{slot}_packet.json") != load(ROOT / OUT / f"reviewer_{slot}_packet.json"):
                raise ValueError("English replay changed reviewer material")
        stdout, stderr = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-q"], study)
        receipt["localized_tests"] = (stdout + stderr).strip()
        receipt["original_tests"] = original_receipt["offline_test_summary"]
        if args.node:
            stdout, _ = run([args.node, "work/fresh120_review_form/check_logic.cjs"], localized)
            receipt["review_form_checks"] = json.loads(stdout)
        # Reject actual changes to a localized frozen method instead of bypassing checks.
        tamper = study / "coprompt/runner.py"
        tamper.write_bytes(tamper.read_bytes() + b"\n# QA mutation must be rejected\n")
        rejected = subprocess.run([sys.executable, "-B", "tools/preflight_fresh.py"], cwd=study,
                                  text=True, capture_output=True, timeout=30)
        if rejected.returncode == 0:
            raise ValueError("Localized freeze failed to reject a changed method")
        receipt.update(status="english_handoff_verified",
                       completed_logical_trajectories=recomputed["completed_trajectories"]["total"],
                       dataset_cases=recomputed["dataset_cases"],
                       selected_lambda=recomputed["validation_selection"]["selected_lambda"],
                       cumulative_accounted_usd=recomputed["costs"]["cumulative_accounted_usd"],
                       original_and_english_analyses_equivalent=True,
                       original_frozen_files_verified=original_receipt["frozen_files_verified"],
                       localized_freeze_tamper_rejected=True,
                       human_review="pending_actual_reviewers",
                       browser_rendering="not_certified; local browser preview was previously blocked")
        if args.export_analysis:
            target = args.export_analysis.expanduser().resolve()
            if target.is_relative_to(ROOT):
                raise ValueError("Export outside the package")
            shutil.copytree(localized / OUT, target)
            receipt["exported_analysis"] = str(target)
    if sha((ROOT / "PACKAGE_MANIFEST.json").read_bytes()) != manifest_hash:
        raise ValueError("Original package was changed during verification")
    verify_files()
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ImportError, subprocess.SubprocessError) as error:
        print("Verification failed: " + str(error), file=sys.stderr)
        sys.exit(1)
