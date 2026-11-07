"""Build the EN1 handoff as a documented localization, retaining original evidence."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
NAME = "CoPrompt_Fresh120_v0.6.0_EN1_2026-10-20"
DEST = ROOT / "outputs" / NAME
STUDY = Path("experiments/120_fresh_v0.6")
BASE_NAME = "CoPrompt_\u5168\u65b0120\u4f8b_\u4ea4\u63a5\u5305_v0.6.0_docs1_2026-10-20"
BASE_ZIP = ROOT / "outputs" / (BASE_NAME + ".zip")
if (ROOT / "audit/original_evidence.zip").is_file():
    BASE_ZIP = ROOT / "audit/original_evidence.zip"
EXPECTED_BASE_SHA = "dfca37ba74bc5f151c05e1b6ef6e5121b628459d26672fe5b11bb4d2fae6333e"

spec = importlib.util.spec_from_file_location("english_source_translation", WORK / "source_translation/translation_map.py")
translation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation)
PATHS = {
    **translation.PATH_REPLACEMENTS,
    "\u6838\u9a8c\u4ea4\u63a5\u5305.command": "verify_package.command",
    "\u6765\u6e90\u6838\u5bf9.json": "source_record.json",
    "\u4ec5\u4f5c\u6765\u6e90\u6392\u67e5\u53c2\u8003.txt": "PROVENANCE_ONLY.txt",
    "\u5f53\u524d\u9884\u7b97\u8bf4\u660e.txt": "budget_note.txt",
    "\u5f53\u524d\u7248\u672c\u9605\u8bfb\u8bf4\u660e.txt": "READ_FIRST.txt",
    "\u5b9e\u9a8c\u65b9\u6cd5\u8bf4\u660e.txt": "METHODS.txt",
    "formal_protocol_v0.6.0_\u8bf4\u660e\u8865\u5168\u7248.json": "protocol_reading_edition.json",
    "\u534f\u8bae\u9605\u8bfb\u987a\u5e8f.txt": "PROTOCOL_README.txt",
    "\u7ed3\u679c\u4e0e\u65b9\u6cd5\u8bf4\u660e.txt": "methods_and_results.txt",
    "120\u4f8b\u4eba\u5de5\u8bc4\u5ba1\u6750\u6599.zip": "human_review_materials.zip",
    "\u4eba\u5de5\u8bc4\u5ba1\u8868": "review_forms",
    "\u4f7f\u7528\u8bf4\u660e.txt": "README.txt",
    "\u8bc4\u5ba1\u54581_\u9605\u8bfb\u586b\u5199\u8868.html": "reviewer_1.html",
    "\u8bc4\u5ba1\u54582_\u9605\u8bfb\u586b\u5199\u8868.html": "reviewer_2.html",
}
HAN = re.compile(r"[\u3400-\u9fff]")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def renamed(name):
    for old, new in sorted(PATHS.items(), key=lambda item: -len(item[0])):
        name = name.replace(old, new)
    return name


def write(rel, data):
    p = DEST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


def dump(rel, obj):
    write(rel, json.dumps(obj, ensure_ascii=True, indent=2) + "\n")


def output(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    return result.stdout


def manifest():
    files = []
    for p in sorted(DEST.rglob("*")):
        if not p.is_file() or p.name == "PACKAGE_MANIFEST.json":
            continue
        if "__pycache__" in p.parts or p.suffix in (".pyc", ".lock"):
            raise ValueError("Disposable file in package: " + str(p))
        rel = str(p.relative_to(DEST))
        if HAN.search(rel):
            raise ValueError("Non-English visible filename: " + rel)
        data = p.read_bytes()
        if re.search(rb"sk-or-v1-[A-Za-z0-9]{32,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}", data):
            raise ValueError("Potential credential in package: " + rel)
        if p.suffix in (".py", ".cjs", ".command", ".html", ".txt") and HAN.search(data.decode("utf-8")):
            raise ValueError("Untranslated user-facing text/source: " + rel)
        files.append({"path": rel, "bytes": len(data), "sha256": sha(data)})
    record = {"package": NAME, "revision": "EN1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "client_date": "2026-10-20", "study": str(STUDY),
              "original_experiment_version": "0.6.0+budget-precision-1",
              "post_run_localization_not_new_experiment": True, "api_calls": 0,
              "files": files, "manifest_self_hash_excluded": True}
    dump("PACKAGE_MANIFEST.json", record)
    return record


def stage():
    if DEST.exists():
        raise ValueError("Destination exists; do not overwrite a handoff.")
    if sha(BASE_ZIP.read_bytes()) != EXPECTED_BASE_SHA:
        raise ValueError("Baseline handoff differs from the audited snapshot.")
    DEST.mkdir(parents=True)
    original_files = {}
    with ZipFile(BASE_ZIP) as z:
        old_manifest = json.loads(z.read(BASE_NAME + "/PACKAGE_MANIFEST.json"))
        for item in old_manifest["files"]:
            name = item["path"]
            raw = z.read(BASE_NAME + "/" + name)
            if sha(raw) != item["sha256"]:
                raise ValueError("Baseline member changed: " + name)
            original_files[name] = raw
            if (name.startswith(("handoff/", "work/handoff_fresh120/", "work/fresh120_review_form/")) or
                    name.startswith(str(STUDY / "amendments/method_documentation_20261020")) or
                    name in ("README.txt", "\u6838\u9a8c\u4ea4\u63a5\u5305.command") or
                    "/\u4eba\u5de5\u8bc4\u5ba1\u8868/" in name or name.endswith("120\u4f8b\u4eba\u5de5\u8bc4\u5ba1\u6750\u6599.zip")):
                continue
            target = renamed(name)
            if name in translation.SOURCE_FILES:
                raw = translation.translate_source(name, raw.decode()).encode()
            if name.endswith("outputs/120\u4f8b\u5168\u65b0\u5b9e\u9a8c\u5206\u6790/analysis.json") or re.search(r"/\u8bc4\u5ba1\u5458[12]_\u72ec\u7acb\u8bc4\u5206\u8868.json$", name):
                raw = (json.dumps(translation.translate_metadata(json.loads(raw)), ensure_ascii=True, indent=2) + "\n").encode()
            if name.endswith("work/budget_forecast.json"):
                raw = (json.dumps(translation.translate_metadata(json.loads(raw)), ensure_ascii=True, indent=2) + "\n").encode()
            write(target, raw)
    write("audit/original_evidence.zip", BASE_ZIP.read_bytes())
    write("audit/README.txt", """Original evidence and language boundary

