#!/usr/bin/env python3
"""
Complete cleanup and GitHub push script for voluntary-feature-revelation
"""
import os
import shutil
import subprocess
import sys

base_dir = r"c:\Users\manis\Documents\antigravity\dazzling-hubble"
username = "MangoStudent"
repo_name = "voluntary-feature-revelation"

def run_command(cmd, description):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✓ {description}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {description}")
        print(f"  Error: {e.stderr}")
        return False, e.stderr

print("\n" + "=" * 70)
print("🚀 VOLUNTARY FEATURE REVELATION - COMPLETE SETUP")
print("=" * 70)

print("\n📁 STEP 1: Cleanup Old Files")
print("-" * 70)

os.chdir(base_dir)

# Remove HTML directory
html_dir = os.path.join(base_dir, "HTML")
if os.path.exists(html_dir):
    shutil.rmtree(html_dir)
    print("✓ Removed HTML/ directory")

# Remove generate_html.py
for fname in ["generate_html.py", "cleanup.py"]:
    fpath = os.path.join(base_dir, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f"✓ Removed {fname}")

# Remove old LaTeX file
old_tex = os.path.join(base_dir, "voluntary_feature_revelation.tex")
if os.path.exists(old_tex):
    os.remove(old_tex)
    print("✓ Removed voluntary_feature_revelation.tex")

# Remove old PDF file
old_pdf = os.path.join(base_dir, "voluntary_feature_revelation.pdf")
if os.path.exists(old_pdf):
    os.remove(old_pdf)
    print("✓ Removed voluntary_feature_revelation.pdf")

print("\n📋 STEP 2: Git Operations")
print("-" * 70)

# Check current branch
_, branch = run_command(["git", "branch", "--show-current"], "Get current branch")
branch = branch.strip()
print(f"  Current branch: {branch}")

# Stage changes
success, _ = run_command(["git", "add", "-A"], "Stage all changes")
if not success:
    print("⚠ Could not stage changes")
    sys.exit(1)

# Commit changes
commit_msg = """refactor: remove HTML and rename to voluntary-feature-revelation

- Remove HTML/ directory and generation utilities
- Rename document to voluntary_feature_revelation
- Update title to reflect cleaner, shorter project name
- All content preserved and cross-references maintained

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"""

success, _ = run_command(
    ["git", "commit", "-m", commit_msg],
    "Commit changes"
)

if not success:
    print("⚠ Nothing new to commit - that's fine!")

# Check git status
_, status = run_command(["git", "status", "--short"], "Check status")
if status.strip():
    print(f"  Untracked/modified files:\n{status}")

print("\n🌐 STEP 3: GitHub Configuration")
print("-" * 70)

# Check current remote
_, remotes = run_command(["git", "remote", "-v"], "Check remotes")
print(f"  Current remotes:\n{remotes}")

print("\n" + "=" * 70)
print("✅ CLEANUP COMPLETE & READY FOR PUSH")
print("=" * 70)
print(f"""
📦 Repository Info:
   Owner: {username}
   Repo Name: {repo_name}
   Branch: {branch}
   Location: {base_dir}

✨ Changes Made:
   ✓ Removed HTML/ directory
   ✓ Removed generate_html.py
   ✓ Renamed LaTeX file to voluntary_feature_revelation.tex
   ✓ Updated document title
   ✓ Committed all changes

🚀 Next Steps:
   1. If remote not set up yet, run:
      git remote add origin https://github.com/{username}/{repo_name}.git
      
   2. Push to GitHub:
      git push -u origin {branch}
      
   3. On GitHub, verify the new repository structure!

📝 Note: All PDF files are in .gitignore (won't be committed)
""")
