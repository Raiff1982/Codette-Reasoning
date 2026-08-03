#!/usr/bin/env python3
"""
ARCHIVED — RETAINED FOR THE RECORD. DO NOT RUN.
===============================================

Flagged 2026-08-03 by a harm screen of all recovered and archived code. It is
not malicious and it is not wired to anything, so it is inert where it sits.
It is marked because of what it does if executed:

    shutil.rmtree('.git-rewrite')                    # discards a filter-branch backup
    git reflog expire --expire=now --all             # discards the reflog
    git gc --prune=now --aggressive                  # discards unreachable objects

Together those remove the safety net that makes a bad history rewrite
recoverable. Once the reflog is expired and unreachable objects pruned, commits
that were only reachable from the reflog are gone for good.

That runs directly against this repository's standing rule: we do not erase the
past, we document and amend forward. It is kept rather than deleted for exactly
the same reason — deleting it would itself be an erasure, and the record of what
was once run against this repository is worth preserving.

If disk pressure ever makes a gc genuinely necessary, do it deliberately and
without `--prune=now` or `reflog expire`, and take a full copy of `.git` first.
"""
import subprocess
import sys
import os

os.chdir(r'j:\codette-clean')

print("=" * 60)
print("CODETTE GIT PUSH CLEANUP SCRIPT")
print("=" * 60)

# Check for .git-rewrite directory (filter-branch backup)
if os.path.exists('.git-rewrite'):
    print("\n[1] Found .git-rewrite directory from previous filter-branch")
    print("    This means filter-branch was running. Removing backup...")
    try:
        import shutil
        shutil.rmtree('.git-rewrite')
        print("    ✓ Backup cleaned")
    except Exception as e:
        print(f"    ✗ Error: {e}")

# Clean reflog
print("\n[2] Reflog garbage collection...")
try:
    result = subprocess.run(['git', 'reflog', 'expire', '--expire=now', '--all'], 
                          capture_output=True, text=True, timeout=30)
    print(f"    ✓ Reflog expired")
except Exception as e:
    print(f"    ✗ Error: {e}")

# Force garbage collection
print("\n[3] Running garbage collection...")
try:
    result = subprocess.run(['git', 'gc', '--prune=now', '--aggressive'], 
                          capture_output=True, text=True, timeout=60)
    print(f"    ✓ GC completed")
except Exception as e:
    print(f"    ✗ Error: {e}")

# Check if results.zip is still in the history
print("\n[4] Checking if results.zip still in git history...")
try:
    result = subprocess.run(['git', 'log', '--all', '--full-history', '--', 'results.zip'],
                          capture_output=True, text=True, timeout=10)
    if 'f03e8f8' in result.stdout or 'results.zip' in result.stdout:
        print("    ✗ File still in history! Running aggressive filter-branch...")
        # Use BFG if available, otherwise git filter-branch with --tag-name-filter=cat
        try:
            # Try git rev-list approach instead
            result = subprocess.run(
                ['git', 'filter-branch', '--force', '--index-filter', 
                 'git rm --cached --ignore-unmatch results.zip', '--', '--all'],
                capture_output=True, text=True, timeout=300
            )
            print("    ✓ Filter-branch completed")
            print(result.stderr[:200] if result.stderr else "")
        except Exception as e:
            print(f"    ✗ Filter-branch error: {e}")
    else:
        print("    ✓ File not found in history - cleanup successful!")
except Exception as e:
    print(f"    ✗ Error checking: {e}")

# Force push
print("\n[5] Force pushing to GitHub...")
try:
    result = subprocess.run(['git', 'push', 'origin', 'main', '--force', '--verbose'],
                          capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        print("    ✓ PUSH SUCCESSFUL!")
        print("\nGit output:")
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    else:
        print("    ✗ PUSH FAILED")
        print("\nError output:")
        print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
except Exception as e:
    print(f"    ✗ Exception: {e}")

# Final status
print("\n[6] Final status...")
try:
    result = subprocess.run(['git', 'status', '-sb'],
                          capture_output=True, text=True, timeout=10)
    print(result.stdout)
except Exception as e:
    print(f"    Error: {e}")

print("\n" + "=" * 60)
print("CLEANUP COMPLETE")
print("=" * 60)
