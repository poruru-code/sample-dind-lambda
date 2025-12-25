
import sys
import os
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace

# Project root path
PROJECT_ROOT = Path("/mnt/c/GitHub/edge-serverless-box").resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from tools.cli.commands import build
from tools.cli import config as cli_config

def verify_cwd_independence():
    # 1. Setup a dummy project in /tmp/cwd-test
    proj_dir = Path("/tmp/cwd-test")
    proj_dir.mkdir(parents=True, exist_ok=True)
    template_path = proj_dir / "template.yml"
    with open(template_path, "w") as f:
        f.write("AWSTemplateFormatVersion: '2010-09-09'\nResources: {}")
    
    # Create generator.yml
    gen_yml = proj_dir / "generator.yml"
    with open(gen_yml, "w") as f:
        f.write(f"paths:\n  sam_template: {template_path}\n  output_dir: {proj_dir / 'out'}\n")

    print(f"Project setup at {proj_dir}")

    # 2. Change CWD to / (something completely different)
    original_cwd = os.getcwd()
    os.chdir("/")
    print(f"Current CWD: {os.getcwd()}")

    # 3. Try to run build --dry-run with explicit template path
    print("--- Running esb build -t <path> from / ---")
    args = Namespace(template=str(template_path), dry_run=True, verbose=True, no_cache=False)
    
    # We call cli_config.set_template_yaml as main.py would
    cli_config.set_template_yaml(str(template_path))
    
    try:
        build.run(args)
        print("✅ SUCCESS: Build ran successfully from a different CWD.")
    except Exception as e:
        print(f"❌ FAILURE: Build failed from different CWD: {e}")
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    verify_cwd_independence()
