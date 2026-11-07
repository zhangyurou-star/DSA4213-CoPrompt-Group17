#!/bin/zsh
set -u
COPROMPT_STUDY_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$COPROMPT_STUDY_DIR/../.." || exit 1
print 'The 120-case experiment is complete. Replaying saved evidence offline; no API key is needed.'
python3 -B handoff/verify_handoff.py
COPROMPT_CHECK_STATUS=$?
read '?Press Enter to close.'
exit $COPROMPT_CHECK_STATUS
