#!/usr/bin/env python3
"""Raccourci : python clonecompress.py bzip2|lzma|7z ..."""
import sys
from clonecompress.cli import principal

if __name__ == "__main__":
    sys.exit(principal())
