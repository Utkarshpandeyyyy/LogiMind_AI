import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.resolve()
TEMP_CLONE_DIR = BASE_DIR / "exl_temp"
TARGET_REPO_URL = "https://github.com/NubeEra-DataEngineering/EXL-DataSpecialization.git"
TARGET_BRANCH = "capstone"
SUBFOLDER_NAME = "ctrl alt compete"

def run_command(cmd, cwd=None):
    """Utility to run shell commands and display stdout/stderr."""
    print(f"Running command: {' '.join(cmd)} (cwd: {cwd})")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error running command: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    # 1. Clean up any existing temp clone dir
    if TEMP_CLONE_DIR.exists():
        print(f"Removing existing temporary folder: {TEMP_CLONE_DIR}")
        shutil.rmtree(TEMP_CLONE_DIR, ignore_errors=True)

    # 2. Clone the repository on the capstone branch
    print(f"Cloning {TARGET_REPO_URL} (branch: {TARGET_BRANCH})...")
    clone_cmd = [
        "git", "clone",
        "--single-branch",
        "--branch", TARGET_BRANCH,
        TARGET_REPO_URL,
        str(TEMP_CLONE_DIR)
    ]
    if not run_command(clone_cmd):
        print("Failed to clone repository. Make sure git is installed and target repository is accessible.")
        sys.exit(1)

    # 3. Create the target subfolder inside the cloned repo
    target_dest_dir = TEMP_CLONE_DIR / SUBFOLDER_NAME
    target_dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created subfolder: {target_dest_dir}")

    # 4. Copy project files to the subfolder
    ignore_patterns = {
        ".git", ".venv", "exl_temp", "__pycache__", ".ipynb_checkpoints", 
        "exl_repo", "push_to_exl.py"
    }

    print("Copying project files to the destination subfolder...")
    for item in BASE_DIR.iterdir():
        if item.name in ignore_patterns:
            continue
        
        dest_item = target_dest_dir / item.name
        if item.is_dir():
            print(f"Copying directory: {item.name} -> {dest_item}")
            shutil.copytree(item, dest_item, dirs_exist_ok=True)
        else:
            print(f"Copying file: {item.name} -> {dest_item}")
            shutil.copy2(item, dest_item)

    # 5. Git commit and push inside the cloned repo
    print("Staging files in the cloned repository...")
    if not run_command(["git", "add", "."], cwd=TEMP_CLONE_DIR):
        print("Failed to stage files.")
        sys.exit(1)

    # Check status first to see if there are any changes to commit
    status_proc = subprocess.run(["git", "status", "--porcelain"], cwd=TEMP_CLONE_DIR, text=True, capture_output=True)
    if not status_proc.stdout.strip():
        print("No changes detected to commit. The folder matches target repository state.")
    else:
        print("Committing changes...")
        commit_cmd = ["git", "commit", "-m", f"Add LogiMind AI project files to '{SUBFOLDER_NAME}' folder"]
        if not run_command(commit_cmd, cwd=TEMP_CLONE_DIR):
            print("Failed to commit changes.")
            sys.exit(1)

        print(f"Pushing to remote branch '{TARGET_BRANCH}'...")
        push_cmd = ["git", "push", "origin", TARGET_BRANCH]
        if not run_command(push_cmd, cwd=TEMP_CLONE_DIR):
            print("Failed to push changes. Please check your GitHub credentials/permissions.")
            sys.exit(1)
        
        print("Successfully pushed to GitHub!")

    # 6. Clean up temporary folder
    print("Cleaning up temporary directory...")
    shutil.rmtree(TEMP_CLONE_DIR, ignore_errors=True)
    print("Cleanup completed successfully!")

if __name__ == "__main__":
    main()
