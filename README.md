# DSA4213 CoPrompt — Group 17

This repository contains the code and research materials for our CoPrompt group project. The completed Fresh-120 v0.6 study examines how clarification policies affect hard-constraint satisfaction and the number of questions asked. The Streamlit demo replays saved experimental results; it does not make live model calls.

## Where to start

- [Demo](demo/README.md): setup instructions and a local replay of selected cases.
- [Research artifacts](research/README.md): study design, code, data, saved trajectories, evaluation results, and reproduction instructions.
- [Experimental methods](research/experiments/120_fresh_v0.6/docs/METHODS.txt): detailed protocol and interpretation boundaries.
- [Evaluation evidence](research/submission/EVALUATION_EVIDENCE.md) and [error analysis](research/submission/ERROR_ANALYSIS.md): main results and diagnostics.

## Run the demo

Use Python 3.10 or later. From the `demo` directory on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The demo requires Streamlit 1.50.0 and pandas 2.x. See `demo/README.md` for setup on other platforms and presentation guidance.

## Verify and reproduce the research

The research package recommends Python 3.12 or 3.13. Its offline verification and reproduction tools use the Python standard library and require no API key.

From the `research` directory:

```powershell
python -B submission.py verify
```

Full offline reproduction uses `python3 -B submission.py reproduce` on macOS, Linux, or Windows Subsystem for Linux. Native Windows supports the integrity check above. See `research/README.md` for the complete commands and limitations. The integrity check was also run successfully on Windows with Python 3.14.6; full reproduction was not checked in that environment.

## Model, data, and evidence

The completed study used `qwen/qwen3-30b-a3b-instruct-2507` through OpenRouter. The recorded model route, inference settings, and experiment version are in `research/experiments/120_fresh_v0.6/config/openrouter.v0.6.formal.json`.

The study contains 120 authored cases across constrained writing and study planning: 40 design, 20 validation, and 60 test cases. Saved requests, outputs, scores, human assessments, and analysis are included under `research/`. Offline inspection and replay do not contact the model provider. Do not commit API credentials or unauthorized private data.

The research package retains historical records and duplicate evidence files so its original integrity checks remain valid. The `demo/` and `research/` guides explain which results are measured, which views are illustrative, and the limits of the conclusions.