original_evidence.zip is the exact, hash-verified docs-1 handoff before English localization.
It retains the 71 frozen files, original Chinese launcher/messages, budget-amendment
before/ sources, original review tools, logs, all trajectories and prior documentation.
Do not translate or re-freeze this archive and claim it was the original run.

The English source tree is a post-run presentation and offline-replay revision (EN1).
LOCALIZATION.json explicitly maps original file hashes to localized paths/hashes.
The original freeze bytes and all experimental records are retained unchanged.
Model-visible field descriptions, raw model requests/responses and authoring metadata
can contain Chinese. They remain immutable evidence, not untranslated reviewer UI.
English interfaces and documentation do not silently rewrite those model inputs.
""")
    # Replace human reading documents, never the model-facing field catalog or data.
    write("README.txt", (WORK / "docs/README.txt").read_bytes())
    write(STUDY / "docs/METHODS.txt", (WORK / "docs/METHODS.txt").read_bytes())
    write(STUDY / "outputs/fresh120_analysis/results_interpretation.txt",
          (WORK / "docs/results_interpretation.txt").read_bytes())
    study_readme = """CoPrompt Fresh 120-Case Study - English handoff (EN1)

Read docs/METHODS.txt, data/protocol_reading_edition.json, and
outputs/fresh120_analysis/results_interpretation.txt.
The top-level README.txt explains every component and the next review steps.

This is a post-run language/path localization of an already completed study:
40 design + 20 validation + 60 test cases; 480 logical trajectories.
Human review is pending. No model was called to localize this package.
The original freeze and evidence are preserved in ../../audit/original_evidence.zip.
Localization is separately declared and does not masquerade as the original sources.

