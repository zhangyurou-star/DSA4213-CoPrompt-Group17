from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from logic import (
    DOMAIN_LABELS,
    FIELD_LABELS,
    OMISSION_LABELS,
    POLICY_LABELS,
    field_label,
    output_text,
    sandbox_comparison,
    value_score,
)

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "demo_data.json"
DATA_FINGERPRINT = hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()[:12]
DEMO_VERSION = "2026-10-27-en-ui5.1-fixed-r4"

CURATED_STORIES = {
    "NTSP13": {
        "label": "Successful case · Clarification repairs a date constraint",
        "tone": "success",
        "summary": "After asking for the deadline, value-based improves from 0.75 to 1.00; the date window and every other hard constraint pass.",
        "lesson": "When missing information directly affects feasibility, one clarification can repair a failure.",
    },
    "NTCW13": {
        "label": "Counterexample · More questions, lower hard-constraint score",
        "tone": "danger",
        "summary": "Direct already scores 1.00; after two questions, value-based produces 92 words, violates the 50–80 word constraint, and falls to 0.50.",
        "lesson": "More information does not guarantee correct execution; clarification policy and generation reliability must be evaluated separately.",
    },
    "NTCW24": {
        "label": "Unavailable answers · No hard-constraint score gain",
        "tone": "neutral",
        "summary": "The user does not know the audience and declines to specify a tone. Value-based records both responses, does not ask either field again, and matches direct's hard-constraint score of 0.50 after two questions.",
        "lesson": "The extra questions produced no measured hard-constraint score gain. Both reviewers counted zero unnecessary questions; equal automatic scores do not establish equal overall usefulness.",
    },
}

st.set_page_config(page_title="CoPrompt · Clarify before acting", page_icon="◈", layout="wide")

