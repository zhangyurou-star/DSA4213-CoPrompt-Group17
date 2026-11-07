"""Offline submission entry. Delegates reproduction to the supplied v0.6 verifier."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def verify_manifest():
    manifest = json.loads((ROOT / 'SUBMISSION_MANIFEST.json').read_text(encoding='utf-8'))
    for name, digest in manifest['files'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Invalid or missing submission member: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Changed submission member: ' + name)
    return len(manifest['files'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify', help='Verify package hashes and source evidence, without model calls')
    reproduce = commands.add_parser('reproduce', help='Recompute saved scores/analysis in temporary copies and run original tests')
    reproduce.add_argument('--out', type=Path, help='Optional new directory for recomputed original analysis')
    export = commands.add_parser('export', help='Regenerate the submission diagnostics and 260-trace browser')
    export.add_argument('--out', type=Path, required=True, help='New directory; existing directories are never replaced')
    inspect = commands.add_parser('inspect', help='Print one saved request, full trajectory and final output')
    inspect.add_argument('--case', required=True)
    inspect.add_argument('--system', choices=['direct','exhaustive','prompt_only','value_based','importance_one'], default='value_based')
    args = parser.parse_args()
    count = verify_manifest()
    if args.command in ('verify', 'reproduce'):
        if args.command == 'reproduce' and sys.platform == 'win32':
            parser.error('Full historical reproduction requires macOS, Linux or WSL because the original runtime uses fcntl. Use verify for native Windows integrity checks.')
        command = [sys.executable, '-B', 'handoff/verify_handoff.py']
        if args.command == 'verify':
            command.append('--manifest-only')
        elif args.out:
            command.extend(['--export-analysis', str(args.out.resolve())])
        env = {k:v for k,v in os.environ.items() if k not in {'OPENROUTER_API_KEY','OPENAI_API_KEY'}}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['PYTHONUTF8'] = '1'
        result = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if result.returncode:
            return result.returncode
        print(json.dumps({'submission_files_verified':count,'paid_api_calls':0}))
    else:
        from submission.build_evidence import collect, export
        if args.command == 'export':
            summary = export(args.out.resolve())
            print(json.dumps({'status':'exported','main_traces':summary['main_trajectories'],'diagnostic_traces':summary['diagnostic_trajectories'],'paid_api_calls':0}))
        else:
            traces = collect()[-1]
            selected = [t for t in traces if t['trajectory']['case_id']==args.case and t['trajectory']['system_id']==args.system]
            if not selected:
                parser.error('No recorded trajectory for this case/system pair')
            print(json.dumps(selected[0],ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print('Submission check failed: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