Double-click run_fresh120.command for offline verification; it does not ask for a key.
Or, from the package root, run: python3 -B handoff/verify_handoff.py
Python 3.10+ on macOS/Linux/WSL is required for full replay (POSIX fcntl).
The HTML reviewer forms need only a browser and work offline.

The original protocol/config budget of USD 0.25 is a preparation-time snapshot.
The final authorized historical cumulative cap is USD 2.00; the recorded cumulative
cost is USD 0.17262309. The transferred record is not a new spending authorization.
Immutable model-visible field descriptions may contain Chinese; their English
meaning is explained in METHODS.txt. Translating them would alter the experiment.
"""
    write(STUDY / "README.txt", study_readme)
    write(STUDY / "READ_FIRST.txt", study_readme)
    write(STUDY / "data/PROTOCOL_README.txt", """Read protocol_reading_edition.json and ../docs/METHODS.txt.
formal_protocol_v0.6.0.json is the unchanged execution-time protocol.
The reading edition explains its mechanism in English after the completed run.
It is not a new preregistration and does not replace the historical protocol.
Preparation-time null/lower-budget values are not the final selected threshold or cap.
""")
    write(STUDY / "budget_note.txt", """Budget history
At 2026-10-19T15:04:30.455262+00:00, the user raised the cumulative cap to USD 2.00,
including previous spending. At that moment USD 0.08857385 was accounted.
Those figures are a historical snapshot. Final cumulative accounted cost is
USD 0.17262309, including the fresh study USD 0.08404924 and an unknown-cost reserve.
Authoritative records: project-root runs/authorized_pilot_budget.json and
runs/budget_authorization_changes.jsonl. No additional spend is authorized by EN1.
""")
    write("experiments/120_v0.5/PROVENANCE_ONLY.txt",
          "Reference requests/annotations for provenance checks only; not the current dataset, results or model input.\n")
    write(STUDY / "amendments/method_documentation_20261020/README.txt",
          "The docs-1 wording amendment and its original before/ documents are preserved in audit/original_evidence.zip at the package root. EN1 provides English reading documents, not replacement historical records.\n")
    # Frozen-source verification recognizes localization explicitly, with true hashes.
    write(STUDY / "coprompt/localization.py", (WORK / "localization.py").read_bytes())
    formal = DEST / STUDY / "coprompt/formal.py"
    text = formal.read_text()
    text = text.replace("def verify_freeze(root, freeze):\n",
                        "def verify_freeze(root, freeze):\n"
                        "    from .localization import verify_localized_freeze\n"
                        "    if verify_localized_freeze(root, freeze):\n"
                        "        return\n", 1)
    text = text.replace("    config = load(root / 'config/openrouter.v0.6.formal.json')\n",
                        "    if (root.parents[1] / 'LOCALIZATION.json').is_file():\n"
                        "        raise ValueError('EN1 is a completed-study replay. New paid experiments require a new version and authorization.')\n"
                        "    config = load(root / 'config/openrouter.v0.6.formal.json')\n", 1)
    formal.write_text(text)
    # Source-only tool translations and their exact original/English maps are portable.
    for source in ("build_package.py", "localization.py", "verify_handoff.py"):
        text = (WORK / source).read_text()
        # Escape source-language lookup keys in the portable builder; English outputs stay English.
        text = "".join(f"\\u{ord(c):04x}" if HAN.match(c) else c for c in text)
        write("work/handoff_fresh120/" + source, text)
    for file in ("translation_map.py", "case_titles_en.json"):
        data = (WORK / "source_translation" / file).read_text()
        if file.endswith(".py"):
            data = "".join(f"\\u{ord(c):04x}" if HAN.match(c) else c for c in data)
        write("work/handoff_fresh120/source_translation/" + file, data)
    write(STUDY / "data/case_titles_en.json", (WORK / "source_translation/case_titles_en.json").read_bytes())
    for source in ("README.txt", "METHODS.txt", "results_interpretation.txt"):
        write("work/handoff_fresh120/docs/" + source, (WORK / "docs" / source).read_bytes())
    for name in ("template.html", "build.py", "check_logic.cjs", "README.txt", "packet_compatibility.json"):
        p = WORK / "review_forms" / name
        write("work/fresh120_review_form/" + p.name, p.read_bytes())
        write("work/handoff_fresh120/review_forms/" + p.name, p.read_bytes())
    write("handoff/verify_handoff.py", (WORK / "verify_handoff.py").read_bytes())
    write("verify_package.command", """#!/bin/zsh
