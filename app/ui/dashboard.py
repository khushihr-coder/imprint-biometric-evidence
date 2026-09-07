"""
app/ui/dashboard.py
===================
IMPRINT — Presentation & Demo UI
Hacker House Goa 2026 — Task 3

Face Identification • Web Discovery • Evidence Integrity
"""

import os
import sys
import json
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk

# Ensure project root is importable
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.run_pipeline import execute_pipeline
from app.evidence import sha256_file


# ---------------------------------------------------------------------------
# Color Palette & Styling Tokens
# ---------------------------------------------------------------------------
BG_DARK          = "#0a0f1d"   # Main window background
BG_PANEL         = "#111827"   # Secondary panel background
BG_CARD          = "#162032"   # Card container background
BG_CARD_INNER    = "#1e293b"   # Inner card field background
BORDER_COLOR     = "#2c3b52"   # Subtle card border
BORDER_FOCUS     = "#38bdf8"   # Focus / highlight border

TEXT_WHITE       = "#f8fafc"   # Primary text
TEXT_SLATE       = "#94a3b8"   # Secondary text / labels
TEXT_MUTED       = "#64748b"   # Muted / hints
TEXT_CYAN        = "#38bdf8"   # Accent cyan

COLOR_SUCCESS    = "#10b981"   # Emerald-500
COLOR_SUCCESS_BG = "#064e3b"   # Emerald-900
COLOR_RUNNING    = "#38bdf8"   # Sky-400
COLOR_RUNNING_BG = "#0c4a6e"   # Sky-900
COLOR_FAIL       = "#ef4444"   # Red-500
COLOR_FAIL_BG    = "#7f1d1d"   # Red-900
COLOR_PENDING    = "#64748b"   # Slate-500
COLOR_PENDING_BG = "#1e293b"   # Slate-800
COLOR_IDLE_BG    = "#1e293b"   # Default idle background

BTN_PRIMARY_BG   = "#2563eb"   # Royal Blue
BTN_PRIMARY_FG   = "#ffffff"
BTN_SECONDARY_BG = "#334155"   # Slate-700
BTN_SECONDARY_FG = "#f8fafc"

FONT_FAMILY      = "Segoe UI"
FONT_MONO        = "Consolas"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trunc(text, left=12, right=10):
    """Clean hash truncation for readability: e.g. 6ff1a77e6766...30a94."""
    if not text or text == "—":
        return "—"
    if len(text) <= (left + right + 3):
        return text
    return f"{text[:left]}...{text[-right:]}"


def _find_latest_run_dir():
    """Look for the most recent run artifact in artifacts/runs/."""
    runs_dir = os.path.join(ROOT, "artifacts", "runs")
    if not os.path.isdir(runs_dir):
        return None
    subdirs = [
        os.path.join(runs_dir, d) for d in os.listdir(runs_dir)
        if os.path.isdir(os.path.join(runs_dir, d)) and d.startswith("run_")
    ]
    if not subdirs:
        return None
    subdirs.sort(reverse=True)
    for s in subdirs:
        if os.path.isfile(os.path.join(s, "pipeline_result.json")):
            return s
    return None


# ---------------------------------------------------------------------------
# View Evidence Dialog
# ---------------------------------------------------------------------------