st.markdown(
    """
<style>
:root {
  --midnight:#22332f; --navy:#29463e; --navy-2:#365d52;
  --ink:#25332f; --muted:#64736b; --slate:#68776f;
  --teal:#35695a; --teal-dark:#285347; --teal-soft:#e9f0ea;
  --sky:#b7cbbd; --mint:#b7cbbd; --mint-soft:#eef4ed;
  --amber:#956e4e; --amber-soft:#f4eee5;
  --red:#a84f4b; --red-soft:#f9eeee;
  --line:#d8dfd7; --line-strong:#b9c7bc; --surface:#fffefa; --canvas:#f7f6f2;
}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
::selection{background:#c9d9cb;color:var(--ink)}
[data-testid="stAppViewContainer"]{color:var(--ink);background:var(--canvas)}
.main .block-container{max-width:1300px;padding-top:1.35rem;padding-bottom:3.1rem}
[data-testid="stSidebar"]{background:#243b35;border-right:1px solid #36534a}
[data-testid="stSidebar"] *{color:#eff3ed}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.12rem}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:.58rem .7rem;border-radius:6px;transition:background .15s ease}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.07)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:rgba(218,232,217,.14);box-shadow:inset 3px 0 0 #c8dac8}
h1,h2,h3{color:var(--ink);letter-spacing:-.025em}
h1,h2{font-weight:650}h3{margin-top:.4rem;font-weight:650}
.hero{position:relative;overflow:hidden;padding:1.8rem 2.05rem;border-radius:12px;background:#e9efe9;color:var(--ink);margin-bottom:1.05rem;border:1px solid #d2ddd2;border-left:4px solid var(--teal);box-shadow:0 8px 26px rgba(35,51,47,.045)}
.hero:after{content:"";position:absolute;width:280px;height:280px;right:-110px;top:-160px;border-radius:50%;border:1px solid rgba(53,105,90,.13);box-shadow:0 0 0 45px rgba(53,105,90,.025),0 0 0 90px rgba(53,105,90,.015)}
.hero h1{position:relative;color:var(--ink);margin:.2rem 0 0;font-family:Georgia,"Times New Roman",serif;font-size:2.45rem;font-weight:600;line-height:1.08}
.hero p{position:relative;color:#4d6359;margin:.7rem 0 0;max-width:870px;font-size:.98rem;line-height:1.6}
.cover-shell{position:relative;overflow:hidden;min-height:500px;padding:3.4rem 3.7rem 2.9rem;border-radius:14px;background:#f0f0e8;color:var(--ink);border:1px solid #d6d9cf;box-shadow:0 18px 50px rgba(35,51,47,.09);margin:1rem 0 1.1rem}
.cover-shell:before{content:"";position:absolute;width:380px;height:380px;right:-130px;top:-150px;border-radius:50%;border:1px solid rgba(53,105,90,.13);box-shadow:0 0 0 58px rgba(53,105,90,.023),0 0 0 115px rgba(53,105,90,.015)}
.cover-shell:after{content:"";position:absolute;width:36%;height:1px;right:3.1rem;bottom:3rem;background:linear-gradient(90deg,transparent,#b2c9b5)}
.cover-topline{position:relative;display:flex;justify-content:space-between;gap:1rem;align-items:center;color:#5f7568;font-size:.69rem;font-weight:750;letter-spacing:.17em;text-transform:uppercase}
.cover-brand{color:#35695a}
.cover-title{position:relative;color:#21352f;margin:3.55rem 0 .3rem;font-family:Georgia,"Times New Roman",serif;font-size:clamp(4rem,7.3vw,7rem);font-weight:600;line-height:.94;letter-spacing:-.06em}
.cover-title:after{content:"";display:block;width:4.1rem;height:3px;margin-top:1.2rem;background:var(--teal)}
.cover-deck{position:relative;color:#263d34;margin:1.05rem 0 0;max-width:850px;font-size:clamp(1.24rem,2.1vw,1.84rem);line-height:1.24;letter-spacing:-.025em;font-weight:560}
.cover-subtitle{position:relative;color:#596e60;margin:1rem 0 2rem;max-width:770px;font-size:.97rem;line-height:1.65}
.cover-flow{position:relative;display:grid;grid-template-columns:1fr auto 1fr auto 1.2fr auto 1fr;gap:.5rem;align-items:center;max-width:940px}
.cover-node{padding:.78rem .84rem;border:1px solid #d0d9cd;border-radius:6px;background:rgba(255,254,250,.74)}
.cover-node b{display:block;color:#29443a;font-size:.79rem;letter-spacing:.09em;font-weight:790}
.cover-node span{display:block;margin-top:.24rem;color:#64776a;font-size:.7rem}
.cover-node.decision{border-color:#8eaf9b;background:#e2eee3;box-shadow:inset 0 2px 0 #6a9478}
.cover-arrow{color:#57806a;font-weight:750}
.cover-meta{position:relative;display:flex;flex-wrap:wrap;gap:.5rem;margin-top:2.05rem}
.cover-chip{display:inline-flex;padding:.38rem .62rem;border-radius:4px;color:#365044;background:#e4ebe1;border:1px solid #d2ddcf;font-size:.72rem;font-weight:730;letter-spacing:.01em}
.cover-question{margin:.45rem 0 1.2rem;padding:1.05rem 1.25rem;border:1px solid var(--line);border-left:3px solid var(--teal);border-radius:7px;background:#fffefa;color:#3c5145;font-size:.93rem;box-shadow:0 7px 22px rgba(35,51,47,.04)}
.cover-question b{color:var(--ink)}.cover-actions{color:var(--muted);font-size:.8rem;margin:.2rem 0 .8rem;line-height:1.5}
.eyebrow{position:relative;text-transform:uppercase;letter-spacing:.18em;font-weight:800;font-size:.68rem;color:var(--teal-dark)}
.badge{display:inline-block;padding:.27rem .58rem;border-radius:4px;background:var(--teal-soft);color:var(--teal-dark);border:1px solid #d1dfd4;font-size:.74rem;font-weight:750;margin:0 .3rem .3rem 0}
.card{padding:1.08rem 1.16rem;background:#fffefa;border:1px solid var(--line);border-radius:8px;box-shadow:0 7px 22px rgba(35,51,47,.035);min-height:100px}
.callout{border-left:3px solid var(--teal);background:var(--teal-soft);padding:.95rem 1.05rem;border-radius:6px;color:#2d4d3f}
.success{border-left-color:#638a6e;background:var(--mint-soft)}.warning{border-left-color:var(--amber);background:var(--amber-soft)}.danger{border-left-color:var(--red);background:var(--red-soft)}.neutral{border-left-color:var(--slate);background:#f0f2ed}
.step-row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.34rem;margin:.3rem 0 1rem}
.step-pill{padding:.5rem .55rem;border-radius:5px;background:#eaede7;color:#6d7b70;border:1px solid transparent;text-align:center;font-size:.79rem;font-weight:750}
.step-pill.done{background:#e3ede2;color:var(--teal-dark);border-color:#cfdece}.step-pill.active{background:var(--navy);color:#fff;box-shadow:0 5px 14px rgba(35,51,47,.13)}
.stage-heading{display:flex;align-items:center;gap:.72rem;margin:.45rem 0 .85rem;padding:.67rem .82rem;background:#fffefa;border:1px solid var(--line);border-radius:7px}
.stage-heading strong{color:var(--ink)}.stage-heading span{color:var(--teal-dark);font-weight:820;font-size:.68rem;letter-spacing:.14em}
.flow-kicker{color:var(--teal-dark);font-size:.68rem;font-weight:820;letter-spacing:.15em;text-transform:uppercase;margin-bottom:.22rem}
.evidence-strip{padding:.6rem .82rem;border:1px solid var(--line);border-left:3px solid #9dbba3;background:#fffefa;border-radius:6px;color:#607167;font-size:.77rem;margin-bottom:1rem}
.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.85rem}.small{color:var(--muted);font-size:.85rem}.ask{color:var(--teal-dark);font-weight:820}.act{color:var(--amber);font-weight:820}
[data-testid="stMetric"]{background:#fffefa;border:1px solid var(--line);border-left:3px solid var(--teal);padding:.82rem .92rem;border-radius:8px;box-shadow:0 6px 18px rgba(35,51,47,.035)}
[data-testid="stMetricLabel"]{color:var(--muted)}[data-testid="stMetricLabel"] p{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
[data-testid="stMetricValue"]{color:var(--ink);letter-spacing:-.035em;white-space:normal!important;overflow:visible!important;text-overflow:clip!important;font-size:clamp(1.25rem,2.1vw,2.2rem)}
[data-testid="stMetricValue"]>div{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
.st-key-replay_metrics [data-testid="stMetricValue"]{font-size:1.25rem!important}
[data-testid="stButton"] button{border-radius:7px;border-color:var(--line-strong);font-weight:700;min-height:2.65rem;box-shadow:none;transition:transform .15s ease,border-color .15s ease,background .15s ease}
[data-testid="stButton"] button:hover{border-color:var(--teal);color:var(--teal-dark);transform:translateY(-1px)}
[data-testid="stButton"] button:focus-visible{outline:3px solid rgba(99,138,110,.38);outline-offset:2px}
[data-testid="stButton"] button[kind="primary"]{background:var(--navy);border-color:var(--navy);color:#fff;box-shadow:0 6px 18px rgba(35,51,47,.12)}
[data-testid="stButton"] button[kind="primary"]:hover{background:var(--navy-2);border-color:var(--navy-2);color:#fff}
[data-testid="stSidebar"] [data-testid="stButton"] button{background:#eff3ed;border-color:#b9c7bc}
[data-testid="stSidebar"] [data-testid="stButton"] button *{color:#25332f}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:7px;background:#fffefa}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:7px;overflow:hidden}
div[data-testid="stVerticalBlockBorderWrapper"]{background:#fffefa;border-color:var(--line);border-radius:8px;box-shadow:0 6px 18px rgba(35,51,47,.03)}
hr{border-color:var(--line)}#MainMenu,footer{visibility:hidden}[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{visibility:visible}
[data-testid="stExpandSidebarButton"]{visibility:visible!important;opacity:1!important;z-index:999999;margin:.55rem 0 0 .55rem;border-radius:8px;background:var(--navy);border:1px solid rgba(255,255,255,.15);box-shadow:0 7px 18px rgba(35,51,47,.18)}
[data-testid="stExpandSidebarButton"] button{visibility:visible!important;color:#fff!important;border-radius:8px;min-width:2.5rem;min-height:2.5rem}
[data-testid="stExpandSidebarButton"] svg{color:#fff!important;fill:#fff!important}[data-testid="stExpandSidebarButton"]:hover{background:var(--teal-dark)}
.results-table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
.results-table{width:100%;min-width:640px;border-collapse:collapse;font-size:.88rem;line-height:1.4}
.results-table th{text-align:left;padding:.75rem .9rem;background:#edf1eb;color:#4b6556;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;white-space:nowrap}
.results-table td{padding:.8rem .9rem;border-top:1px solid var(--line);color:var(--ink);font-variant-numeric:tabular-nums}
.results-table th:first-child,.results-table td:first-child{width:38%;font-weight:680}
.results-table tbody tr:nth-child(even){background:#fbfcf9}
.quality-chart{margin:1rem 0 .25rem;padding:1.2rem 1.35rem 1rem;background:var(--surface);border:1px solid var(--line);border-radius:8px}
.quality-chart-title{display:flex;justify-content:space-between;gap:1rem;align-items:baseline;margin-bottom:.95rem;color:var(--ink);font-weight:750;font-size:.9rem}
.quality-chart-title span{color:var(--muted);font-weight:500;font-size:.76rem}
.quality-row{display:grid;grid-template-columns:minmax(180px,240px) minmax(0,1fr) 4.4rem;gap:1rem;align-items:center;margin:.78rem 0}
.quality-label{color:var(--ink);font-size:.86rem;font-weight:620;line-height:1.3}
.quality-track{height:18px;background:#e7ece5;border-radius:4px;overflow:hidden}
.quality-fill{height:100%;background:#54816d;border-radius:4px}
.quality-row:last-of-type .quality-fill{background:#315f4e}
.quality-value{text-align:right;color:var(--ink);font-size:.86rem;font-weight:750;font-variant-numeric:tabular-nums}
.quality-axis{display:grid;grid-template-columns:repeat(3,1fr);margin-left:calc(240px + 1rem);margin-right:calc(4.4rem + 1rem);color:var(--muted);font-size:.7rem;font-variant-numeric:tabular-nums}
.quality-axis span:nth-child(2){text-align:center}.quality-axis span:last-child{text-align:right}
@media(max-width:650px){.quality-row{grid-template-columns:minmax(0,1fr) 4rem;gap:.45rem}.quality-label{grid-column:1/-1}.quality-track{grid-column:1}.quality-value{grid-column:2}.quality-axis{margin-left:0;margin-right:calc(4rem + .45rem)}}
@media(max-width:900px){.step-row{grid-template-columns:1fr 1fr}.hero h1{font-size:2rem}.main .block-container{padding-left:1rem;padding-right:1rem}.cover-shell{padding:2.5rem 1.5rem 2rem;min-height:unset}.cover-title{margin-top:2.6rem}.cover-topline{align-items:flex-start;flex-direction:column}.cover-flow{grid-template-columns:1fr}.cover-arrow{transform:rotate(90deg);text-align:center}.cover-shell:after{display:none}}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def hero(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<section class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></section>',
        unsafe_allow_html=True,
    )


def pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def cover_page(data: dict[str, Any]) -> None:
    meta = data["metadata"]
    st.markdown(
        f"""
        <section class="cover-shell">
          <div class="cover-topline">
            <span class="cover-brand">Group 17 · DSA4213</span>
            <span>Semester 1 · AY 2026/2027</span>
          </div>
          <div class="cover-title" role="heading" aria-level="1">CoPrompt</div>
          <div class="cover-deck">When should an agent clarify—and when should it act?</div>
          <p class="cover-subtitle">Adaptive clarification for task completion under a limited interaction budget. The controller weighs the importance and uncertainty of missing information before choosing ASK or ACT.</p>
          <div class="cover-flow">
            <div class="cover-node"><b>REQUEST</b><span>Incomplete user goal</span></div>
            <div class="cover-arrow">→</div>
            <div class="cover-node"><b>OBSERVE</b><span>Visible field state</span></div>
            <div class="cover-arrow">→</div>
            <div class="cover-node decision"><b>ASK / ACT</b><span>V(f) = I(f)U(f) − λ</span></div>
            <div class="cover-arrow">→</div>
            <div class="cover-node"><b>EVIDENCE</b><span>Quality + questions</span></div>
          </div>
          <div class="cover-meta">
            <span class="cover-chip">{meta['dataset_cases']['total']} reviewed cases</span>
            <span class="cover-chip">{meta['completed_trajectories']['total']} recorded trajectories</span>
            <span class="cover-chip">λ = {meta['selected_lambda']}</span>
            <span class="cover-chip">0 live API calls</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="cover-question"><b>Research question</b> · Can importance × uncertainty improve the quality–question trade-off over direct, exhaustive, and prompt-only clarification policies?</div>',
        unsafe_allow_html=True,
    )
    primary, secondary, note = st.columns([1.25, 1, 1.55])
    if primary.button("Start the 90-second demo →", type="primary", use_container_width=True, key="cover_start"):
        st.session_state.cover_entered = True
        st.session_state.nav_page = "Presenter mode"
        st.session_state.presenter_step = 0
        st.rerun()
    if secondary.button("Explore the results", use_container_width=True, key="cover_results"):
        st.session_state.cover_entered = True
        st.session_state.nav_page = "Experiment overview"
        st.rerun()
    note.markdown('<div class="cover-actions">Recorded Fresh-120 replay<br>No model call or new experiment is triggered.</div>', unsafe_allow_html=True)


