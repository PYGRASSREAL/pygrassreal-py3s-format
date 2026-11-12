#!/usr/bin/env python3
"""
PyGrassReal to Creality Print Direct Bridge
Reads a .py3s Single-Container asset and directly sends it to Creality Print 7.2 for 3D printing.
"""

import os
import sys
import tempfile
import subprocess
import shutil
from typing import Optional, Union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py3s_codec import Py3sContainer, sanitize_filename_token, validate_safe_zip_bytes

CREALITY_PRINT_PATHS = [
    r"C:\Program Files\Creality\Creality Print 7.2\CrealityPrint.exe",
    r"C:\Program Files\Creality\Creality Print 5.0\CrealityPrint.exe",
    r"C:\Program Files\Creality\Creality Print\CrealityPrint.exe",
]

def find_creality_print() -> str:
    for p in CREALITY_PRINT_PATHS:
        if os.path.exists(p):
            return p
    # Search in PATH
    found = shutil.which("CrealityPrint.exe")
    if found:
        return found
    raise FileNotFoundError("Creality Print installation not found on this system.")

def send_py3s_to_creality(
    py3s_path: str,
    auto_launch: bool = True,
    secret_key: Optional[Union[str, bytes]] = None,
    require_signature: bool = False,
) -> str:
    if not os.path.exists(py3s_path):
        raise FileNotFoundError(f"File not found: {py3s_path}")

    with open(py3s_path, 'rb') as f:
        buffer = f.read()

    container = Py3sContainer.unpack(
        buffer,
        secret_key=secret_key,
        require_signature=require_signature,
    )

    printing = container.metadata.get("printing")
    telemetry = container.metadata.get("telemetryProfile")

    def resolve_cached_3mf_bytes() -> bytes:
        cache_dir = os.path.abspath(os.path.join(os.path.expanduser("~"), ".pygrassreal", "print-cache"))
        if not os.path.isdir(cache_dir):
            return b""
        candidates = []
        raw_key = None
        if isinstance(printing, dict) and isinstance(printing.get("cacheKey"), str):
            raw_key = printing.get("cacheKey")
        elif isinstance(telemetry, dict) and isinstance(telemetry.get("printCacheKey"), str):
            raw_key = telemetry.get("printCacheKey")
        if raw_key:
            safe_leaf = os.path.basename(raw_key.strip())
            if safe_leaf.lower().endswith(".3mf"):
                candidates.append(os.path.abspath(os.path.join(cache_dir, safe_leaf)))
        for cand in candidates:
            if os.path.commonpath([cache_dir, cand]) == cache_dir and os.path.isfile(cand):
                print(f"[CACHE] Hydrating full-resolution 3MF from local cache: {cand}")
                with open(cand, "rb") as cf:
                    return cf.read()
        return b""

    mfg_bytes = container.print_3mf_data
    if not mfg_bytes:
        mfg_bytes = resolve_cached_3mf_bytes()
    if not mfg_bytes:
        raise ValueError(
            "No Print 3D (.3mf) payload or local print cache found for this .py3s container. "
            "Open the model in Print Preview and re-download Print 3D (.py3s)."
        )
    validate_safe_zip_bytes(mfg_bytes, require_3mf_model=True)

    asset_meta = container.metadata.get("asset")
    raw_name = asset_meta.get("name") if isinstance(asset_meta, dict) else None
    asset_name = sanitize_filename_token(raw_name, default="py3s_print_asset")

    # Report stored 3D Print profile and check SPARKX i7 build plate bounds (260x260x255 mm)
    dims = container.metadata.get("dimensionsMm")
    print_profile = container.metadata.get("printProfile")
    if isinstance(dims, dict):
        w, d, h = dims.get("width"), dims.get("depth"), dims.get("height")
        if all(isinstance(v, (int, float)) for v in (w, d, h)):
            print(f"[INFO] Dimensions: {w:.1f} x {d:.1f} x {h:.1f} mm")
            if h > 255 or w > 260 or d > 260:
                print("[WARN] Model exceeds SPARKX i7 bed size (260 x 260 x 255 mm); scale down in Creality Print before slicing.")
    if isinstance(print_profile, dict):
        print(
            f"[INFO] Profile: Material={print_profile.get('material', 'N/A')}, "
            f"Layer={print_profile.get('layerHeightMm', 'N/A')} mm, "
            f"Infill={print_profile.get('infillPercent', 'N/A')}%, "
            f"Support={print_profile.get('supportType', 'N/A')}"
        )
    if isinstance(printing, dict):
        print(f"[INFO] Print Validation: {printing.get('validation', 'unknown')}")

    # Create temporary print package for Creality Print with strict directory confinement
    temp_dir = os.path.abspath(tempfile.gettempdir())
    target_print_file = os.path.abspath(os.path.join(temp_dir, f"{asset_name}_creality.3mf"))
    if os.path.commonpath([temp_dir, target_print_file]) != temp_dir:
        raise ValueError(f"Unsafe Creality Print output path blocked: {target_print_file}")
    with open(target_print_file, 'wb') as f:
        f.write(mfg_bytes)

    print(f"[OK] Extracted print-ready geometry: {target_print_file} ({len(mfg_bytes)} bytes)")

    if auto_launch:
        creality_exe = find_creality_print()
        print(f"[LAUNCH] Opening model directly in: {creality_exe}")
        # Launch Creality Print asynchronously
        subprocess.Popen([creality_exe, target_print_file])
        print("[SUCCESS] Sent to Creality Print 7.2 successfully!")

    return target_print_file

def pick_py3s_file_dialog() -> Optional[str]:
    """Open a native file picker for selecting a .py3s file."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    initial_dir = downloads_dir if os.path.isdir(downloads_dir) else os.path.expanduser("~")
    selected = filedialog.askopenfilename(
        title="Select a .py3s file to open in Creality Print 7.2",
        initialdir=initial_dir,
        filetypes=[("PY3S files", "*.py3s"), ("All files", "*.*")],
    )
    root.destroy()
    return selected or None

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != "-l"]
    extract_only = "--extract-only" in sys.argv
    pick_file = "--pick" in sys.argv
    has_explicit_input = bool(args)
    should_launch = ("--launch" in sys.argv or "-l" in sys.argv or has_explicit_input or pick_file) and not extract_only
    if pick_file and not has_explicit_input:
        picked = pick_py3s_file_dialog()
        if not picked:
            print("[INFO] Cancelled.")
            sys.exit(0)
        test_file = picked
    else:
        test_file = args[0] if has_explicit_input else os.path.join(os.path.dirname(__file__), "creality_test_model.py3s")
    send_py3s_to_creality(test_file, auto_launch=should_launch)