class ViewEvidenceDialog(tk.Toplevel):
    """Read-only child window displaying the pretty-printed evidence JSON."""

    def __init__(self, parent, evidence_data, run_id=""):
        super().__init__(parent)
        self.title("IMPRINT — Evidence Record")
        self.geometry("820x620")
        self.minsize(650, 480)
        self.configure(bg=BG_DARK)
        self.transient(parent)

        # Header Frame
        header = tk.Frame(self, bg=BG_PANEL, padx=16, pady=12,
                          highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(header, text="Canonical Evidence Record (JSON)",
                 font=(FONT_FAMILY, 13, "bold"), fg=TEXT_WHITE, bg=BG_PANEL).pack(anchor="w")

        subtext = f"Artifact Run ID: {run_id}  •  Cryptographically fingerprinted & deterministic" if run_id else "Deterministic, tamper-evident JSON structure"
        tk.Label(header, text=subtext, font=(FONT_FAMILY, 9), fg=TEXT_SLATE, bg=BG_PANEL).pack(anchor="w", pady=(2, 0))

        # Pretty-print JSON
        if isinstance(evidence_data, str):
            try:
                evidence_data = json.loads(evidence_data)
            except Exception:
                pass

        if isinstance(evidence_data, (dict, list)):
            formatted_json = json.dumps(evidence_data, indent=2, ensure_ascii=False)
        else:
            formatted_json = str(evidence_data)

        # Scrolled Text Box
        self.text_area = scrolledtext.ScrolledText(
            self, wrap="none", font=(FONT_MONO, 10),
            bg="#080c16", fg="#38bdf8", insertbackground=TEXT_WHITE,
            highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10
        )
        self.text_area.pack(fill="both", expand=True, padx=12, pady=6)
        self.text_area.insert("1.0", formatted_json)
        self.text_area.configure(state="disabled")

        # Bottom Button Bar
        btn_bar = tk.Frame(self, bg=BG_DARK, padx=12, pady=10)
        btn_bar.pack(fill="x")

        self.copy_btn = tk.Button(
            btn_bar, text="Copy JSON", font=(FONT_FAMILY, 10, "bold"),
            bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG, activebackground="#475569",
            activeforeground=TEXT_WHITE, relief="flat", padx=14, pady=6, cursor="hand2",
            command=lambda: self._copy_to_clipboard(formatted_json)
        )
        self.copy_btn.pack(side="left")

        self.copy_feedback = tk.Label(btn_bar, text="", font=(FONT_FAMILY, 9),
                                      fg=COLOR_SUCCESS, bg=BG_DARK)
        self.copy_feedback.pack(side="left", padx=12)

        close_btn = tk.Button(
            btn_bar, text="Close", font=(FONT_FAMILY, 10),
            bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG, activebackground="#475569",
            activeforeground=TEXT_WHITE, relief="flat", padx=16, pady=6, cursor="hand2",
            command=self.destroy
        )
        close_btn.pack(side="right")

    def _copy_to_clipboard(self, content):
        self.clipboard_clear()
        self.clipboard_append(content)
        self.copy_feedback.configure(text="Copied to clipboard!")
        self.after(2500, lambda: self.copy_feedback.configure(text=""))


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------

class ImprintDashboard:
    """Main Tkinter Dashboard for IMPRINT Task 3 presentation."""

    STAGES = [
        ("INPUT",       "[1] INPUT"),
        ("BIOMETRIC",   "[2] BIOMETRIC 1:N"),
        ("WEB",         "[3] WEB DISCOVERY"),
        ("MEDIA",       "[3A] CANDIDATE MEDIA"),
        ("EVIDENCE",    "[4] EVIDENCE"),
        ("BLOCKCHAIN",  "[5] BLOCKCHAIN"),
        ("READBACK",    "[6] READBACK"),
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("IMPRINT — Hacker House Goa 2026 — Task 3")
        self.root.geometry("1260x780")
        self.root.minsize(1100, 700)
        self.root.configure(bg=BG_DARK)

        # State
        self.selected_image_path = None
        self.current_pipeline_result = None
        self.current_evidence = None
        self.current_source_url = None
        self.is_running = False
        self._thumbnail_img = None  # Prevent garbage collection

        # Thread-safe event queue for worker thread communication
        self.msg_queue = queue.Queue()
        self._poll_queue()

        # Build UI
        self._build_header()
        self._build_stage_tracker()
        self._build_main_panels()
        self._build_status_area()

        # Clean startup: do NOT auto-load latest historical run.
        # _check_and_load_latest_run() is retained for optional future inspection.

    def _poll_queue(self):
        """Poll the message queue from the main Tkinter thread."""
        try:
            while True:
                msg_type, payload = self.msg_queue.get_nowait()
                if msg_type == "progress":
                    stage_id, status, details = payload
                    self._handle_progress_update(stage_id, status, details)
                elif msg_type == "complete":
                    result = payload
                    self._handle_pipeline_complete(result)
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self._poll_queue)

    # -----------------------------------------------------------------------
    # Top Header
    # -----------------------------------------------------------------------
    def _build_header(self):
        header_frame = tk.Frame(self.root, bg=BG_PANEL, padx=20, pady=10,
                                highlightbackground=BORDER_COLOR, highlightthickness=1)
        header_frame.pack(fill="x", padx=16, pady=(12, 6))

        # Title row
        title_row = tk.Frame(header_frame, bg=BG_PANEL)
        title_row.pack(fill="x")

        tk.Label(title_row, text="IMPRINT", font=(FONT_FAMILY, 20, "bold"),
                 fg=TEXT_WHITE, bg=BG_PANEL).pack(side="left")

        tag = tk.Label(title_row, text="Hacker House Goa 2026 — Task 3",
                       font=(FONT_FAMILY, 10, "bold"), fg=TEXT_CYAN, bg="#1e293b",
                       padx=8, pady=3)
        tag.pack(side="left", padx=12, pady=2)

        # Subtitle
        tk.Label(header_frame,
                 text="Face Identification  •  Web Discovery  •  Evidence Integrity",
                 font=(FONT_FAMILY, 10), fg=TEXT_SLATE, bg=BG_PANEL).pack(anchor="w", pady=(2, 0))

    # -----------------------------------------------------------------------
    # Stage Tracker (Horizontal Indicator)
    # -----------------------------------------------------------------------
    def _build_stage_tracker(self):
        tracker_frame = tk.Frame(self.root, bg=BG_PANEL, padx=12, pady=8,
                                 highlightbackground=BORDER_COLOR, highlightthickness=1)
        tracker_frame.pack(fill="x", padx=16, pady=4)

        self.stage_pills = {}
        for idx, (stage_id, stage_label) in enumerate(self.STAGES):
            pill = tk.Frame(tracker_frame, bg=COLOR_PENDING_BG, padx=8, pady=4,
                            highlightbackground=BORDER_COLOR, highlightthickness=1)
            pill.pack(side="left", expand=True, fill="x", padx=3)

            lbl_name = tk.Label(pill, text=stage_label, font=(FONT_FAMILY, 8, "bold"),
                                fg=TEXT_SLATE, bg=COLOR_PENDING_BG)
            lbl_name.pack(anchor="center")

            lbl_status = tk.Label(pill, text="○ PENDING", font=(FONT_FAMILY, 8),
                                  fg=COLOR_PENDING, bg=COLOR_PENDING_BG)
            lbl_status.pack(anchor="center")

            self.stage_pills[stage_id] = {
                "frame": pill,
                "name": lbl_name,
                "status": lbl_status
            }

    def _update_stage_pill(self, stage_id, state, text=None):
        """Update visual state of a stage pill: 'PENDING', 'RUNNING', 'SUCCESS', 'FAILED'."""
        if stage_id not in self.stage_pills:
            return
        pill = self.stage_pills[stage_id]

        if state == "RUNNING":
            bg = COLOR_RUNNING_BG
            fg = COLOR_RUNNING
            status_str = text or "⏳ RUNNING"
        elif state == "SUCCESS":
            bg = COLOR_SUCCESS_BG
            fg = COLOR_SUCCESS
            status_str = text or "✓ SUCCESS"
        elif state == "FAILED":
            bg = COLOR_FAIL_BG
            fg = COLOR_FAIL
            status_str = text or "✗ FAILED"
        else:  # PENDING
            bg = COLOR_PENDING_BG
            fg = COLOR_PENDING
            status_str = text or "○ PENDING"

        pill["frame"].configure(bg=bg)
        pill["name"].configure(bg=bg)
        pill["status"].configure(bg=bg, fg=fg, text=status_str)

    def _reset_stage_pills(self):
        for stage_id, _ in self.STAGES:
            self._update_stage_pill(stage_id, "PENDING")

    # -----------------------------------------------------------------------
    # Main Body Panels (3 Columns)
    # -----------------------------------------------------------------------
    def _build_main_panels(self):
        body_frame = tk.Frame(self.root, bg=BG_DARK)
        body_frame.pack(fill="both", expand=True, padx=16, pady=4)

        body_frame.columnconfigure(0, weight=3)  # Left column (Input Probe)
        body_frame.columnconfigure(1, weight=4)  # Middle column (Biometric & Web)
        body_frame.columnconfigure(2, weight=4)  # Right column (Evidence & Blockchain)
        body_frame.rowconfigure(0, weight=1)

        # ------------------------------------------------------------------ #
        # Column 1: Input Face Image Panel                                   #
        # ------------------------------------------------------------------ #
        col1 = tk.Frame(body_frame, bg=BG_CARD, padx=14, pady=12,
                        highlightbackground=BORDER_COLOR, highlightthickness=1)
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=4)

        # Card Title
        self._create_card_header(col1, "INPUT PROBE", "FACE SELECTION")

        # Preview Canvas
        self.canvas_preview = tk.Canvas(col1, width=220, height=220, bg="#0d1424",
                                        highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.canvas_preview.pack(pady=10)
        self._draw_placeholder_image("No Face Selected")

        # Image Details
        info_frame = tk.Frame(col1, bg=BG_CARD)
        info_frame.pack(fill="x", pady=4)

        tk.Label(info_frame, text="File:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=0, column=0, sticky="w")
        self.lbl_filename = tk.Label(info_frame, text="None", font=(FONT_FAMILY, 9, "bold"),
                                     fg=TEXT_WHITE, bg=BG_CARD, wraplength=200, justify="left")
        self.lbl_filename.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(info_frame, text="SHA-256:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.lbl_image_hash = tk.Label(info_frame, text="—", font=(FONT_MONO, 8),
                                       fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_image_hash.grid(row=1, column=1, sticky="w", padx=6, pady=(4, 0))

        # Action Buttons
        btn_frame = tk.Frame(col1, bg=BG_CARD)
        btn_frame.pack(fill="x", pady=(12, 4))

        self.btn_select = tk.Button(
            btn_frame, text="Select Face Image", font=(FONT_FAMILY, 10, "bold"),
            bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG, activebackground="#475569",
            activeforeground=TEXT_WHITE, relief="flat", pady=7, cursor="hand2",
            command=self._on_select_image
        )
        self.btn_select.pack(fill="x", pady=3)

        self.btn_run = tk.Button(
            btn_frame, text="Run Pipeline", font=(FONT_FAMILY, 10, "bold"),
            bg=BTN_PRIMARY_BG, fg=BTN_PRIMARY_FG, activebackground="#1d4ed8",
            activeforeground=TEXT_WHITE, relief="flat", pady=8, cursor="hand2",
            state="disabled", command=self._on_run_pipeline
        )
        self.btn_run.pack(fill="x", pady=3)

        self.lbl_worker_status = tk.Label(col1, text="", font=(FONT_FAMILY, 9),
                                          fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_worker_status.pack(pady=4)

        # ------------------------------------------------------------------ #
        # Column 2: Biometric & Web Discovery Panels                         #
        # ------------------------------------------------------------------ #
        col2 = tk.Frame(body_frame, bg=BG_DARK)
        col2.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        col2.rowconfigure(0, weight=1)
        col2.rowconfigure(1, weight=1)
        col2.columnconfigure(0, weight=1)

        # Card: Biometric 1:N
        card_bio = tk.Frame(col2, bg=BG_CARD, padx=14, pady=10,
                            highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_bio.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

        self.bio_status_badge = self._create_card_header(card_bio, "BIOMETRIC 1:N", "RETRIEVAL")

        bio_grid = tk.Frame(card_bio, bg=BG_CARD)
        bio_grid.pack(fill="x", pady=4)

        tk.Label(bio_grid, text="Top Candidate:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=0, column=0, sticky="w")
        self.lbl_bio_identity = tk.Label(bio_grid, text="—", font=(FONT_FAMILY, 12, "bold"),
                                         fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_bio_identity.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(bio_grid, text="Similarity:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_bio_similarity = tk.Label(bio_grid, text="—", font=(FONT_FAMILY, 10, "bold"),
                                           fg=COLOR_SUCCESS, bg=BG_CARD)
        self.lbl_bio_similarity.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(bio_grid, text="Template:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_bio_template = tk.Label(bio_grid, text="—", font=(FONT_MONO, 8),
                                         fg=TEXT_WHITE, bg=BG_CARD, wraplength=220, justify="left")
        self.lbl_bio_template.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        tk.Label(bio_grid, text="Candidates Evaluated:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_bio_count = tk.Label(bio_grid, text="—", font=(FONT_FAMILY, 9),
                                      fg=TEXT_SLATE, bg=BG_CARD)
        self.lbl_bio_count.grid(row=3, column=1, sticky="w", padx=6, pady=2)

        tk.Label(card_bio, text="* FAISS inner-product search over L2-normalized SFace embeddings",
                 font=(FONT_FAMILY, 8, "italic"), fg=TEXT_MUTED, bg=BG_CARD).pack(anchor="w", pady=(4, 0))

        # Card: Web Discovery & Candidate Media
        card_web = tk.Frame(col2, bg=BG_CARD, padx=14, pady=10,
                            highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_web.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        self.web_status_badge = self._create_card_header(card_web, "WEB DISCOVERY", "GOOGLE LENS")

        web_grid = tk.Frame(card_web, bg=BG_CARD)
        web_grid.pack(fill="x", pady=2)

        tk.Label(web_grid, text="Results:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=0, column=0, sticky="w")
        self.lbl_web_count = tk.Label(web_grid, text="—", font=(FONT_FAMILY, 9, "bold"),
                                      fg=TEXT_WHITE, bg=BG_CARD)
        self.lbl_web_count.grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(web_grid, text="Source:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_web_source = tk.Label(web_grid, text="—", font=(FONT_FAMILY, 9, "bold"),
                                       fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_web_source.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(web_grid, text="Classification:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_web_social = tk.Label(web_grid, text="—", font=(FONT_FAMILY, 9),
                                       fg=TEXT_SLATE, bg=BG_CARD)
        self.lbl_web_social.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        tk.Label(web_grid, text="Media SHA-256:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_media_hash = tk.Label(web_grid, text="—", font=(FONT_MONO, 8),
                                       fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_media_hash.grid(row=3, column=1, sticky="w", padx=6, pady=2)

        # Open Source Result Button
        self.btn_open_url = tk.Button(
            card_web, text="Open Source Result", font=(FONT_FAMILY, 9, "bold"),
            bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG, activebackground="#475569",
            activeforeground=TEXT_WHITE, relief="flat", pady=5, cursor="hand2",
            state="disabled", command=self._on_open_source_url
        )
        self.btn_open_url.pack(fill="x", pady=(8, 2))

        # ------------------------------------------------------------------ #
        # Column 3: Evidence & Blockchain Panels                             #
        # ------------------------------------------------------------------ #
        col3 = tk.Frame(body_frame, bg=BG_DARK)
        col3.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=4)
        col3.rowconfigure(0, weight=1)
        col3.rowconfigure(1, weight=1)
        col3.columnconfigure(0, weight=1)

        # Card: Evidence Record
        card_ev = tk.Frame(col3, bg=BG_CARD, padx=14, pady=10,
                           highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_ev.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

        self.ev_status_badge = self._create_card_header(card_ev, "EVIDENCE RECORD", "PROVENANCE")

        ev_grid = tk.Frame(card_ev, bg=BG_CARD)
        ev_grid.pack(fill="x", pady=2)

        tk.Label(ev_grid, text="Schema:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=0, column=0, sticky="w")
        tk.Label(ev_grid, text="imprint.task3.evidence (v1)", font=(FONT_FAMILY, 9),
                 fg=TEXT_WHITE, bg=BG_CARD).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(ev_grid, text="Evidence SHA-256:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_ev_hash = tk.Label(ev_grid, text="—", font=(FONT_MONO, 8, "bold"),
                                    fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_ev_hash.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(ev_grid, text="Format:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=2, column=0, sticky="w", pady=2)
        tk.Label(ev_grid, text="Deterministic Canonical JSON (UTF-8)", font=(FONT_FAMILY, 8),
                 fg=TEXT_SLATE, bg=BG_CARD).grid(row=2, column=1, sticky="w", padx=6, pady=2)

        self.btn_view_evidence = tk.Button(
            card_ev, text="View Evidence", font=(FONT_FAMILY, 9, "bold"),
            bg=BTN_SECONDARY_BG, fg=BTN_SECONDARY_FG, activebackground="#475569",
            activeforeground=TEXT_WHITE, relief="flat", pady=5, cursor="hand2",
            state="disabled", command=self._on_view_evidence
        )
        self.btn_view_evidence.pack(fill="x", pady=(8, 2))

        # Card: Blockchain Anchor (Base Sepolia)
        card_bc = tk.Frame(col3, bg=BG_CARD, padx=14, pady=10,
                           highlightbackground=BORDER_COLOR, highlightthickness=1)
        card_bc.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

        self.bc_status_badge = self._create_card_header(card_bc, "BLOCKCHAIN ANCHOR", "BASE SEPOLIA")

        bc_grid = tk.Frame(card_bc, bg=BG_CARD)
        bc_grid.pack(fill="x", pady=2)

        tk.Label(bc_grid, text="Network / Chain ID:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=0, column=0, sticky="w")
        tk.Label(bc_grid, text="Base Sepolia (84532)", font=(FONT_FAMILY, 9, "bold"),
                 fg=TEXT_WHITE, bg=BG_CARD).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(bc_grid, text="Transaction:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_bc_tx = tk.Label(bc_grid, text="—", font=(FONT_MONO, 8),
                                  fg=TEXT_CYAN, bg=BG_CARD)
        self.lbl_bc_tx.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        tk.Label(bc_grid, text="Block / Gas Used:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_bc_block_gas = tk.Label(bc_grid, text="—", font=(FONT_FAMILY, 9),
                                         fg=TEXT_SLATE, bg=BG_CARD)
        self.lbl_bc_block_gas.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        tk.Label(bc_grid, text="On-Chain Match:", font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_CARD).grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_bc_match = tk.Label(bc_grid, text="—", font=(FONT_FAMILY, 10, "bold"),
                                     fg=COLOR_SUCCESS, bg=BG_CARD)
        self.lbl_bc_match.grid(row=3, column=1, sticky="w", padx=6, pady=2)

    def _create_card_header(self, parent, title, badge_text=""):
        hdr = tk.Frame(parent, bg=BG_CARD)
        hdr.pack(fill="x", pady=(0, 6))

        tk.Label(hdr, text=title, font=(FONT_FAMILY, 10, "bold"),
                 fg=TEXT_WHITE, bg=BG_CARD).pack(side="left")

        badge = tk.Label(hdr, text=badge_text, font=(FONT_FAMILY, 8, "bold"),
                         fg=TEXT_CYAN, bg="#1e293b", padx=6, pady=2)
        badge.pack(side="right")
        return badge

    # -----------------------------------------------------------------------
    # Bottom Large Final Status Area
    # -----------------------------------------------------------------------
    def _build_status_area(self):
        self.status_panel = tk.Frame(
            self.root, bg=COLOR_IDLE_BG, padx=20, pady=12,
            highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        self.status_panel.pack(fill="x", padx=16, pady=(4, 12))

        # Main status line
        self.lbl_final_status = tk.Label(
            self.status_panel, text="READY TO VERIFY",
            font=(FONT_FAMILY, 16, "bold"), fg=TEXT_WHITE, bg=COLOR_IDLE_BG
        )
        self.lbl_final_status.pack(anchor="center")

        # Subtitle explanation line
        self.lbl_final_sub = tk.Label(
            self.status_panel,
            text="Select a face image to initiate the IMPRINT verification pipeline.",
            font=(FONT_FAMILY, 10), fg=TEXT_SLATE, bg=COLOR_IDLE_BG
        )
        self.lbl_final_sub.pack(anchor="center", pady=(2, 4))

        # Informational / educational note
        note_text = (
            "The blockchain does not identify the person. It verifies that the evidence fingerprint "
            "read from Base Sepolia matches the fingerprint generated from the local evidence record."
        )
        tk.Label(
            self.status_panel, text=note_text,
            font=(FONT_FAMILY, 8, "italic"), fg=TEXT_MUTED, bg=COLOR_IDLE_BG
        ).pack(anchor="center")

    def _set_status_display(self, state, title, subtitle):
        """Configure the prominent bottom status banner."""
        if state == "VERIFIED":
            bg = COLOR_SUCCESS_BG
            fg = COLOR_SUCCESS
            border = COLOR_SUCCESS
        elif state == "RUNNING":
            bg = COLOR_RUNNING_BG
            fg = COLOR_RUNNING
            border = COLOR_RUNNING
        elif state == "FAILED":
            bg = COLOR_FAIL_BG
            fg = COLOR_FAIL
            border = COLOR_FAIL
        else:  # IDLE
            bg = COLOR_IDLE_BG
            fg = TEXT_WHITE
            border = BORDER_COLOR

        self.status_panel.configure(bg=bg, highlightbackground=border)
        self.lbl_final_status.configure(text=title, fg=fg, bg=bg)
        self.lbl_final_sub.configure(text=subtitle, fg=TEXT_WHITE if state == "VERIFIED" else TEXT_SLATE, bg=bg)

        # Update child widgets in the status panel
        for child in self.status_panel.winfo_children():
            child.configure(bg=bg)

    # -----------------------------------------------------------------------
    # Thumbnail / Image Display
    # -----------------------------------------------------------------------
    def _draw_placeholder_image(self, text="No Image"):
        self.canvas_preview.delete("all")
        self.canvas_preview.create_rectangle(10, 10, 210, 210, outline=BORDER_COLOR, width=1, dash=(4, 4))
        self.canvas_preview.create_text(110, 100, text="👤", font=(FONT_FAMILY, 36), fill=TEXT_MUTED)
        self.canvas_preview.create_text(110, 140, text=text, font=(FONT_FAMILY, 9), fill=TEXT_MUTED)

    def _load_preview_thumbnail(self, path):
        if not os.path.isfile(path):
            self._draw_placeholder_image("File not found")
            return
        try:
            img = Image.open(path)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            self._thumbnail_img = ImageTk.PhotoImage(img)
            self.canvas_preview.delete("all")
            self.canvas_preview.create_image(110, 110, image=self._thumbnail_img)
        except Exception as exc:
            self._draw_placeholder_image("Error loading image")

    # -----------------------------------------------------------------------
    # UI Actions & Events
    # -----------------------------------------------------------------------
    def _on_select_image(self):
        """Open file dialog for probe face selection."""
        if self.is_running:
            return

        initial_dir = os.path.join(ROOT, "lfw-deepfunneled")
        if not os.path.isdir(initial_dir):
            initial_dir = ROOT

        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Face Image",
            initialdir=initial_dir,
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png"), ("All Files", "*.*")]
        )

        if not path:
            return

        self.selected_image_path = os.path.abspath(path)
        filename = os.path.basename(self.selected_image_path)
        self.lbl_filename.configure(text=filename)

        # Compute probe SHA-256
        try:
            h = sha256_file(self.selected_image_path)
            self.lbl_image_hash.configure(text=_trunc(h, 10, 8))
        except Exception:
            self.lbl_image_hash.configure(text="Error computing hash")

        # Load preview
        self._load_preview_thumbnail(self.selected_image_path)

        # Enable Run button, reset stages and status
        self.btn_run.configure(state="normal")
        self._reset_stage_pills()
        self._reset_result_cards()
        self._set_status_display("IDLE", "READY TO VERIFY", f"Selected: {filename}. Click 'Run Pipeline' to verify.")

    def _on_run_pipeline(self):
        """Trigger background pipeline thread."""
        if self.is_running or not self.selected_image_path:
            return

        self.is_running = True
        self.btn_run.configure(state="disabled")
        self.btn_select.configure(state="disabled")
        self.btn_view_evidence.configure(state="disabled")
        self.btn_open_url.configure(state="disabled")

        self._reset_stage_pills()
        self._reset_result_cards()
        self._set_status_display(
            "RUNNING", "PROCESSING PIPELINE...",
            "Running face detection, embedding, FAISS search, web discovery, evidence hashing, and Base Sepolia transaction..."
        )
        self.lbl_worker_status.configure(text="Pipeline active...")

        # Worker thread
        t = threading.Thread(target=self._worker_thread, args=(self.selected_image_path,), daemon=True)
        t.start()

    def _worker_thread(self, image_path):
        """Worker thread executing the pipeline without freezing the GUI."""
        def progress_cb(stage_id, status, details=None):
            self.msg_queue.put(("progress", (stage_id, status, details)))

        try:
            result = execute_pipeline(image_path, progress_callback=progress_cb)
        except Exception as exc:
            result = {
                "status": "FAILED",
                "final_status": f"FAILED — {exc}",
                "error": str(exc),
            }

        self.msg_queue.put(("complete", result))

    def _handle_progress_update(self, stage_id, status, details=None):
        """Called on Tkinter main thread on every stage transition."""
        self._update_stage_pill(stage_id, status)
        details = details or {}

        # Update card fields dynamically as each stage finishes
        if stage_id == "INPUT" and status == "SUCCESS":
            h = details.get("image_hash", "")
            if h:
                self.lbl_image_hash.configure(text=_trunc(h, 10, 8))

        elif stage_id == "BIOMETRIC" and status == "SUCCESS":
            top_id = details.get("top_identity", "—")
            sim = details.get("similarity", 0.0)
            tpl = details.get("template", "—")
            cnt = details.get("candidate_count", 0)
            self.lbl_bio_identity.configure(text=top_id)
            self.lbl_bio_similarity.configure(text=f"{sim:.4f}")
            self.lbl_bio_template.configure(text=tpl)
            self.lbl_bio_count.configure(text=f"{cnt} candidate(s) retrieved")
            self.bio_status_badge.configure(text="✓ SUCCESS", fg=COLOR_SUCCESS)

        elif stage_id == "WEB" and status == "SUCCESS":
            cnt = details.get("result_count", 0)
            src = details.get("selected_source", "—")
            url = details.get("selected_url", "—")
            is_social = details.get("is_social", False)
            self.lbl_web_count.configure(text=f"{cnt} candidates found")
            self.lbl_web_source.configure(text=src)
            self.lbl_web_social.configure(text="Social/Web candidate" if is_social else "General web match")
            self.current_source_url = url
            if url and url != "—":
                self.btn_open_url.configure(state="normal")
            self.web_status_badge.configure(text="✓ LIVE SEARCH", fg=COLOR_SUCCESS)

        elif stage_id == "MEDIA" and status == "SUCCESS":
            media_hash = details.get("media_sha256", "")
            if media_hash:
                self.lbl_media_hash.configure(text=_trunc(media_hash, 10, 8))

        elif stage_id == "EVIDENCE" and status == "SUCCESS":
            ev_hash = details.get("evidence_hash", "")
            if ev_hash:
                self.lbl_ev_hash.configure(text=_trunc(ev_hash, 10, 8))
            self.current_evidence = details.get("evidence")
            self.btn_view_evidence.configure(state="normal")
            self.ev_status_badge.configure(text="✓ READY", fg=COLOR_SUCCESS)

        elif stage_id == "BLOCKCHAIN" and status == "SUCCESS":
            tx = details.get("tx_hash", "")
            blk = details.get("block_number", "")
            gas = details.get("gas_used", "")
            self.lbl_bc_tx.configure(text=_trunc(tx, 12, 8))
            self.lbl_bc_block_gas.configure(text=f"Block {blk}  •  {gas} gas units")
            self.bc_status_badge.configure(text="✓ ANCHORED", fg=COLOR_SUCCESS)

    def _handle_pipeline_complete(self, result):
        """Called when pipeline execution finishes."""
        self.is_running = False
        self.btn_select.configure(state="normal")
        self.btn_run.configure(state="normal")
        self.lbl_worker_status.configure(text="")

        self.current_pipeline_result = result
        if "evidence" in result:
            self.current_evidence = result["evidence"]
            self.btn_view_evidence.configure(state="normal")

        # Check final status
        status = result.get("status")
        final_status = result.get("final_status", "")
        readback = result.get("readback", {})
        readback_match = readback.get("match", False)
        readback_status = readback.get("status", "")

        if status == "SUCCESS" and readback_match and readback_status == "VERIFIED":
            self.lbl_bc_match.configure(text="TRUE ✓", fg=COLOR_SUCCESS)
            self._set_status_display(
                "VERIFIED", "✓ EVIDENCE VERIFIED",
                "Local evidence fingerprint matches the on-chain fingerprint."
            )
        else:
            self.lbl_bc_match.configure(text="FALSE ✗", fg=COLOR_FAIL)
            self._set_status_display(
                "FAILED", final_status or "PIPELINE FAILED",
                result.get("error", "Evidence verification could not be completed.")
            )

    # -----------------------------------------------------------------------
    # Card Display Reset
    # -----------------------------------------------------------------------
    def _reset_result_cards(self):
        self.lbl_bio_identity.configure(text="—")
        self.lbl_bio_similarity.configure(text="—")
        self.lbl_bio_template.configure(text="—")
        self.lbl_bio_count.configure(text="—")
        self.bio_status_badge.configure(text="RETRIEVAL", fg=TEXT_CYAN)

        self.lbl_web_count.configure(text="—")
        self.lbl_web_source.configure(text="—")
        self.lbl_web_social.configure(text="—")
        self.lbl_media_hash.configure(text="—")
        self.web_status_badge.configure(text="GOOGLE LENS", fg=TEXT_CYAN)

        self.lbl_ev_hash.configure(text="—")
        self.ev_status_badge.configure(text="PROVENANCE", fg=TEXT_CYAN)

        self.lbl_bc_tx.configure(text="—")
        self.lbl_bc_block_gas.configure(text="—")
        self.lbl_bc_match.configure(text="—")
        self.bc_status_badge.configure(text="BASE SEPOLIA", fg=TEXT_CYAN)

        self.btn_open_url.configure(state="disabled")
        self.btn_view_evidence.configure(state="disabled")
        self.current_source_url = None
        self.current_evidence = None

    # -----------------------------------------------------------------------
    # View Evidence & Open URL Buttons
    # -----------------------------------------------------------------------
    def _on_view_evidence(self):
        if not self.current_evidence:
            messagebox.showinfo("Evidence", "No evidence record available for current run.")
            return
        run_id = ""
        if isinstance(self.current_pipeline_result, dict):
            run_id = self.current_pipeline_result.get("run_id", "")
        ViewEvidenceDialog(self.root, self.current_evidence, run_id=run_id)

    def _on_open_source_url(self):
        if self.current_source_url and self.current_source_url != "—":
            webbrowser.open(self.current_source_url)
        else:
            messagebox.showinfo("Web Candidate", "No web source URL available.")

    # -----------------------------------------------------------------------
    # Auto-load Latest Run Artifact (Inspection Mode)
    # -----------------------------------------------------------------------
    def _check_and_load_latest_run(self):
        latest_dir = _find_latest_run_dir()
        if not latest_dir:
            return

        result_path = os.path.join(latest_dir, "pipeline_result.json")
        evidence_path = os.path.join(latest_dir, "evidence.json")
        if not os.path.isfile(result_path):
            return

        try:
            with open(result_path, "r", encoding="utf-8") as f:
                res = json.load(f)

            evidence_data = None
            if os.path.isfile(evidence_path):
                with open(evidence_path, "r", encoding="utf-8") as f:
                    evidence_data = json.load(f)

            # Populate state
            self.current_pipeline_result = res
            self.current_evidence = evidence_data

            # Image
            img_path = res.get("image_path")
            if img_path and os.path.isfile(img_path):
                self.selected_image_path = img_path
                self.lbl_filename.configure(text=os.path.basename(img_path))
                self.lbl_image_hash.configure(text=_trunc(res.get("image_sha256", ""), 10, 8))
                self._load_preview_thumbnail(img_path)
                self.btn_run.configure(state="normal")

            # Biometric
            bio = res.get("biometric", {})
            self.lbl_bio_identity.configure(text=bio.get("top_identity", "—"))
            score = bio.get("top_score")
            self.lbl_bio_similarity.configure(text=f"{score:.4f}" if isinstance(score, (int, float)) else "—")
            self.lbl_bio_template.configure(text=bio.get("top_template", "—"))
            cnt = bio.get("candidate_count", 0)
            self.lbl_bio_count.configure(text=f"{cnt} candidate(s) retrieved")
            self.bio_status_badge.configure(text="✓ SUCCESS", fg=COLOR_SUCCESS)

            # Web
            web = res.get("web", {})
            self.lbl_web_count.configure(text=f"{web.get('result_count', 0)} candidates found")
            self.lbl_web_source.configure(text=web.get("selected_source", "—"))
            self.lbl_web_social.configure(text="Social/Web candidate" if web.get("is_social") else "General web match")
            url = web.get("selected_url")
            self.current_source_url = url
            if url:
                self.btn_open_url.configure(state="normal")
            self.web_status_badge.configure(text="✓ LIVE SEARCH", fg=COLOR_SUCCESS)

            # Candidate Media
            cmedia = res.get("candidate_media", {})
            self.lbl_media_hash.configure(text=_trunc(cmedia.get("sha256", ""), 10, 8))

            # Evidence
            ev = res.get("evidence", {})
            self.lbl_ev_hash.configure(text=_trunc(ev.get("sha256", ""), 10, 8))
            if evidence_data:
                self.btn_view_evidence.configure(state="normal")
            self.ev_status_badge.configure(text="✓ READY", fg=COLOR_SUCCESS)

            # Blockchain
            bc = res.get("blockchain", {})
            tx = bc.get("tx_hash", "")
            blk = bc.get("block_number", "")
            gas = bc.get("gas_used", "")
            self.lbl_bc_tx.configure(text=_trunc(tx, 12, 8))
            self.lbl_bc_block_gas.configure(text=f"Block {blk}  •  {gas} gas units")
            self.bc_status_badge.configure(text="✓ ANCHORED", fg=COLOR_SUCCESS)

            # Readback
            rb = res.get("readback", {})
            if rb.get("match") and rb.get("status") == "VERIFIED":
                self.lbl_bc_match.configure(text="TRUE ✓", fg=COLOR_SUCCESS)
                self._set_status_display(
                    "VERIFIED", "✓ EVIDENCE VERIFIED",
                    f"Showing stored verification artifact ({res.get('run_id')}). Select any face to run anew."
                )
                for stage_id, _ in self.STAGES:
                    self._update_stage_pill(stage_id, "SUCCESS")

        except Exception as exc:
            # Fallback cleanly if artifact cannot be loaded
            pass


def launch_dashboard():
    """Entry point to start the Tkinter dashboard application."""
    root = tk.Tk()
    app = ImprintDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    launch_dashboard()
