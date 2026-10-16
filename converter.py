"""DWG to DXF conversion via ODA File Converter."""
import subprocess
import shutil
from pathlib import Path
from typing import Optional

# Path to extracted ODA File Converter binary
# In production Docker, this is baked into the image
ODA_BIN = Path("/opt/oda/ODAFileConverter")
ODA_FALLBACK = Path("/tmp/oda_extract/squashfs-root/usr/bin/ODAFileConverter")


def find_oda() -> Optional[Path]:
    """Locate the ODA File Converter binary."""
    for p in [ODA_BIN, ODA_FALLBACK]:
        if p.exists():
            return p
    # Check PATH
    found = shutil.which("ODAFileConverter")
    if found:
        return Path(found)
    return None


def dwg_to_dxf(dwg_path: str, output_dir: str = None) -> str:
    """
    Convert a DWG file to DXF using ODA File Converter.
    Returns path to the converted DXF file.
    Raises RuntimeError if conversion fails.
    """
    dwg = Path(dwg_path)
    if not dwg.exists():
        raise RuntimeError(f"Input file not found: {dwg_path}")

    # Already DXF - no conversion needed
    if dwg.suffix.lower() == ".dxf":
        return str(dwg)

    oda = find_oda()
    if not oda:
        raise RuntimeError(
            "ODA File Converter not found. "
            "Install from https://www.opendesign.com/guestfiles/oda_file_converter"
        )

    # ODA works on directories, not single files
    work_dir = Path(output_dir) if output_dir else dwg.parent
    input_dir = work_dir / "oda_input"
    output_dxf_dir = work_dir / "oda_output"
    input_dir.mkdir(exist_ok=True)
    output_dxf_dir.mkdir(exist_ok=True)

    # Copy DWG to input dir
    shutil.copy2(str(dwg), str(input_dir / dwg.name))

    # Run ODA: ODAFileConverter <input> <output> <version> <format> <recurse> <audit>
    # ACAD2018 = modern DXF, DXF = output format, 0 = no recurse, 1 = audit
    cmd = [
        "xvfb-run", "-a",
        str(oda),
        str(input_dir),
        str(output_dxf_dir),
        "ACAD2018", "DXF", "0", "1",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("DWG conversion timed out (>5 min)")

    # Find the output DXF
    expected = output_dxf_dir / (dwg.stem + ".dxf")
    if expected.exists():
        return str(expected)

    # Fallback: any DXF in output dir
    dxfs = list(output_dxf_dir.glob("*.dxf"))
    if dxfs:
        return str(dxfs[0])

    raise RuntimeError(
        f"Conversion failed. ODA output: {result.stdout[-500:]}\n"
        f"Errors: {result.stderr[-500:]}"
    )
