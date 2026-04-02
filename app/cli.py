#!/usr/bin/env python3
"""
CLI tool for Typst template management.

Supports installing templates from GitHub releases, local zip files, and the web app.
"""
import argparse
import sys
import os
from pathlib import Path
import zipfile
import json
import re
import subprocess
from typing import Optional

# Import the theme installation logic
from theme_package import install_theme_package


def run_gh_command(args: list[str]) -> tuple[int, str, str]:
    """Run a gh (GitHub CLI) command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", "gh CLI not found. Install from https://cli.github.com"
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"


def download_gh_release(repo: str, asset_pattern: str, output_path: Path) -> bool:
    """
    Download a release asset from a GitHub repository.
    
    Args:
        repo: GitHub repo in format "owner/repo"
        asset_pattern: Pattern for asset filename (e.g., "*.zip")
        output_path: Where to save the downloaded file
    
    Returns:
        True if successful, False otherwise
    """
    print(f"🔍 Finding releases for {repo}...")
    
    # Get the latest release
    code, stdout, stderr = run_gh_command(["release", "list", "-R", repo, "--limit", "1", "--json", "tagName"])
    if code != 0:
        print(f"❌ Failed to fetch releases: {stderr}")
        return False
    
    if not stdout.strip():
        print(f"❌ No releases found for {repo}")
        return False
    
    try:
        releases = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from gh")
        return False
    
    if not releases:
        print(f"❌ No releases found")
        return False
    
    tag = releases[0].get("tagName")
    if not tag:
        print(f"❌ Could not determine release tag")
        return False
    
    print(f"📦 Latest release: {tag}")
    
    # Download the asset
    print(f"⬇️  Downloading asset matching '{asset_pattern}'...")
    code, stdout, stderr = run_gh_command([
        "release", "download", tag, "-R", repo,
        "-p", asset_pattern,
        "-O", "-"  # Output to stdout
    ])
    
    if code != 0:
        print(f"❌ Failed to download: {stderr}")
        return False
    
    # Write to file
    output_path.write_bytes(stdout.encode('utf-8') if isinstance(stdout, str) else stdout)
    print(f"✅ Downloaded to {output_path}")
    return True


def install_from_github(repo: str, install_dir: Path) -> bool:
    """
    Install a Typst template from a GitHub release.
    
    Args:
        repo: GitHub repository in format "owner/repo"
        install_dir: Installation directory
    
    Returns:
        True if successful, False otherwise
    """
    import tempfile
    
    # Create temp file for zip download
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        temp_zip = Path(tf.name)
    
    try:
        # Download the zip
        if not download_gh_release(repo, "*.zip", temp_zip):
            return False
        
        # Install the theme
        print(f"\n📝 Installing theme...")
        zip_bytes = temp_zip.read_bytes()
        
        try:
            meta = install_theme_package(zip_bytes, install_dir)
            print(f"✅ Theme installed successfully!")
            print(f"   Name: {meta.get('name')}")
            print(f"   ID: {meta.get('id')}")
            print(f"   Author: {meta.get('author', 'Unknown')}")
            return True
        except ValueError as e:
            print(f"❌ Failed to install: {e}")
            return False
    
    finally:
        # Clean up temp file
        if temp_zip.exists():
            temp_zip.unlink()


def install_from_file(zip_path: Path, install_dir: Path) -> bool:
    """Install a Typst template from a local zip file."""
    if not zip_path.exists():
        print(f"❌ File not found: {zip_path}")
        return False
    
    if not zip_path.suffix.lower() == ".zip":
        print(f"❌ File must be a .zip file")
        return False
    
    print(f"📝 Installing theme from {zip_path.name}...")
    
    try:
        zip_bytes = zip_path.read_bytes()
        meta = install_theme_package(zip_bytes, install_dir)
        print(f"✅ Theme installed successfully!")
        print(f"   Name: {meta.get('name')}")
        print(f"   ID: {meta.get('id')}")
        print(f"   Author: {meta.get('author', 'Unknown')}")
        return True
    except ValueError as e:
        print(f"❌ Failed to install: {e}")
        return False


def list_installed_themes(install_dir: Path) -> bool:
    """List installed themes in a directory."""
    if not install_dir.exists():
        print(f"No installed themes in {install_dir}")
        return True
    
    themes = []
    for theme_dir in install_dir.iterdir():
        if not theme_dir.is_dir():
            continue
        
        meta_file = theme_dir / "meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    themes.append(meta)
            except (json.JSONDecodeError, IOError):
                pass
    
    if not themes:
        print(f"No installed themes in {install_dir}")
        return True
    
    print(f"📚 Installed themes in {install_dir}:")
    for theme in themes:
        print(f"  • {theme.get('name', 'Unknown')} ({theme.get('id', 'unknown')})")
        if theme.get('description'):
            print(f"    {theme['description']}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Typst template manager - install themes from GitHub or local files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install from GitHub release
  python cli.py install-github owner/repo

  # Install from local zip file
  python cli.py install owner/repo/release/theme.zip

  # List installed themes
  python cli.py list

  # Install to custom directory
  python cli.py install theme.zip --install-dir /path/to/themes
        """
    )
    
    parser.add_argument(
        "--install-dir",
        type=Path,
        default=Path(__file__).parent / "templates_custom",
        help="Installation directory (default: app/templates_custom)",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # install-github command
    gh_parser = subparsers.add_parser(
        "install-github",
        help="Install a theme from a GitHub repository release",
    )
    gh_parser.add_argument(
        "repo",
        help="GitHub repository (format: owner/repo)",
    )
    
    # install command (from file)
    file_parser = subparsers.add_parser(
        "install",
        help="Install a theme from a local zip file",
    )
    file_parser.add_argument(
        "zip_file",
        type=Path,
        help="Path to theme zip file",
    )
    
    # list command
    subparsers.add_parser(
        "list",
        help="List installed themes",
    )
    
    args = parser.parse_args()
    
    # Ensure install directory exists
    args.install_dir.mkdir(parents=True, exist_ok=True)
    
    if args.command == "install-github":
        success = install_from_github(args.repo, args.install_dir)
        sys.exit(0 if success else 1)
    
    elif args.command == "install":
        success = install_from_file(args.zip_file, args.install_dir)
        sys.exit(0 if success else 1)
    
    elif args.command == "list":
        success = list_installed_themes(args.install_dir)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
