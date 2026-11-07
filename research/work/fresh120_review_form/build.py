"""Build English offline forms from this fresh study's anonymous review packets."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

BASE = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
SOURCE = BASE / "experiments/120_fresh_v0.6/outputs/fresh120_analysis"
DEST = SOURCE / "review_forms"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    DEST.mkdir(exist_ok=True)
    template = (WORK / "template.html").read_text(encoding="utf-8")
    assert template.count("__PACKET__") == 1
    assert not re.search(r"[\u3400-\u9fff]", template)
    compatibility = json.loads(
        (WORK / "packet_compatibility.json").read_text(encoding="utf-8")
    )
    manifest = {
        "form_version": "fresh120-review-form-1",
        "interface_language": "en",
        "sources": [],
        "outputs": [],
        "model_calls": 0,
        "original_packets_modified": False,
        "private_strategy_mapping_included": False,
    }
    for slot in (1, 2):
        source = SOURCE / f"reviewer_{slot}_packet.json"
        raw = source.read_bytes()
        packet = json.loads(raw)
        assert packet["reviewer_slot"] == slot and len(packet["records"]) == 100
        assert len({r["review_item_id"] for r in packet["records"]}) == 100
        forbidden = {
            "system_id", "case_id", "score", "lambda_value",
            "importance_override", "underlying_policy",
        }
        assert all(not forbidden.intersection(r) for r in packet["records"])
        assert all(v is None for r in packet["records"] for v in r["ratings"].values())
        records_hash = digest(json.dumps(
            packet["records"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"))
        baseline = compatibility["reviewer_slots"][str(slot)]
        assert records_hash == baseline["records_sha256"], (
            "Record content, order, anonymous IDs, or initial ratings changed"
        )
        assert packet["source_evidence_sha256"] == baseline["source_evidence_sha256"]
        material = {
            "source_packet_sha256": digest(raw),
            "compatible_source_packet_sha256": [baseline["source_packet_sha256"]],
            "packet": packet,
        }
        payload = json.dumps(
            material, ensure_ascii=False, separators=(",", ":")
        ).replace("<", "\\u003c")
        target = DEST / f"reviewer_{slot}.html"
        result = template.replace("__PACKET__", payload)
        assert not re.search(r"[\u3400-\u9fff]", result), (
            "Review packet metadata must be localized without changing records"
        )
        target.write_text(result, encoding="utf-8")
        manifest["sources"].append({
            "file": source.name,
            "sha256": material["source_packet_sha256"],
            "records_sha256": records_hash,
            "source_evidence_sha256": packet["source_evidence_sha256"],
            "compatible_source_packet_sha256": material["compatible_source_packet_sha256"],
        })
        manifest["outputs"].append({
            "file": target.name, "sha256": digest(target.read_bytes()), "records": 100
        })
        assert source.read_bytes() == raw
    usage = (WORK / "README.txt").read_text(encoding="utf-8")
    (DEST / "README.txt").write_text(usage, encoding="utf-8")
    archive = SOURCE / "human_review_materials.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for slot in (1, 2):
            p = DEST / f"reviewer_{slot}.html"
            z.write(p, p.name)
        z.write(DEST / "README.txt", "README.txt")
    (WORK / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "reviewers": 2, "records_each": 100,
        "output": str(DEST), "archive": str(archive),
    }))


if __name__ == "__main__":
    main()
