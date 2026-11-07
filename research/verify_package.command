#!/bin/zsh
set -u
COPROMPT_PACKAGE_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$COPROMPT_PACKAGE_DIR" || exit 1
print 'Offline verification of original evidence and English presentation. No key or API needed.'
python3 -B handoff/verify_handoff.py
COPROMPT_CHECK_STATUS=$?
read '?Press Enter to close.'
exit $COPROMPT_CHECK_STATUS
