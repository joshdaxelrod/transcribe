#!/usr/bin/env python3
"""
transcribe.py — one-command interview transcription with timestamps.

Single file:
    python transcribe.py gerald                          # looks in the current directory
    python transcribe.py gerald --dir ~/Documents/interviews

Batch mode (no name given): processes every .m4a / .wav file found in --dir,
one at a time, skipping steps already done for each file. By default --dir
is wherever you run the command from, so the usual workflow is just:
    cd ~/Desktop/whatever_folder_today
    python /path/to/transcribe.py
You can still override it explicitly:
    python transcribe.py --dir ~/Desktop/interviews_to_transcribe

For each "<name>" found, it:
  1. Converts <name>.m4a -> <name>.wav (16kHz mono) via ffmpeg
  2. Transcribes with whisper-cli (produces <name>.wav.srt with timestamps)
  3. Converts the .srt into a clean, timestamped <name>_timestamps.txt

REQUIREMENTS:
    - ffmpeg installed and on PATH
    - whisper-cli installed and on PATH
    - a whisper.cpp model, by default at ~/.whisper-cpp/models/ggml-small.bin
      (override with --model or the WHISPER_MODEL environment variable)

Recordings in another language:
    python transcribe.py --language de
    python transcribe.py --language auto
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = Path(
    os.environ.get("WHISPER_MODEL")
    or Path.home() / ".whisper-cpp" / "models" / "ggml-small.bin"
).expanduser()
DEFAULT_LANGUAGE = "en"


def run(cmd, **kwargs):
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def convert_to_wav(m4a_path: Path, wav_path: Path):
    if wav_path.exists():
        print(f"[1/3] {wav_path.name} already exists, skipping conversion.")
        return
    print(f"[1/3] Converting {m4a_path.name} -> {wav_path.name} ...")
    tmp_path = wav_path.parent / (wav_path.name + ".partial")
    try:
        run([
            "ffmpeg", "-y", "-i", str(m4a_path),
            "-ar", "16000", "-ac", "1",
            "-f", "wav", str(tmp_path),
        ])
    except BaseException:
        # Interrupted or failed: leave nothing behind that a later run
        # could mistake for a finished conversion.
        tmp_path.unlink(missing_ok=True)
        raise
    os.replace(tmp_path, wav_path)


def transcribe(wav_path: Path, srt_path: Path, model_path: Path, language: str):
    if srt_path.exists():
        print(f"[2/3] {srt_path.name} already exists, skipping transcription.")
        return
    if not model_path.exists():
        sys.exit(
            f"ERROR: whisper model not found at {model_path}\n"
            "Pass a different one with --model, or set the WHISPER_MODEL "
            "environment variable."
        )
    print(f"[2/3] Transcribing {wav_path.name} with whisper-cli (language: {language}) ...")
    tmp_prefix = srt_path.parent / (srt_path.stem + ".partial")
    tmp_srt = srt_path.parent / (srt_path.stem + ".partial.srt")
    try:
        run([
            "whisper-cli",
            "--model", str(model_path),
            "--language", language,
            "--output-srt",
            "--output-file", str(tmp_prefix),
            str(wav_path),
        ])
    except BaseException:
        tmp_srt.unlink(missing_ok=True)
        raise
    os.replace(tmp_srt, srt_path)


def srt_to_timestamps(srt_path: Path, output_path: Path):
    print(f"[3/3] Converting to timestamped text ...")
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()
    blocks = content.strip().split("\n\n")
    tmp_path = output_path.parent / (output_path.name + ".partial")
    try:
        with open(tmp_path, "w", encoding="utf-8") as out:
            for block in blocks:
                lines = block.split("\n")
                if len(lines) < 3:
                    continue
                timestamp = lines[1].split(" --> ")[0].replace(",", ".")
                text = " ".join(lines[2:]).strip()
                out.write(f"[{timestamp}] {text}\n")
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    os.replace(tmp_path, output_path)
    print(f"\nDone! Final transcript: {output_path}")


def process_one(name: str, base_dir: Path, model_path: Path, language: str):
    """Run the full pipeline for a single basename. Raises on failure."""
    m4a_path = base_dir / f"{name}.m4a"
    wav_path = base_dir / f"{name}.wav"
    srt_path = base_dir / f"{name}.wav.srt"
    output_path = base_dir / f"{name}_timestamps.txt"

    if not m4a_path.exists() and not wav_path.exists():
        raise FileNotFoundError(f"neither {m4a_path} nor {wav_path} exists.")

    if m4a_path.exists():
        convert_to_wav(m4a_path, wav_path)
    transcribe(wav_path, srt_path, model_path, language)
    srt_to_timestamps(srt_path, output_path)


def discover_names(base_dir: Path):
    """Find every distinct basename with a .m4a or .wav file in base_dir,
    sorted alphabetically. A name with both (because a previous run already
    converted it) appears once."""
    names = set()
    for pattern in ("*.m4a", "*.wav"):
        for p in base_dir.glob(pattern):
            names.add(p.stem)
    return sorted(names)


def main():
    parser = argparse.ArgumentParser(description="Transcribe an interview with timestamps.")
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Basename of the audio file, e.g. 'gerald' for gerald.m4a. "
             "Omit this to batch-process every .m4a/.wav file in --dir.",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Directory containing the audio file(s) (default: the current directory)",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL),
        help=f"Path to the whisper.cpp model file (default: {DEFAULT_MODEL}). "
             "Can also be set with the WHISPER_MODEL environment variable.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language spoken in the recording, e.g. 'en', 'de', 'fr' "
             f"(default: {DEFAULT_LANGUAGE}). Use 'auto' to let whisper detect it.",
    )
    args = parser.parse_args()

    base_dir = Path(args.dir).expanduser().resolve()
    if not base_dir.is_dir():
        sys.exit(f"ERROR: directory not found: {base_dir}")

    model_path = Path(args.model).expanduser()

    if args.name:
        # Single-file mode, same as before.
        process_one(args.name, base_dir, model_path, args.language)
        return

    # Batch mode.
    names = discover_names(base_dir)
    if not names:
        sys.exit(f"ERROR: no .m4a or .wav files found in {base_dir}")

    print(f"Found {len(names)} file(s) to process in {base_dir}:")
    for n in names:
        print(f"  - {n}")

    succeeded, failed = [], []
    for i, name in enumerate(names, 1):
        print(f"\n{'=' * 60}\nProcessing {i}/{len(names)}: {name}\n{'=' * 60}")
        try:
            process_one(name, base_dir, model_path, args.language)
            succeeded.append(name)
        except Exception as e:
            print(f"!! FAILED on '{name}': {e}", file=sys.stderr)
            failed.append(name)

    print(f"\n{'=' * 60}\nBatch complete: {len(succeeded)} succeeded, {len(failed)} failed.")
    if succeeded:
        print("Succeeded: " + ", ".join(succeeded))
    if failed:
        print("Failed:    " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
