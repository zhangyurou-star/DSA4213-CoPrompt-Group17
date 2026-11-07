# CoPrompt Streamlit demo

UI 5.1 r4, clean runtime package. This local application replays the completed Fresh-120 v0.6.0 experiment. It makes no model calls, needs no API key, and accepts no arbitrary new requests or answers. Saved requests, replies, outputs, scores and results are unchanged.

## Run locally

Python 3.10 or later is required. The requirements pin Streamlit 1.50.0. The verified local environment used Python 3.13.15 and pandas 2.3.3.

Extract the complete folder and open a terminal in that folder. Keep the hidden `.streamlit/config.toml` file: it sets the light appearance of native tables and buttons. Run from this folder so Streamlit reads the project theme.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

After installation, `start_demo.bat` uses `.venv` when present. It changes into the demo folder automatically.

macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open the local URL printed by Streamlit. Dependency installation may need network access; replay makes no model or provider requests.

## Demonstration

1. Click **Start the 90-second demo** and follow **Request → Observe → ASK → ACT → Evidence**.
2. Use **NTSP13** for a successful deadline clarification: Value-based scores 1.00 versus Direct's 0.75 after one question.
3. Use **NTCW13** for a generation failure after clarification: the saved 92-word output violates a 50–80-word requirement, scoring 0.50 versus Direct's 1.00.
4. Use **NTCW24** for unavailable answers: unknown audience and declined tone are not asked again. Two questions yield no measured hard-constraint score gain; both reviewers counted zero unnecessary questions.
5. **Experiment overview**, **Case replay**, **Policy sandbox** and **Evidence boundary** support further explanation. Replay contains 12 selected cases and 60 case-policy records; overall results describe the full 60-case test set.

The 60–90 second duration is a suggested demo segment, not the whole group's course presentation limit. **Projector mode** enlarges presentation text. Diagnostic trace tables distinguish the saved **Raw I** from the **Effective I** used by the Importance=1 diagnostic.

Saved constraint failures remain part of the experiment. For NTCW24, the notice reads:

> Saved experimental output failed the word-count check: 110 words; required 60–90 words. This is a recorded experiment result, not a demo error.

Counts and ranges are read from the saved checks. Do not alter outputs or scores to remove an experimental failure.

## Evidence boundaries

- This package uses the proposal's saved-trajectory demonstration route. It does not run a live agent.
- Lambda remains 0.25 and the question cap is three. Only missing fields are eligible; provided and unavailable fields, including unknown or declined answers, are excluded. Value-based uses the strict I×U−lambda > 0 trigger. Public execute-now records act immediately.
- The sandbox applies the rule to a manually specified field state. Its I/U values and Prompt-only selections are explanatory inputs; it does not re-estimate I/U after an answer. The formal experimental controller reassesses after each answer.
- The automatic score covers predefined hard constraints. Equal scores do not establish equal outputs or equal overall usefulness. The recorded results do not establish an advantage over Exhaustive or Prompt-only, or question savings over Exhaustive.
- Two returned reviews cover 100 outputs on the preselected 20-case, five-variant subset: 200 assessments. Both returns document human confirmation. The assessment process differs from the proposal's original review plan.
- R2-002 retains an unnecessary-question count of three for a Direct output with an empty clarification trace. It remains in the existing statistics and is not evidence that Direct asked questions.

## Package layout

```text
app.py
logic.py
requirements.txt
start_demo.bat
README.md
PACKAGE_MANIFEST.json
.streamlit/config.toml
data/demo_data.json
data/human_review_summary.json
```

This text revision changes only the displayed assessment wording and this README. The data files, decision logic, light-theme configuration, dependencies and Windows startup helper match the r4 clean release byte-for-byte. The manifest records this packaging revision and excludes its own hash. The software footer retains the r4 base version `2026-10-27-en-ui5.1-fixed-r4`.

Historical screenshots and export tooling remain in the original r4 Support Materials package. None of these files is required to start or present the demo. The full experimental study evidence remains a separate submission artifact.
