#!/usr/bin/env python3

"""
crate_maker.py

Read iCloud-based file paths (possibly from another Mac),
map them to the *local* user's iCloud Drive, and then generate either:
  - a legacy text-based Scratch Live style .crate file (default),
  - a modern binary Serato .crate file (via pyserato), or
  - an .m3u playlist.

Usage examples:
  # 1) Default: legacy Scratch Live style crate (text) from file
  # Output name automatically derived from input filename
  python crate_maker.py --input paths.txt

  # 2) From directory containing MP3 files (non-recursive)
  # Output name automatically derived from directory name
  python crate_maker.py --input /path/to/20251125_03

  # 3) Explicit output name
  python crate_maker.py \
      --input paths.txt \
      --output 20251125_03.crate

  # 4) Modern binary .crate via pyserato
  python crate_maker.py \
      --input paths.txt \
      --format crate \
      --serato-root ~/Music/_Serato_

  # 5) M3U playlist
  python crate_maker.py \
      --input paths.txt \
      --format m3u

Input can be either:
  - A text file containing one absolute path per line (from any Mac), e.g.:
    /Users/andy/Library/Mobile Documents/com~apple~CloudDocs/Zen/mp3/20251125_03/track1.mp3
  - A directory path containing MP3 files (scanned non-recursively)
"""

import os
import argparse
from pathlib import Path
from typing import List, Tuple

# --- iCloud mapping constants ---

ICLOUD_MARKER = "Library/Mobile Documents/com~apple~CloudDocs"

def map_to_local_icloud(original_path: str) -> str:
    """
    Given an absolute path from some other Mac's iCloud Drive,
    map it to this machine's iCloud Drive.

    Example:
        /Users/andy/Library/Mobile Documents/com~apple~CloudDocs/Zen/mp3/20251125_03/track1.mp3
    becomes (on the local machine, regardless of username):
        ~/Library/Mobile Documents/com~apple~CloudDocs/Zen/mp3/20251125_03/track1.mp3
    """
    original_path = original_path.strip()
    if not original_path:
        return ""

    # Normalize slashes
    original_path = original_path.replace("\\", "/")

    if ICLOUD_MARKER not in original_path:
        # Not an iCloud path we recognize; return as-is
        return os.path.normpath(original_path)

    prefix, suffix = original_path.split(ICLOUD_MARKER, 1)
    # suffix starts like "/Zen/mp3/20251125_03/track1.mp3"
    suffix = suffix.lstrip("/")  # remove leading slash

    local_base = os.path.expanduser(os.path.join("~", ICLOUD_MARKER))
    local_full = os.path.join(local_base, suffix)

    return os.path.normpath(local_full)

def load_paths_from_directory(input_dir: Path) -> List[str]:
    """
    Load MP3 file paths from a directory (non-recursive).
    Returns list of absolute paths to MP3 files found in the directory.
    """
    mp3_paths: List[str] = []
    
    if not input_dir.is_dir():
        return mp3_paths
    
    # Non-recursive: only scan files directly in the directory
    for item in input_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".mp3":
            mp3_paths.append(str(item.resolve()))
    
    return sorted(mp3_paths)  # Sort for consistent ordering

def load_and_map_paths(input_path: Path) -> Tuple[List[str], List[str]]:
    """
    Read paths from input_path (file or directory), map them to local iCloud locations,
    and return (mapped_paths, missing_paths).
    
    If input_path is a directory, scans for MP3 files non-recursively.
    If input_path is a file, reads paths from the file (one per line).
    """
    mapped_paths: List[str] = []
    missing_paths: List[str] = []
    seen = set()  # avoid duplicates
    
    # Determine if input is a directory or file
    if input_path.is_dir():
        # Load MP3 files from directory
        raw_paths = load_paths_from_directory(input_path)
        # For directory input, paths are already local, so no mapping needed
        for p in raw_paths:
            if p in seen:
                continue
            seen.add(p)
            
            if not os.path.exists(p):
                missing_paths.append(p)
            else:
                mapped_paths.append(p)
    else:
        # Read paths from text file
        text = input_path.read_text(encoding="utf-8")
        input_lines = text.splitlines()

        for line in input_lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            local_path = map_to_local_icloud(line)
            if not local_path:
                continue

            if local_path in seen:
                continue
            seen.add(local_path)

            if not os.path.exists(local_path):
                missing_paths.append(local_path)

            mapped_paths.append(local_path)

    return mapped_paths, missing_paths

# --- M3U generation ---

def write_m3u(mapped_paths: List[str], output_file: Path) -> None:
    """
    Write a simple M3U playlist containing the mapped paths.
    """
    if not mapped_paths:
        print("No valid paths found. Nothing to write.")
        return

    if output_file.suffix.lower() != ".m3u":
        output_file = output_file.with_suffix(".m3u")

    if output_file.parent and not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for p in mapped_paths:
            f.write(p + "\n")

    print(f"Wrote M3U playlist with {len(mapped_paths)} entries to:")
    print(f"  {output_file}")

