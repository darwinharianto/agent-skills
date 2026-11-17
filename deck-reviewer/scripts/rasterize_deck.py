#!/usr/bin/env python3
"""Rasterize a .pptx presentation into per-slide PNGs for visual QA inspection."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf


def rasterize_pptx(pptx_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """Convert pptx -> pdf via LibreOffice, then pdf -> slide_XX.png via PyMuPDF."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) is required to rasterize .pptx slides.")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("slide_*.png"):
        old.unlink()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(pptx_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pdf_path = tmp_path / f"{pptx_path.stem}.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError(f"Expected PDF not generated: {pdf_path}")

        doc = pymupdf.open(str(pdf_path))
        out_files: list[Path] = []
        for idx, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            dest = output_dir / f"slide_{idx:02d}.png"
            pix.save(str(dest))
            out_files.append(dest)
        doc.close()
    return out_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Rasterize PPTX slides to PNGs.")
    parser.add_argument("--input", type=Path, default=Path("workspace/output_deck.pptx"))
    parser.add_argument("--output-dir", type=Path, default=Path("workspace/review_slides"))
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    slides = rasterize_pptx(args.input.resolve(), args.output_dir.resolve(), dpi=args.dpi)
    print(f"Rasterized {len(slides)} slides to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