set -u
COPROMPT_PACKAGE_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$COPROMPT_PACKAGE_DIR" || exit 1
print 'Offline verification of original evidence and English presentation. No key or API needed.'
python3 -B handoff/verify_handoff.py
COPROMPT_CHECK_STATUS=$?
read '?Press Enter to close.'
exit $COPROMPT_CHECK_STATUS
""")
    write(STUDY / "run_fresh120.command", """#!/bin/zsh
set -u
COPROMPT_STUDY_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$COPROMPT_STUDY_DIR/../.." || exit 1
print 'The 120-case experiment is complete. Replaying saved evidence offline; no API key is needed.'
python3 -B handoff/verify_handoff.py
COPROMPT_CHECK_STATUS=$?
read '?Press Enter to close.'
exit $COPROMPT_CHECK_STATUS
""")
    for p in (DEST / "verify_package.command", DEST / STUDY / "run_fresh120.command"):
        p.chmod(0o755)
    # Create the reading protocol from the unchanged English original plus precise detail.
    protocol = json.loads(original_files[str(STUDY / "data/formal_protocol_v0.6.0.json")])
    protocol["documentation_revision"] = {
        "id": "EN1", "date": "2026-10-20", "not_a_new_preregistration": True,
        "original_protocol_sha256": sha(original_files[str(STUDY / "data/formal_protocol_v0.6.0.json")]),
        "complete_method": "docs/METHODS.txt", "original_status": protocol["status"],
        "original_created_utc_is_preparation_time": True,
        "current_state": "480 trajectories completed; validation selected lambda=0.25; cumulative cap USD 2.00; human review pending.",
    }
    protocol["status"] = "post_run_English_reading_edition"
    protocol["explanation_language"] = "en"
    protocol["value_policy"]["selection_result_file"] = "outputs/CoPrompt_validation_v0.6.0/lambda_selection.json"
    protocol["complete_method_description"] = (WORK / "docs/METHODS.txt").read_text()
    protocol["authoring_provenance"]["limits"] = (
        "The method uses source-unit extraction and evidence checks, four ASK/ACT policies, a fixed field-answer simulator, "
        "common JSON generation with bounded format/visible-constraint repair, computed schedule summaries, hidden-constraint scoring, "
        "and paired case analysis. Exact rules are included in complete_method_description and docs/METHODS.txt. "
        "The method had prior development and the coordinator had seen historical results; isolated author contexts do not prove zero contamination.")
    protocol["generation"]["plan_summary"] = (
        "For a format-valid study plan, sum minutes from the final schedule overall, per date and per normalized topic; replace only summary. "
        "Report recognized visible-constraint violations or the limited scope of passing checks; preserve the original summary in provenance. "
        "Do not modify schedule rows or make another model call.")
    protocol["generation"]["execution_details"] = (
        "Initial generation plus at most one format repair. If a valid draft violates recognized visible constraints, one additional constraint "
        "revision uses the same public context and complete measurements. That revision gets no further format retry. "
        "Accept a format-valid revision even if quality declines; otherwise preserve the valid draft. At most three generation calls, no hidden-score selection.")
    protocol["changes_from_proposal"] = [
        "The 120-case size, 40/20/60 split, four main policies and 20-case importance diagnostic implement the main planned scale.",
        "Prompts and scoring were fixed before this fresh pilot; its 40 design cases checked the workflow rather than developing the method from these outputs.",
        "Case authoring used separate author contexts and coordinator/offline checks, not five human authors each writing and cross-reviewing 24 cases.",
        "Source-unit evidence selection and limited semantic guards specify the shared extraction implementation.",
        "A further one-shot visible-constraint revision and a deterministic schedule summary supplement the planned format repair, equally across policies.",
        "Lambda selection specifies larger lambda as a final tie-break after equal quality and question burden.",
        "Two actual reviewers were not assigned before case authoring and 200 human assessments remain incomplete.",
        "The final user-authorized cumulative cap is USD 2.00, including history, rather than the proposal's USD 15 planning allowance.",
        "The experiment and offline reviewer forms do not constitute the proposed Streamlit agent demonstration.",
    ]
    dump(STUDY / "data/protocol_reading_edition.json", protocol)
    # Generate the English public catalog without changing the underlying case plan.
    output([sys.executable, "-B", "work/build_catalog.py"], DEST / STUDY)
    # Record exact separate file identities for every original frozen source.
    freeze = json.loads(original_files[str(STUDY / "data/formal_freeze_v0.6.0.json")])
    frozen_map = {}
    for name, digest in freeze["files"].items():
        target = renamed(str(STUDY / name))
        frozen_map[name] = {"localized_path": str(Path(target).relative_to(STUDY)),
                            "original_sha256": digest, "localized_sha256": sha((DEST / target).read_bytes())}
    localization = {
        "revision": "EN1", "study": str(STUDY), "original_archive": "audit/original_evidence.zip",
        "original_archive_sha256": EXPECTED_BASE_SHA, "original_archive_prefix": BASE_NAME,
        "original_freeze_sha256": sha(original_files[str(STUDY / "data/formal_freeze_v0.6.0.json")]),
        "post_run_localization_only": True, "api_calls": 0,
        "frozen_file_mapping": frozen_map,
        "model_visible_inputs_and_trajectory_records_unchanged": True,
        "immutable_language_exception": "Original model-visible field descriptions and evidence metadata may contain Chinese; never translated.",
    }
    dump("LOCALIZATION.json", localization)
    # Run the localized analyzer once to create English derived summaries/metadata.
    output([sys.executable, "-B", "tools/analyze_fresh.py"], DEST / STUDY)
    active = json.loads(original_files["experiments/ACTIVE_STUDY.json"])
    active.update(
        presentation_revision="EN1",
        source_active_study_sha256=sha(original_files["experiments/ACTIVE_STUDY.json"]),
        original_record="audit/original_evidence.zip::experiments/ACTIVE_STUDY.json",
        user_scope="Start over with 120 newly authored cases.",
        user_scope_clarification="Retain the existing method; isolate the data and results.",
    )
    for key in ("launch_file", "current_budget_note", "analysis_path", "interpretation_report"):
        active[key] = renamed(active[key])
    active["analysis_sha256"] = sha((DEST / "experiments" / active["analysis_path"]).read_bytes())
    dump("experiments/ACTIVE_STUDY.json", active)
    write(STUDY / "outputs/fresh120_analysis/methods_and_results.txt",
          (WORK / "docs/METHODS.txt").read_text() + "\n\nAUTOMATIC RESULTS\n\n" +
          (DEST / STUDY / "outputs/fresh120_analysis/results_summary.txt").read_text())
    output([sys.executable, "-B", "work/fresh120_review_form/build.py"], DEST)
    record = manifest()
    return {"directory": str(DEST), "files": len(record["files"]) + 1}


def seal():
    receipt = json.loads((WORK / "verification_receipt.json").read_text())
    if receipt["status"] != "english_handoff_verified" or receipt["verified_manifest_sha256"] != sha((DEST / "PACKAGE_MANIFEST.json").read_bytes()):
        raise ValueError("Full verification receipt must match the current package.")
    dump("handoff/verification_receipt.json", receipt)
    record = manifest()
    archive = DEST.with_name(DEST.name + ".zip")
    with ZipFile(archive, "w", ZIP_DEFLATED) as z:
        for p in sorted(DEST.rglob("*")):
            if p.is_file():
                z.write(p, str(Path(NAME) / p.relative_to(DEST)))
    with ZipFile(archive) as z:
        if z.testzip():
            raise ValueError("ZIP CRC failed")
        for item in record["files"]:
            if sha(z.read(NAME + "/" + item["path"])) != item["sha256"]:
                raise ValueError("ZIP member differs from manifest")
    digest = sha(archive.read_bytes())
    archive.with_name(archive.name + ".sha256.txt").write_text(digest + "  " + archive.name + "\n")
    return {"archive": str(archive), "bytes": archive.stat().st_size, "files": len(record["files"]) + 1, "sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("stage", "seal"))
    args = parser.parse_args()
    print(json.dumps(stage() if args.action == "stage" else seal(), indent=2))