# --- Legacy Scratch Live style .crate generation (plain text) ---

def write_legacy_crate(mapped_paths: List[str], output_file: Path) -> None:
    """
    Write a legacy Scratch Live style .crate file as plain text:
        v2.0
        playlists
        <full POSIX path 1>
        <full POSIX path 2>
        <full POSIX path 3>
        ...
    Serato DJ can still read these crate files.
    """
    if not mapped_paths:
        print("No valid paths found. Nothing to write.")
        return

    if output_file.suffix.lower() != ".crate":
        output_file = output_file.with_suffix(".crate")

    if output_file.parent and not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write("v2.0\n")
        f.write("playlists\n")
        for p in mapped_paths:
            f.write(f"{p}\n")

    print(f"Wrote legacy Scratch Live style crate with {len(mapped_paths)} entries to:")
    print(f"  {output_file}")

# --- Modern Serato .crate generation using pyserato (binary) ---

def write_modern_crate(mapped_paths: List[str], output_file: Path, serato_root: Path | None) -> None:
    """
    Write a modern Serato .crate file using pyserato.

    - The crate *name* is taken from output_file.stem
    - The .crate file itself will be written into:
        <serato_root>/SubCrates/<crate_name>.crate
      where serato_root defaults to pyserato's default Serato folder
      if not provided.
    """
    if not mapped_paths:
        print("No valid paths found. Nothing to write.")
        return

    crate_name = output_file.stem  # e.g. "20251125_03"

    print(f"Creating modern Serato crate: {crate_name}")

    try:
        from pyserato.model.crate import Crate
        from pyserato.builder import Builder
    except ImportError:
        raise SystemExit(
            "ERROR: pyserato is not installed.\n"
            "Install it with:\n\n"
            "    pip install pyserato\n"
        )

    builder = Builder()
    crate = Crate(crate_name)

    for p in mapped_paths:
        crate.add_track(p)

    if serato_root is not None:
        serato_root = serato_root.expanduser().resolve()
        if not serato_root.exists():
            print(f"WARNING: Serato root does not exist yet: {serato_root}")
        builder.save(crate, root_path=serato_root)
        subcrates_dir = serato_root / "SubCrates"
    else:
        # Use pyserato's default Serato folder
        builder.save(crate)
        # Typical default location:
        subcrates_dir = Path.home() / "Music" / "Serato" / "SubCrates"

    crate_path = subcrates_dir / f"{crate_name}.crate"

    print("Wrote modern Serato crate (expected path):")
    print(f"  {crate_path}")
    print("Restart or refocus Serato to see the new crate.")

# --- CLI entrypoint ---

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert iCloud-based paths to local paths and generate either:\n"
            "  - a legacy Scratch Live style .crate file (default),\n"
            "  - a modern binary Serato .crate file (--format crate), or\n"
            "  - an .m3u playlist (--format m3u)."
        )
    )

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help=(
            "Input file or directory:\n"
            "  - Text file: one absolute path per line (from source machine)\n"
            "  - Directory: path to folder containing MP3 files (scanned non-recursively)"
        ),
    )

    parser.add_argument(
        "--output",
        "-o",
        required=False,
        type=Path,
        default=None,
        help=(
            "Output file name (optional). If not provided, derives from input:\n"
            "  - Directory input: uses directory name\n"
            "  - File input: uses filename without extension\n"
            "For crates, the stem (name without extension) becomes the crate name."
        ),
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["legacy", "crate", "m3u"],
        default="legacy",
        help=(
            "Output format:\n"
            "  legacy = Scratch Live style text crate (default)\n"
            "  crate  = modern binary Serato crate via pyserato\n"
            "  m3u    = M3U playlist"
        ),
    )

    parser.add_argument(
        "--serato-root",
        type=Path,
        default=None,
        help=(
            "Optional Serato root folder for modern .crate output "
            "(e.g. ~/Music/_Serato_). If omitted, pyserato's default is used. "
            "Ignored for legacy and m3u formats."
        ),
    )

    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input path not found: {args.input}")

    # Derive output name from input if not provided
    if args.output is None:
        if args.input.is_dir():
            # Use directory name
            output_name = args.input.name
        else:
            # Use filename without extension
            output_name = args.input.stem
        
        # Determine extension based on format
        if args.format == "m3u":
            output_ext = ".m3u"
        else:
            output_ext = ".crate"
        
        args.output = Path(output_name).with_suffix(output_ext)
        print(f"Output name derived from input: {args.output}")

    mapped_paths, missing_paths = load_and_map_paths(args.input)

    if missing_paths:
        print("WARNING: The following paths do NOT exist on this machine:")
        for p in missing_paths:
            print("  MISSING:", p)
        print("They may be unsynced from iCloud or in a different folder.\n")

    if args.format == "m3u":
        write_m3u(mapped_paths, args.output)
    elif args.format == "crate":
        write_modern_crate(mapped_paths, args.output, args.serato_root)
    else:
        # default: legacy text-based crate
        write_legacy_crate(mapped_paths, args.output)

if __name__ == "__main__":
    main()

