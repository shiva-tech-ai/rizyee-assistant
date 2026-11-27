"""
Download the Vosk speech model for RIZYEE.
==========================================
Run with:  python -m rizyee.utils.download_model

This script downloads the small English speech model (~40 MB)
and extracts it into the models/ folder.

The model lets RIZYEE understand spoken English — completely offline!
"""

import os
import sys
import zipfile
import urllib.request

# ── Configuration ──
MODEL_NAME = "vosk-model-en-us-0.22-lgraph"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"

# Figure out where to save the model
# This file is at: rizyee/utils/download_model.py
# Project root is:  ../../  (two folders up)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_NAME)
ZIP_PATH = os.path.join(MODELS_DIR, f"{MODEL_NAME}.zip")


def download_model() -> None:
    """Download and extract the Vosk speech model."""

    # Check if already downloaded
    if os.path.isdir(MODEL_PATH):
        print(f"✅ Model already exists at: {MODEL_PATH}")
        print("   No need to download again!")
        return

    # Create models/ folder if it doesn't exist
    os.makedirs(MODELS_DIR, exist_ok=True)

    # ── Download the zip file ──
    print(f"📥 Downloading speech model ({MODEL_NAME})...")
    print(f"   URL: {MODEL_URL}")
    print(f"   This is about 40 MB — may take a minute...\n")

    try:
        # Download with a progress indicator
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 // total_size)
                mb_done = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
                print(
                    f"\r   [{bar}] {percent}% ({mb_done:.1f}/{mb_total:.1f} MB)",
                    end="",
                    flush=True,
                )

        urllib.request.urlretrieve(MODEL_URL, ZIP_PATH, show_progress)
        print("\n")  # New line after progress bar

    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        print("\n👉 Manual download:")
        print(f"   1. Go to: {MODEL_URL}")
        print(f"   2. Save the zip to: {MODELS_DIR}")
        print(f"   3. Extract it so you have: {MODEL_PATH}")
        sys.exit(1)

    # ── Extract the zip ──
    print("📦 Extracting model files...")
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(MODELS_DIR)
        print("✅ Model extracted successfully!")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)

    # ── Clean up the zip file ──
    try:
        os.remove(ZIP_PATH)
        print("🗑️  Zip file cleaned up.")
    except OSError:
        pass  # Not critical if we can't delete the zip

    print(f"\n✅ Speech model ready at: {MODEL_PATH}")
    print("   You can now run RIZYEE and it will understand your voice!")


if __name__ == "__main__":
    download_model()