def case_by_id(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    return next(case for case in data["cases"] if case["case_id"] == case_id)


def evidence_strip(data: dict[str, Any], case_id: str | None = None) -> None:
    meta = data["metadata"]
    case_text = f" · case {case_id}" if case_id else ""
    st.markdown(
        f'<div class="evidence-strip">Recorded replay · demo {DEMO_VERSION} · data {html.escape(str(meta.get("created_utc", "—"))[:10])}'
        f' · SHA-256 {DATA_FINGERPRINT}{case_text} · λ={meta.get("selected_lambda", "—")} · no new sampling</div>',
        unsafe_allow_html=True,
    )


def field_ids(case: dict[str, Any]) -> list[str]:
    if case["domain"] == "constrained_writing":
        return ["audience", "tone", "length", "required_content"]
    return ["deadline", "available_time", "topics", "priorities"]


def render_field_state(case: dict[str, Any], compact: bool = False) -> None:
    known = case.get("extracted_field_values") or {}
    columns = st.columns(2) if compact else None
    for index, fid in enumerate(field_ids(case)):
        value = known.get(fid)
        target = columns[index % 2] if columns else st
        if value:
            target.success(f"{field_label(fid)} · Resolved", icon="✅")
        else:
            target.warning(f"{field_label(fid)} · Unresolved", icon="❔")


def outcome_for(case: dict[str, Any], policy: str) -> tuple[str, str, str]:
    record = case["policies"][policy]
    direct = case["policies"].get("direct", {})
    quality = (record.get("score") or {}).get("quality")
    direct_quality = (direct.get("score") or {}).get("quality")
    question_delta = record.get("question_items", 0) - direct.get("question_items", 0)
    if quality is not None and direct_quality is not None and quality > direct_quality:
        return "Higher score", "success", f"The saved hard-constraint score is {quality - direct_quality:+.2f} versus direct."
    if quality is not None and direct_quality is not None and quality < direct_quality:
        return "Lower score", "danger", f"The saved hard-constraint score is {quality - direct_quality:+.2f} versus direct."
    if question_delta > 0:
        return "Equal score", "neutral", f"The hard-constraint score matches direct with {question_delta} additional question(s). Equal automatic scores do not establish equal overall usefulness."
    return "Equal score", "neutral", "The saved hard-constraint score and question count match direct. This does not establish equivalent outputs."

def policy_table(case: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for policy, item in case["policies"].items():
        score = item.get("score") or {}
        outcome, _, _ = outcome_for(case, policy)
        rows.append({
            "Policy": POLICY_LABELS.get(policy, policy),
            "Hard-constraint": score.get("quality"),
            "Questions": item.get("question_items", 0),
            "Score vs direct": outcome,
            "Format failure": "Yes" if score.get("format_failure") else "No",
            "Cache reuse": "Yes" if item.get("generation_cache_hit") else "No",
        })
    return pd.DataFrame(rows).sort_values("Policy")


def render_output(output: Any) -> None:
    text = output_text(output)
    if text:
        st.markdown(text)
        return
    if not isinstance(output, dict):
        st.write(output)
        return
    schedule = output.get("schedule") or output.get("sessions") or output.get("plan")
    if isinstance(schedule, list) and schedule:
        st.dataframe(pd.DataFrame(schedule), width="stretch", hide_index=True)
    summary = output.get("summary")
    if summary:
        st.markdown("**Plan summary**")
        if isinstance(summary, (dict, list)):
            st.json(summary, expanded=False)
        else:
            st.write(str(summary))
    remaining = {key: value for key, value in output.items() if key not in {"schedule", "sessions", "plan", "summary"}}
    if remaining:
        st.json(remaining, expanded=False)


def render_decision(decision: dict[str, Any], index: int, policy: str) -> None:
    action = decision.get("action", "—")
    field_id = decision.get("field_id")
    title = f"Step {decision.get('step', index + 1)} · {action}"
    if field_id:
        title += f" · {field_label(field_id)}"
    with st.expander(title, expanded=index == 0):
        if decision.get("stop_reason"):
            st.caption(f"Stop reason: {decision['stop_reason']}")
        if decision.get("eligible_fields"):
            st.write("Eligible fields:", ", ".join(field_label(x) for x in decision["eligible_fields"]))
        ratings = decision.get("ratings") or []
        if ratings:
            rows = []
            values = decision.get("values") or {}
            effective_importance = decision.get("effective_importance") or {}
            diagnostic = policy == "importance_one"
            for rating in ratings:
                fid = rating["field_id"]
                importance = (
                    {"Raw I": rating.get("importance"), "Effective I": effective_importance.get(fid)}
                    if diagnostic else {"I": rating.get("importance")}
                )
                rows.append({
                    "Field": field_label(fid), **importance,
                    "U": rating.get("uncertainty"), "I×U−λ": values.get(fid),
                    "Short rationale": rating.get("reason", ""),
                })
            if diagnostic:
                st.caption("Importance=1 diagnostic: Effective I is fixed at 1. Saved I×U−λ values use Effective I; Raw I is the original saved rating.")
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.caption(
            f'Question budget: {decision.get("budget_before", "—")} → '
            f'{decision.get("budget_after", "—")} · λ={decision.get("lambda_value", "—")}'
        )


def presenter_mode(data: dict[str, Any]) -> None:
    hero("PRESENTER MODE · 60–90 SECONDS", "How does CoPrompt decide whether to ask or act?", "Walk through one frozen, recorded trajectory to explain the controller, runner, outcome, and limitations—without a model call or a new experiment.")
    evidence_strip(data)
    st.markdown('<div class="callout"><b>Research question</b><br>When a request is incomplete, can adaptive clarification improve hard-constraint satisfaction while controlling interaction burden?</div>', unsafe_allow_html=True)

    story_ids = list(CURATED_STORIES)
    case_id = st.selectbox("Choose a presentation story", story_ids, format_func=lambda x: CURATED_STORIES[x]["label"], key="presenter_case")
    if st.session_state.get("presenter_last_case") != case_id:
        st.session_state.presenter_last_case = case_id
        st.session_state.presenter_step = 0
    step = int(st.session_state.get("presenter_step", 0))
    case = case_by_id(data, case_id)
    record = case["policies"]["value_based"]
    story = CURATED_STORIES[case_id]
    labels = ["1 Request", "2 Observe", "3 ASK", "4 ACT", "5 Evidence"]
    pills = []
    for index, label in enumerate(labels):
        state = "active" if index == step else "done" if index < step else ""
        pills.append(f'<span class="step-pill {state}">{label}</span>')
    st.markdown(f'<div class="step-row">{"".join(pills)}</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="badge">{case_id}</span><span class="badge">Value-based</span><span class="badge">λ={data["metadata"]["selected_lambda"]}</span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="stage-heading"><span>STEP {step + 1:02d}</span><strong>{labels[step].split(" ", 1)[1]}</strong><div class="small">{story["label"]}</div></div>',
        unsafe_allow_html=True,
    )

    if step == 0:
        st.markdown("### What did the user provide?")
        st.markdown(f'<div class="card">{html.escape(case["initial_request"])}</div>', unsafe_allow_html=True)
        st.caption("Before revealing the answer, identify what is explicit and what may affect execution.")
    elif step == 1:
        st.markdown("### What does the controller observe?")
        render_field_state(case, compact=True)
        st.caption("Green fields were resolved from the initial request; yellow fields enter the clarification candidate set.")
    elif step == 2:
        st.markdown("### The controller chooses ASK")
        ask_decisions = [item for item in record.get("decisions", []) if item.get("action") == "ASK"]
        exchanges = record.get("visible_exchanges") or []
        for index, decision in enumerate(ask_decisions):
            fid = decision.get("field_id")
            rating = next((item for item in decision.get("ratings", []) if item.get("field_id") == fid), {})
            net_value = (decision.get("values") or {}).get(fid, "—")
            with st.container(border=True):
                st.markdown(f'**ASK {index + 1} · {field_label(fid)}**')
                st.markdown(
                    f'I={rating.get("importance", "—")} · U={rating.get("uncertainty", "—")} · '
                    f'I×U−λ={net_value} · budget {decision.get("budget_before", "—")}→{decision.get("budget_after", "—")}'
                )
                if rating.get("reason"):
                    st.caption(rating["reason"])
                if index < len(exchanges):
                    exchange = exchanges[index]
                    status = exchange.get("status", "available")
                    st.markdown(f'**Q. {html.escape(str(exchange.get("question", "")))}**')
                    st.info(f'{exchange.get("answer_text", "—")}  ·  status={status}')
    elif step == 3:
        st.markdown("### The runner executes ACT")
        score = record.get("score") or {}
        a, b, c = st.columns(3)
        a.metric("Hard-constraint", pct(score.get("quality")))
        b.metric("Questions", record.get("question_items", 0))
        c.metric("Final action", "ACT")
        with st.container(border=True):
            render_output(record.get("output"))
    else:
        st.markdown("### Evidence and error analysis")
        st.markdown(f'<div class="callout {story["tone"]}"><b>{story["label"]}</b><br>{story["summary"]}<br><br><b>Interpretation:</b>{story["lesson"]}</div>', unsafe_allow_html=True)
        st.dataframe(policy_table(case), width="stretch", hide_index=True,
                     column_config={"Hard-constraint": st.column_config.NumberColumn(format="%.2f")})
        failed = [item for item in (record.get("score") or {}).get("constraint_results", []) if not item.get("passed")]
        if failed:
            messages = []
            for item in failed:
                if item["check_type"] == "word_count":
                    details = item["details"]
                    messages.append(
                        f'Saved experimental output failed the word-count check: '
                        f'{details["word_count"]} words; required '
                        f'{details["min_words"]}–{details["max_words"]} words.'
                    )
                else:
                    messages.append(f'Saved experimental output failed {item["check_type"]} ({item["constraint_id"]}).')
            st.error(" ".join(messages) + " This is a recorded experiment result, not a demo error.")
        st.caption("This is one representative record, not a population-level causal result. Overall conclusions must come from the 60-case test set and paired comparisons.")

    back, position, forward = st.columns([1, 2, 1])
    if back.button("← Back", disabled=step == 0, use_container_width=True):
        st.session_state.presenter_step = step - 1
        st.rerun()
    position.markdown(f'<p style="text-align:center;color:#5d6a7b">Step {step + 1} / {len(labels)}</p>', unsafe_allow_html=True)
    next_label = "Replay" if step == len(labels) - 1 else "Next →"
    if forward.button(next_label, use_container_width=True):
        st.session_state.presenter_step = 0 if step == len(labels) - 1 else step + 1
        st.rerun()

def overview(data: dict[str, Any]) -> None:
    hero("FRESH-120 · OFFLINE EVIDENCE", "Clarify before acting", "Interaction burden and hard-constraint satisfaction across four clarification policies. All figures come from the completed 60-case test set.")
    evidence_strip(data)
    meta = data["metadata"]
    a, b, c, d = st.columns(4)
    a.metric("New cases", meta["dataset_cases"]["total"], "40 / 20 / 60")
    b.metric("Logical trajectories", meta["completed_trajectories"]["total"])
    c.metric("Validation-selected λ", meta["selected_lambda"])
    d.metric("Fresh-study cost", f"US${meta['costs']['fresh_accounted_usd']:.4f}")
    st.markdown("### Main test results")
    stats = data["statistics"]
    table_rows = []
    chart_rows = []
    for policy, record in stats.items():
        label = html.escape(POLICY_LABELS[policy])
        quality = float(record["mean_quality"])
        questions = float(record["mean_questions"])
        table_rows.append(
            f"<tr><td>{label}</td><td>{quality:.3f}</td><td>{questions:.2f}</td>"
            f"<td>{int(record['full_pass'])}/{int(record['n'])}</td></tr>"
        )
        chart_rows.append(
            f'<div class="quality-row"><span class="quality-label">{label}</span>'
            f'<div class="quality-track" aria-hidden="true"><div class="quality-fill" style="width:{quality * 100:.1f}%"></div></div>'
            f'<span class="quality-value">{quality * 100:.1f}%</span></div>'
        )
    st.markdown(
        '<div class="results-table-wrap"><table class="results-table">'
        '<thead><tr><th>Policy</th><th>Hard-constraint</th><th>Mean questions</th><th>Full pass</th></tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="quality-chart"><div class="quality-chart-title">Hard-constraint satisfaction'
        '<span>Mean over 60 test cases</span></div>'
        f'{"".join(chart_rows)}'
        '<div class="quality-axis"><span>0%</span><span>50%</span><span>100%</span></div></div>',
        unsafe_allow_html=True,
    )
    st.caption("The automatic score covers predefined hard constraints only; it does not measure overall usability.")
    st.markdown("### Paired comparisons for value-based")
    comparisons = []
    for item in data["paired_comparisons"]:
        comparisons.append({
            "Comparator": POLICY_LABELS[item["right"]],
            "Quality difference": f"{item['quality_difference']:+.4f}",
            "Quality 95% interval": f"[{item['quality_95pct_interval'][0]:.4f}, {item['quality_95pct_interval'][1]:.4f}]",
            "Question difference": f"{item['question_difference']:+.3f}",
        })
    st.dataframe(pd.DataFrame(comparisons), width="stretch", hide_index=True)
    st.markdown('<div class="callout warning"><b>Key finding</b><br>Value-based improves hard-constraint satisfaction over direct, but the evidence does not show an advantage over exhaustive or prompt-only. In the recorded run, λ=0.25 filters out no candidate questions, so value-based asks exactly as many questions as exhaustive.</div>', unsafe_allow_html=True)


def retain_replay_policy() -> None:
    if st.session_state.replay_policy is None:
        st.session_state.replay_policy = st.session_state.replay_previous_policy


def replay(data: dict[str, Any]) -> None:
    hero("RECORDED REPLAY", "Case replay", "Follow one recorded trajectory from input through controller decisions to output evidence. This page makes no model calls.")
    st.caption("Choose a case and policy. The layout follows the system flow: Input → Control → Output.")
    c1, c2, c3 = st.columns([1, 1, 1.2])
    domain = c1.selectbox("Task domain", list(DOMAIN_LABELS), format_func=lambda x: DOMAIN_LABELS[x], key="replay_domain")
    domain_cases = [x for x in data["cases"] if x["domain"] == domain]
    omission = c2.selectbox("Information condition", sorted({x["omission_type"] for x in domain_cases}), format_func=lambda x: OMISSION_LABELS[x], key="replay_condition")
    filtered = [x for x in domain_cases if x["omission_type"] == omission]
    case = c3.selectbox("Replay case", filtered, format_func=lambda x: f"{x['case_id']} · {x['title']}", key="replay_case")
    policies = list(case["policies"])
    if st.session_state.get("replay_policy") not in policies:
        st.session_state.replay_policy = "value_based" if "value_based" in policies else policies[0]
    st.session_state.replay_previous_policy = st.session_state.replay_policy
    policy = st.segmented_control(
        "Policy", policies, key="replay_policy",
        format_func=lambda x: POLICY_LABELS.get(x, x), on_change=retain_replay_policy,
    )
    record = case["policies"][policy]
    score = record.get("score") or {}
    decisions = record.get("decisions") or []
    exchanges = record.get("visible_exchanges") or []
    constraints = score.get("constraint_results") or []

    st.markdown(
        f'<span class="badge">{case["case_id"]}</span><span class="badge">{DOMAIN_LABELS[domain]}</span>'
        f'<span class="badge">{OMISSION_LABELS[omission]}</span>', unsafe_allow_html=True,
    )
    evidence_strip(data, case["case_id"])
    outcome, outcome_tone, outcome_detail = outcome_for(case, policy)
    st.markdown(f'<div class="callout {outcome_tone}"><b>{outcome}</b><br>{outcome_detail}</div>', unsafe_allow_html=True)

    input_col, control_col, output_col = st.columns([1, 1.12, 1.18], gap="large")
    with input_col:
        st.markdown('<div class="flow-kicker">1 · Input</div>', unsafe_allow_html=True)
        st.markdown("### Request & context")
        st.markdown(f'<div class="card">{html.escape(case["initial_request"])}</div>', unsafe_allow_html=True)
        st.caption(f"Reference date: {case.get('reference_date')} · User control: {case.get('user_control')}")
        st.markdown("#### Visible field state")
        render_field_state(case)

    with control_col:
        st.markdown('<div class="flow-kicker">2 · Control</div>', unsafe_allow_html=True)
        st.markdown("### ASK / ACT trace")
        for idx, decision in enumerate(decisions):
            render_decision(decision, idx, policy)
        if not decisions:
            st.info("This record has no decision step.")
        if exchanges:
            st.markdown("#### Visible interaction")
            for idx, exchange in enumerate(exchanges, 1):
                question = exchange.get("question") or exchange.get("question_text") or exchange.get("field_id", "Question")
                answer = exchange.get("answer") or exchange.get("answer_text") or exchange.get("response")
                st.markdown(f"**Q{idx}. {question}**")
                st.info(str(answer) if answer is not None else "No answer recorded")

    with output_col:
        st.markdown('<div class="flow-kicker">3 · Output</div>', unsafe_allow_html=True)
        st.markdown("### Result & evidence")
        with st.container(key="replay_metrics"):
            m1, m2 = st.columns(2)
            m1.metric("Hard-constraint", pct(score.get("quality")))
            m2.metric("Questions", record.get("question_items", 0))
        st.caption(f"Generation cache: {'hit' if record.get('generation_cache_hit') else 'miss'}")
        with st.container(border=True):
            render_output(record.get("output"))
        if constraints:
            with st.expander("Automatic constraint checks"):
                rows = [{"Constraint": x.get("constraint_id"), "Type": x.get("check_type"), "Passed": x.get("passed"),
                         "Details": json.dumps(x.get("details"), ensure_ascii=False)} for x in constraints]
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("### Cross-policy comparison")
    st.dataframe(
        policy_table(case), width="stretch", hide_index=True,
        column_config={"Hard-constraint": st.column_config.NumberColumn(format="%.2f")},
    )

def sandbox(data: dict[str, Any]) -> None:
    hero("NO-LLM POLICY LAB", "Policy sandbox", "Change field status, importance, and uncertainty to illustrate four policies at the frozen threshold and three-question cap.")
    st.markdown('<div class="callout"><b>Explanatory simulation</b><br>Value-based uses the formal I×U−λ rule with the strict >0 trigger. For clarity, this page does not call the model again after an answer. Prompt-only is simulated through your field selections.</div>', unsafe_allow_html=True)
    top1, top2, top3 = st.columns(3)
    domain = top1.selectbox("Domain", list(DOMAIN_LABELS), format_func=lambda x: DOMAIN_LABELS[x], key="sandbox_domain")
    lambda_value = top2.select_slider("λ (frozen)", options=[0.0, 0.25, 0.5], value=data["metadata"]["selected_lambda"], disabled=True)
    budget = top3.slider("Maximum questions (fixed)", min_value=1, max_value=3, value=3, disabled=True)
    fields = ["audience", "tone", "length", "required_content"] if domain == "constrained_writing" else ["deadline", "available_time", "topics", "priorities"]
    st.caption("Unavailable covers unknown or declined answers. Provided and unavailable fields are excluded from questioning.")
    st.markdown("### Configure fields")
    configured = []
    for index, fid in enumerate(fields):
        with st.container(border=True):
            st.markdown(f"**{field_label(fid)}**")
            a, b, c, d = st.columns([1.1, 1, 1, 1.1])
            status = a.selectbox("Status", ["missing", "provided", "unavailable"],
                                 format_func=lambda x: {"missing": "Missing", "provided": "Provided", "unavailable": "Unavailable"}[x],
                                 key=f"status_{domain}_{fid}", index=1 if index == 0 else 0)
            importance = b.select_slider("Importance I", options=[0.0, 0.5, 1.0], value=0.5 if index else 1.0,
                                         key=f"i_{domain}_{fid}")
            uncertainty = c.select_slider("Uncertainty U", options=[0.5, 1.0], value=1.0,
                                           key=f"u_{domain}_{fid}")
            prompt_only_ask = d.checkbox("Prompt-only asks", value=index in (1, 2), key=f"p_{domain}_{fid}")
            configured.append({"field_id": fid, "status": status, "importance": importance,
                               "uncertainty": uncertainty, "prompt_only_ask": prompt_only_ask})
    comparison = sandbox_comparison(configured, lambda_value, budget)
    st.markdown("### Policy decisions")
    cards = st.columns(4)
    for column, item in zip(cards, comparison):
        fields_text = ", ".join(field_label(x) for x in item["fields"]) or "—"
        with column:
            st.markdown(f'<div class="card"><div class="small">{POLICY_LABELS[item["policy"]]}</div><h3 class="{item["action"].lower()}">{item["action"]}</h3><b>{item["questions"]} question(s)</b><p class="small">{fields_text}</p></div>', unsafe_allow_html=True)
    st.caption("Direct asks nothing; exhaustive follows catalog order; prompt-only uses your selections above; value-based ranks fields by net value.")
    eligible = [x for x in configured if x["status"] == "missing"]
    if eligible:
        value_rows = []
        for row in eligible:
            value_rows.append({"Field": field_label(row["field_id"]), "I": row["importance"], "U": row["uncertainty"],
                               "I×U": row["importance"] * row["uncertainty"],
                               "I×U−λ": value_score(row["importance"], row["uncertainty"], lambda_value),
                               "Triggered": value_score(row["importance"], row["uncertainty"], lambda_value) > 0})
        st.dataframe(pd.DataFrame(value_rows), width="stretch", hide_index=True)
    if lambda_value == 0.25 and eligible and all(row["importance"] * row["uncertainty"] >= 0.5 for row in eligible):
        st.warning("This reproduces the structure observed in the formal experiment: every candidate has I×U≥0.5, so λ=0.25 filters out nothing and value-based approaches exhaustive.")


def boundaries(_: dict[str, Any]) -> None:
    hero("EVIDENCE BOUNDARY", "What can the evidence support?", "Completed experiment records, returned assessments, and the limits of the evidence.")
    review = json.loads((ROOT / "data" / "human_review_summary.json").read_text(encoding="utf-8"))
    left, right = st.columns(2)
    with left:
        st.markdown("### Completed")
        for item in [
            "120 new cases with frozen data, protocol, and code fingerprints",
            "40 design / 20 validation / 60 test",
            "240 test trajectories across four main policies",
            "20-case importance diagnostic",
            "Paired bootstrap, cost, and cache analyses",
            "Two returned reviewer assessments per output: 100 outputs, 200 assessments",
            "Agreement statistics computed on the 100 paired outputs",
        ]:
            st.success(item, icon="✅")
    with right:
        st.markdown("### Review limitations")
        for item in [
            "The supplied assessments were confirmed by human reviewers. Their collection process differs from the proposal's original review plan.",
            "R2-002 reports three unnecessary questions for a Direct output with an empty clarification trace. The original count remains in the statistics.",
            "The assessment covers the preselected 20-case subset; it is descriptive and does not represent all 60 test cases.",
        ]:
            st.warning(item, icon="⚠️")
    st.markdown("### Returned assessment agreement")
    st.caption("20 preselected cases × five variants = 100 outputs, each assessed by two reviewers. Existing aggregates are shown without changing any returned rating.")
    st.dataframe(pd.DataFrame(review["rating_agreement"]), width="stretch", hide_index=True,
                 column_config={"Linear weighted κ": st.column_config.NumberColumn(format="%.4f")})
    st.dataframe(pd.DataFrame(review["count_agreement"]), width="stretch", hide_index=True)
    st.markdown("### Conclusion boundaries")
    st.markdown(
        """
- **Supported:** On this synthetic case distribution, value-based has a higher hard-constraint score than direct.
- **Not supported:** Value-based outperforms exhaustive or prompt-only; value-based saves questions; the automatic score equals overall usability.
- **Cannot be generalized to:** New model samples, other models or providers, real-user satisfaction, or general dialogue tasks.
- **Must not be done:** Reselect λ on the current test set. Any change to scoring granularity or threshold requires a new frozen follow-up experiment.
        """
    )
    st.markdown('<div class="callout warning"><b>Recorded replay and assessment limits</b><br>This demo uses saved trajectories and accepts no new requests or answers. Agreement describes the returned assessments on the preselected 20-case subset.</div>', unsafe_allow_html=True)


def main() -> None:
    data = load_data()
    if not st.session_state.get("cover_entered", False):
        cover_page(data)
        st.caption(f"CoPrompt demo {DEMO_VERSION} · Recorded evidence only · SHA-256 {DATA_FINGERPRINT} · 200 returned assessments")
        return

    pages = ["Presenter mode", "Experiment overview", "Case replay", "Policy sandbox", "Evidence boundary"]
    if st.session_state.get("nav_page") not in pages:
        st.session_state.nav_page = "Presenter mode"
    with st.sidebar:
        st.markdown("## ◈ CoPrompt")
        st.caption("Adaptive clarification before acting")
        if st.button("← Back to cover", use_container_width=True):
            st.session_state.cover_entered = False
            st.rerun()
        st.divider()
        page = st.radio("Navigation", pages, key="nav_page", label_visibility="collapsed")
        st.divider()
        projector = st.toggle("Projector mode", value=False, key="projector_mode", help="Enlarge presentation text without changing data or results.")
        st.markdown("**Offline demo**")
        st.caption("0 API calls · 0 paid inference")
        st.caption(f"Demo {DEMO_VERSION} · data {DATA_FINGERPRINT}")
    if projector:
        st.markdown(
            """<style>
            [data-testid="stMainBlockContainer"]{max-width:1540px;padding-top:.75rem}
            [data-testid="stMain"] p,[data-testid="stMain"] li,[data-testid="stMain"] label,
            [data-testid="stMain"] .card,[data-testid="stMain"] .callout,[data-testid="stMain"] .small{font-size:1.15rem;line-height:1.55}
            [data-testid="stMain"] h3{font-size:1.9rem}.hero h1{font-size:2.85rem}.hero p{font-size:1.15rem}
            .step-pill{font-size:1rem;padding:.62rem}.badge{font-size:.92rem}
            [data-testid="stMetricValue"]{font-size:clamp(1.5rem,2.5vw,2.35rem)}
            [data-testid="stMetricLabel"]{font-size:1rem}
            div[data-testid="stVerticalBlockBorderWrapper"]{border-width:2px}
            </style>""",
            unsafe_allow_html=True,
        )
    {"Presenter mode": presenter_mode, "Experiment overview": overview, "Case replay": replay, "Policy sandbox": sandbox, "Evidence boundary": boundaries}[page](data)
    st.divider()
    st.caption(f"CoPrompt demo {DEMO_VERSION} · Recorded evidence only · SHA-256 {DATA_FINGERPRINT} · 200 returned assessments")


if __name__ == "__main__":
    main()
