#!/usr/bin/env python3
"""Download a small GGUF model for local llama.cpp inference."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import hf_hub_download

DEFAULT_REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
DEFAULT_FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a tiny GGUF model for the demo")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="Hugging Face repo containing GGUF")
    parser.add_argument("--filename", default=DEFAULT_FILENAME, help="GGUF filename in the repo")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "models"),
        help="Directory where the GGUF file should be stored",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = hf_hub_download(
        repo_id=args.repo_id,
        filename=args.filename,
        local_dir=str(output_dir),
        local_dir_use_symlinks=False,
    )
    print(f"Downloaded model to: {model_path}")


if __name__ == "__main__":
    main()
