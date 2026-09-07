"""
scripts/run_ui.py
=================
IMPRINT — Desktop Presentation UI Runner
Hacker House Goa 2026 — Task 3

Face Identification • Web Discovery • Evidence Integrity
"""

import os
import sys

# Ensure repository root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.ui.dashboard import launch_dashboard


def main():
    launch_dashboard()


if __name__ == "__main__":
    main()
