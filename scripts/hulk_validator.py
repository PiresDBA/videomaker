# -*- coding: utf-8 -*-
"""Compatibilidade: use hook_validator.py (o HOOK)."""
from hook_validator import *
if __name__ == "__main__":
    import sys
    from hook_validator import main
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--slug",required=True)
    ap.add_argument("--strict",action="store_true")
    a=ap.parse_args(); sys.exit(main(a.slug,a.strict))
