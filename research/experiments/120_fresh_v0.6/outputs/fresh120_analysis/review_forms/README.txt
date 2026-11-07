CoPrompt fresh 120-case study: human content review

FOR THE COORDINATOR

The review covers 20 preselected test cases, with five outputs per case:
100 outputs for each reviewer, or 200 assessments across two reviewers.
The full 120-case dataset is not the formal human-review sample. The
20-case diagnostic subset is not an additional independent sample.

Give reviewer_1.html to one reviewer and reviewer_2.html to the other.
Each reviewer must use only their assigned form and should not see the
other form, strategy mapping, automatic scores, or results reports.
One person completing both forms does not constitute independent
two-reviewer assessment.

The forms preserve the existing anonymous IDs and independently
randomized orders. Identical outputs have not been merged. Ratings
are initially blank. The coordinator must confirm actual blinding and
authorship/cross-review exclusion criteria truthfully.

FOR THE REVIEWER

1. Open your assigned HTML file in Safari, Chrome, or Edge. The material
   is embedded and works offline. No login or API key is required.
2. Enter your name or reviewer ID. Complete "Review instructions and
   declarations" accurately. Leave unknown declarations unconfirmed.
   The form never establishes independence or blinding automatically.
3. Read the original request, reference date, user control, actual
   exchanges and answer status, and final output. The original English
   text has not been translated or rewritten. Study plans are displayed
   as tables, with the original summaries preserved.
4. Enter four scores from 1 to 5 and two nonnegative integer counts.
   If a dimension cannot be assessed, select "Cannot assess" and
   explain why in the notes. Blank entries never become zero.
   Optional questions are not automatically unnecessary questions.
5. Select all three reading confirmations, then click "Confirm this
   item". Editing a confirmed rating or note returns that item to a
   draft and clears its reading confirmations; read and confirm again.
6. Browser autosave is attempted locally. At the end of every session,
   select "Export JSON backup" and keep the downloaded JSON file.
   Use "Import backup" when changing browsers or devices. Autosave
   depends on the browser and file location and does not replace an
   exported backup.
7. "Export ratings CSV" creates a spreadsheet-ready summary. Its formal
   rating columns contain only confirmed assessments. Drafts remain
   in the JSON backup. An absent rating and an explicit zero remain
   distinguishable.
8. "Print this item" prints the current material and assessment only.
   You can print it before entering ratings for review on paper.
   It does not print all 100 items at once.

WHAT TO RETURN

Return your latest JSON backup. You may also include the ratings CSV.
Confirmed items with any "Cannot assess" dimension are counted
separately. They require follow-up and do not count as complete on all
six rating dimensions.

The JSON retains the review-record structure, evidence fingerprint,
reviewer declarations, and confirmed ratings. Its review_form_state
also preserves drafts and reading confirmations. Do not edit source
outputs manually. The HTML form does not overwrite the source packet,
call a model, or submit anything to a server.

EXISTING BACKUPS

The English form can import a JSON backup exported by the original
interface for the same reviewer and the same source materials.
Compatibility checks require the recorded original packet hash,
the identical evidence fingerprint, every immutable record, and the
same record order. Imports from another reviewer or changed materials
are rejected. After importing, export a new backup from this form.
Browser autosave does not migrate automatically between file locations.

All assessments require a human reviewer. Preparing materials or
autosaving entries does not mean that human review has been completed.

VERIFICATION SCOPE

The forms are checked for source-material consistency and interaction
logic using a local Node.js DOM stub. That check is not a browser
rendering, native file-download, or native dialog certification.
