import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk


MIDDAI_USER_DIR = os.path.join(os.path.expanduser("~"), "Documents", "MiddAI")
ACTIVE_MODEL_FILE = os.path.join(MIDDAI_USER_DIR, "active_model.json")
LOCAL_ACTIVE_MODEL_FILE = (
    Path(sys.executable).resolve().parent / "active_model.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1] / "active_model.json"
)

LM_STUDIO_API_PORT = 1234
MIDDAI_CHAT_PORT = 5000
LOCAL_MODEL_IDENTIFIER = "local-model"
LM_STUDIO_DOWNLOAD_URL = "https://lmstudio.ai/download"
DEFAULT_CONTEXT_LENGTH = 12000
GPU_OFFLOAD_OFF = "off"
GPU_OFFLOAD_HALF = "0.5"

MEMORY_MODE_RULES = "rules"
MEMORY_MODE_AI_JUDGE = "ai_judge"
MEMORY_MODE_OFF = "off"

SETUP_SPLASH = {
    "root": None,
    "image": None,
    "status_var": None,
    "phrase_index": 0,
    "next_phrase_at": 0,
}

SPLASH_TRANSPARENT_COLOR = "#010203"
SPLASH_TEXT_COLOR = "#23b7ff"
SPLASH_SCREEN_HEIGHT_RATIO = 0.72
SPLASH_PHRASES = [
    "Reticulating Splines",
    "Waking the forest server",
    "Reading signs in the moss",
    "Tying blue knots in the code",
    "Asking LM Studio politely",
    "Finding the path through the trees",
    "Gathering sparks from the stones",
    "Listening for the local model",
    "Drawing bright runes in the air",
    "Checking the roots",
    "Opening the clearing",
    "Making pictures out of sticks and mud",
]


MODEL_OPTIONS = [
    {
        "label": "Laptop - Phi-4-mini",
        "model_name": "Phi-4-mini",
        "download_query": "microsoft/phi-4-mini@q4_k_m",
        "match_terms": [
            "microsoft/phi-4-mini",
            "lmstudio-community/phi-4-mini-instruct-gguf",
            "phi-4-mini-instruct",
            "phi-4-mini",
        ],
        "description": "Recommended laptop option. Small, practical, and responsive.",
        "download_size": "approx. 2.49 GB",
        "memory_mode": MEMORY_MODE_RULES,
        "context_length": 6000,
        "gpu_offload": GPU_OFFLOAD_OFF,
    },
    {
        "label": "Mid-range - Qwen3-4B-Instruct-2507",
        "model_name": "Qwen3-4B-Instruct-2507",
        "download_query": "qwen/qwen3-4b-2507@q4_k_m",
        "match_terms": [
            "qwen/qwen3-4b-2507",
            "qwen3-4b-instruct-2507",
            "qwen3-4b",
        ],
        "description": "Balanced local option with AI Judge memory for ordinary PCs and stronger laptops.",
        "download_size": "approx. 2.50 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 30000,
        "gpu_offload": GPU_OFFLOAD_OFF,
    },
    {
        "label": "Mid-range - Qwen3-8B-GGUF",
        "model_name": "Qwen3-8B-GGUF",
        "download_query": "qwen/qwen3-8b@q4_k_m",
        "match_terms": ["qwen/qwen3-8b", "qwen3-8b-gguf", "qwen3-8b"],
        "description": "Better answers than 4B, with AI Judge memory, but noticeably heavier.",
        "download_size": "approx. 5.03 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 30000,
        "gpu_offload": GPU_OFFLOAD_HALF,
    },
    {
        "label": "High-end PC - Qwen3-30B-A3B-Instruct-2507",
        "model_name": "Qwen3-30B-A3B-Instruct-2507",
        "download_query": "qwen/qwen3-30b-a3b-2507@q4_k_m",
        "match_terms": [
            "qwen/qwen3-30b-a3b-2507",
            "qwen3-30b-a3b-instruct-2507",
            "qwen3-30b-a3b",
        ],
        "description": "Largest option. Only choose this for a stronger machine.",
        "download_size": "approx. 18.56 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 70000,
        "gpu_offload": GPU_OFFLOAD_HALF,
    },
    {
        "label": "Extreme - Llama 3.3 70B Instruct",
        "model_name": "Llama-3.3-70B-Instruct",
        "download_query": "https://huggingface.co/lmstudio-community/Llama-3.3-70B-Instruct-GGUF",
        "match_terms": [
            "lmstudio-community/llama-3.3-70b-instruct-gguf",
            "llama-3.3-70b-instruct",
            "llama 3.3 70b",
        ],
        "description": "Extreme workstation option. Not for normal laptops.",
        "download_size": "approx. 42.5 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 120000,
        "gpu_offload": GPU_OFFLOAD_HALF,
        "requires_understood": True,
        "system_requirements": [
            "EXTREME MODEL: APPROXIMATELY 71B PARAMETERS.",
            "Q4_K_M IS ABOUT 42.5 GB BEFORE RUNTIME MEMORY OVERHEAD.",
            "RECOMMENDED: 64 GB+ SYSTEM MEMORY OR 48 GB+ VRAM/UNIFIED MEMORY.",
            "THIS MAY FREEZE, CRASH, OR MAKE WEAKER PCS UNUSABLE.",
        ],
    },
    {
        "label": "Extreme - Mistral Large 2 123B",
        "model_name": "Mistral-Large-Instruct-2407",
        "download_query": "https://huggingface.co/lmstudio-community/Mistral-Large-Instruct-2407-GGUF",
        "match_terms": [
            "lmstudio-community/mistral-large-instruct-2407-gguf",
            "mistral-large-instruct-2407",
            "mistral large instruct 2407",
            "mistral large 2",
        ],
        "description": "Extreme workstation option. Very large Mistral model.",
        "download_size": "approx. 73.3 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 120000,
        "gpu_offload": GPU_OFFLOAD_HALF,
        "requires_understood": True,
        "system_requirements": [
            "EXTREME MODEL: APPROXIMATELY 123B PARAMETERS.",
            "Q4_K_M CAN BE AROUND 70+ GB BEFORE RUNTIME MEMORY OVERHEAD.",
            "RECOMMENDED: 96 GB-128 GB+ SYSTEM MEMORY OR MULTI-GPU/WORKSTATION HARDWARE.",
            "THIS MAY FREEZE, CRASH, OR MAKE WEAKER PCS UNUSABLE.",
        ],
    },
    {
        "label": "Image Analysis - Qwen2.5-VL-3B",
        "model_name": "Qwen2.5-VL-3B",
        "download_query": "qwen/qwen2.5-vl-3b@q4_k_m",
        "match_terms": [
            "qwen/qwen2.5-vl-3b",
            "qwen2.5-vl-3b",
            "qwen2_5-vl-3b",
        ],
        "description": (
            "Light image-analysis model. Describes photos, objects, screenshots, "
            "and visible plant features."
        ),
        "warning": "DO NOT USE THIS LOW-END MODEL TO DECIDE IF WILD PLANTS ARE EDIBLE OR SAFE.",
        "download_size": "approx. 2.15 GB",
        "memory_mode": MEMORY_MODE_RULES,
        "context_length": 6000,
        "gpu_offload": GPU_OFFLOAD_OFF,
        "image_analysis": True,
    },
    {
        "label": "Image Analysis - Qwen2.5-VL-7B",
        "model_name": "Qwen2.5-VL-7B",
        "download_query": "qwen/qwen2.5-vl-7b@q4_k_m",
        "match_terms": [
            "qwen/qwen2.5-vl-7b",
            "qwen2.5-vl-7b",
            "qwen2_5-vl-7b",
        ],
        "description": (
            "Medium image-analysis model. Better for detailed visible features, "
            "plant structure, documents, and object checks."
        ),
        "download_size": "approx. 5.37 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 16000,
        "gpu_offload": GPU_OFFLOAD_HALF,
        "image_analysis": True,
    },
    {
        "label": "Image Analysis - Qwen2.5-VL-32B",
        "model_name": "Qwen2.5-VL-32B",
        "download_query": "qwen/qwen2.5-vl-32b@q4_k_m",
        "match_terms": [
            "qwen/qwen2.5-vl-32b",
            "qwen2.5-vl-32b",
            "qwen2_5-vl-32b",
        ],
        "description": (
            "High-end image-analysis model. Strongest local option for detailed "
            "visual reasoning."
        ),
        "download_size": "approx. 18.5 GB",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": 30000,
        "gpu_offload": GPU_OFFLOAD_HALF,
        "image_analysis": True,
    },
    {
        "label": "Restricted - Dolphin 2.8 Mistral 7B",
        "model_name": "dolphin-2.8-mistral-7b-v02",
        "download_query": "https://huggingface.co/lmstudio-community/dolphin-2.8-mistral-7b-v02-GGUF",
        "match_terms": [
            "lmstudio-community/dolphin-2.8-mistral-7b-v02-gguf",
            "dolphin-2.8-mistral-7b-v02",
            "dolphin-2.8-mistral-7b",
            "dolphin",
        ],
        "description": "Password-protected option for approved users.",
        "download_size": "approx. 4.37 GB",
        "password": "byteme",
        "memory_mode": MEMORY_MODE_OFF,
        "context_length": DEFAULT_CONTEXT_LENGTH,
        "gpu_offload": GPU_OFFLOAD_OFF,
    },
    {
        "label": "Custom - Use loaded LM Studio model",
        "model_name": "Custom loaded LM Studio model",
        "download_query": "",
        "match_terms": [],
        "description": (
            "Advanced option. Use a model that is already loaded in LM Studio. "
            "MiddAI will not download, unload, or configure it."
        ),
        "download_size": "none",
        "memory_mode": MEMORY_MODE_AI_JUDGE,
        "context_length": DEFAULT_CONTEXT_LENGTH,
        "gpu_offload": "LM Studio setting",
        "custom_loaded_model": True,
    },
]


def make_dialog_root():
    root = create_setup_window("MiddAI", withdraw=True)

    try:
        root.attributes("-topmost", True)
        root.lift()
        root.update()
    except tk.TclError:
        pass

    return root


def show_error(title, message):
    root = make_dialog_root()
    messagebox.showerror(title, message, parent=root)
    root.destroy()


def show_info(title, message):
    root = make_dialog_root()
    messagebox.showinfo(title, message, parent=root)
    root.destroy()


def show_lm_studio_required(lm_studio_app=None):
    root = create_setup_window("LM Studio required")
    root.resizable(False, False)
    root.configure(bg="#f6f8f3")

    frame = tk.Frame(root, bg="#f6f8f3", padx=20, pady=18)
    frame.pack(fill="both", expand=True)

    if lm_studio_app:
        body = (
            "MiddAI found LM Studio, but could not find the lms command that "
            "MiddAI uses to download/load models and start the local server.\n\n"
            "Please open LM Studio once, let it finish setting itself up, then "
            "close it and run MiddAI again.\n\n"
            f"Detected LM Studio app:\n{lm_studio_app}"
        )
    else:
        body = (
            "LM Studio is required before MiddAI can run local AI models.\n\n"
            "Please download and install LM Studio, open it once, then close it "
            "and start MiddAI again."
        )

    tk.Label(
        frame,
        text="LM Studio is required",
        justify="left",
        bg="#f6f8f3",
        fg="#111111",
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w")

    tk.Label(
        frame,
        text=body,
        justify="left",
        bg="#f6f8f3",
        fg="#111111",
        wraplength=500,
        pady=12,
    ).pack(anchor="w")

    tk.Label(
        frame,
        text=LM_STUDIO_DOWNLOAD_URL,
        justify="left",
        bg="#f6f8f3",
        fg="#075985",
        font=("Segoe UI", 9, "underline"),
    ).pack(anchor="w", pady=(0, 12))

    buttons = tk.Frame(frame, bg="#f6f8f3")
    buttons.pack(fill="x")

    def open_download():
        webbrowser.open(LM_STUDIO_DOWNLOAD_URL)

    def open_lm_studio():
        if not lm_studio_app:
            return

        try:
            subprocess.Popen([lm_studio_app])
        except OSError as error:
            messagebox.showerror("Could not open LM Studio", str(error), parent=root)

    close_button = tk.Button(buttons, text="Close", width=11, command=root.destroy)
    close_button.pack(side="right", padx=(8, 0))

    download_button = tk.Button(
        buttons,
        text="Download LM Studio",
        width=18,
        command=open_download,
    )
    download_button.pack(side="right")

    if lm_studio_app:
        open_button = tk.Button(
            buttons,
            text="Open LM Studio",
            width=16,
            command=open_lm_studio,
        )
        open_button.pack(side="right", padx=(0, 8))

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    lift_window_over_splash(root)
    root.mainloop()


def setup_asset_path(relative_path):
    relative_path = Path(relative_path)

    if hasattr(sys, "_MEIPASS"):
        external_assets = Path(sys.executable).resolve().parent / "Assets"

        if relative_path.parts and relative_path.parts[0].lower() == "assets":
            packaged_asset = external_assets.joinpath(*relative_path.parts[1:])

            if packaged_asset.exists():
                return packaged_asset

            return external_assets

        return Path(sys._MEIPASS) / relative_path

    return Path(__file__).resolve().parents[1] / "chat_program" / relative_path


def show_setup_splash():
    close_setup_splash()

    root = tk.Tk()
    root.overrideredirect(True)
    root.resizable(False, False)
    root.configure(bg=SPLASH_TRANSPARENT_COLOR)

    try:
        root.attributes("-transparentcolor", SPLASH_TRANSPARENT_COLOR)
    except tk.TclError:
        pass

    frame = tk.Frame(root, bg=SPLASH_TRANSPARENT_COLOR, padx=0, pady=0)
    frame.pack()

    logo_path = setup_asset_path(Path("assets") / "logo.png")

    try:
        logo_image = tk.PhotoImage(file=str(logo_path))
        available_height = max(480, int(root.winfo_screenheight() * SPLASH_SCREEN_HEIGHT_RATIO))
        scale = max(1, ceil(logo_image.height() / available_height))

        if scale > 1:
            logo_image = logo_image.subsample(scale, scale)

        logo = tk.Label(
            frame,
            image=logo_image,
            bg=SPLASH_TRANSPARENT_COLOR,
            borderwidth=0,
            highlightthickness=0,
        )
        logo.pack()
        SETUP_SPLASH["image"] = logo_image
    except tk.TclError:
        fallback = tk.Label(
            frame,
            text="MiddAI",
            bg=SPLASH_TRANSPARENT_COLOR,
            fg=SPLASH_TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
            borderwidth=0,
            highlightthickness=0,
        )
        fallback.pack()
        SETUP_SPLASH["image"] = None

    status_var = tk.StringVar(value=SPLASH_PHRASES[0])
    status = tk.Label(
        frame,
        textvariable=status_var,
        bg=SPLASH_TRANSPARENT_COLOR,
        fg=SPLASH_TEXT_COLOR,
        font=("Segoe UI", 16, "bold"),
        borderwidth=0,
        highlightthickness=0,
        pady=12,
    )
    status.pack()

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.lift()
    root.update()

    SETUP_SPLASH["root"] = root
    SETUP_SPLASH["status_var"] = status_var
    SETUP_SPLASH["phrase_index"] = 0
    SETUP_SPLASH["next_phrase_at"] = time.monotonic() + 1.2
    return root


def refresh_setup_splash():
    root = SETUP_SPLASH.get("root")

    if root is None:
        return

    try:
        now = time.monotonic()
        status_var = SETUP_SPLASH.get("status_var")

        if status_var is not None and now >= SETUP_SPLASH.get("next_phrase_at", 0):
            phrase_index = (SETUP_SPLASH.get("phrase_index", 0) + 1) % len(
                SPLASH_PHRASES
            )
            SETUP_SPLASH["phrase_index"] = phrase_index
            SETUP_SPLASH["next_phrase_at"] = now + 1.4
            status_var.set(SPLASH_PHRASES[phrase_index])

        root.update_idletasks()
        root.update()
    except tk.TclError:
        SETUP_SPLASH["root"] = None
        SETUP_SPLASH["image"] = None
        SETUP_SPLASH["status_var"] = None


def set_setup_splash_status(message, hold_seconds=1.6):
    root = SETUP_SPLASH.get("root")
    status_var = SETUP_SPLASH.get("status_var")

    if root is None or status_var is None:
        return

    try:
        status_var.set(message)
        SETUP_SPLASH["next_phrase_at"] = time.monotonic() + hold_seconds
        root.update_idletasks()
        root.update()
    except tk.TclError:
        SETUP_SPLASH["root"] = None
        SETUP_SPLASH["image"] = None
        SETUP_SPLASH["status_var"] = None


def close_setup_splash():
    root = SETUP_SPLASH.get("root")

    if root is not None:
        try:
            root.destroy()
        except tk.TclError:
            pass

    SETUP_SPLASH["root"] = None
    SETUP_SPLASH["image"] = None
    SETUP_SPLASH["status_var"] = None


def lift_window_over_splash(window):
    def drop_topmost():
        try:
            if window.winfo_exists():
                window.attributes("-topmost", False)
        except tk.TclError:
            pass

    try:
        window.lift()
        window.attributes("-topmost", True)
        window.after(350, drop_topmost)
    except tk.TclError:
        pass


def setup_parent_window():
    parent = SETUP_SPLASH.get("root")

    try:
        if parent is not None and parent.winfo_exists():
            return parent
    except tk.TclError:
        return None

    return None


def create_setup_window(title, withdraw=False):
    parent = setup_parent_window()

    if parent is not None:
        window = tk.Toplevel(parent)
    else:
        window = tk.Tk()

    window.title(title)

    if withdraw:
        window.withdraw()

    return window


def save_active_model(option, model_key, chat_model_id=LOCAL_MODEL_IDENTIFIER):
    data = {
        "label": option.get("label", ""),
        "model_name": option.get("model_name", ""),
        "model_key": model_key,
        "chat_model_id": chat_model_id,
        "memory_mode": option.get("memory_mode", MEMORY_MODE_AI_JUDGE),
        "context_length": get_context_length(option),
        "gpu_offload": get_gpu_offload(option),
        "image_analysis": bool(option.get("image_analysis")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_active_model_file(ACTIVE_MODEL_FILE, data)
    write_active_model_file(LOCAL_ACTIVE_MODEL_FILE, data, required=False)


def read_active_model_file(path):
    path = Path(path)

    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def read_active_model():
    for path in (ACTIVE_MODEL_FILE, LOCAL_ACTIVE_MODEL_FILE):
        data = read_active_model_file(path)

        if data:
            return data

    return {}


def write_active_model_file(path, data, required=True):
    path = Path(path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_name(f"{path.name}.tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        os.replace(temp_file, path)
    except OSError:
        if required:
            raise


def ask_yes_no(title, message):
    parent = setup_parent_window()
    dialog = create_setup_window(title)
    dialog.resizable(False, False)
    dialog.configure(bg="#f6f8f3")

    try:
        if parent is not None:
            dialog.transient(parent)
        dialog.grab_set()
    except tk.TclError:
        pass

    answer = {"value": False}

    frame = tk.Frame(dialog, bg="#f6f8f3", padx=18, pady=16)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text=title,
        justify="left",
        bg="#f6f8f3",
        fg="#111111",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    tk.Label(
        frame,
        text=message,
        justify="left",
        bg="#f6f8f3",
        fg="#111111",
        wraplength=420,
        pady=12,
    ).pack(anchor="w")

    buttons = tk.Frame(frame, bg="#f6f8f3")
    buttons.pack(fill="x", pady=(4, 0))

    def choose(value):
        answer["value"] = value
        dialog.destroy()

    no_button = tk.Button(buttons, text="No", width=10, command=lambda: choose(False))
    no_button.pack(side="right", padx=(8, 0))

    yes_button = tk.Button(buttons, text="Yes", width=10, command=lambda: choose(True))
    yes_button.pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", lambda: choose(False))
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    lift_window_over_splash(dialog)
    dialog.wait_window()

    return answer["value"]


def confirm_extreme_model_requirements(option):
    requirements = option.get("system_requirements")

    if not option.get("requires_understood") or not requirements:
        return True

    parent = setup_parent_window()
    dialog = create_setup_window("EXTREME MODEL WARNING")
    dialog.resizable(False, False)
    dialog.configure(bg="#2b0000")

    try:
        if parent is not None:
            dialog.transient(parent)
        dialog.grab_set()
    except tk.TclError:
        pass

    confirmed = {"value": False}
    typed = tk.StringVar(value="")

    frame = tk.Frame(dialog, bg="#2b0000", padx=20, pady=18)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text="WARNING: EXTREME MODEL SELECTED",
        justify="center",
        bg="#2b0000",
        fg="#ff2a2a",
        font=("Segoe UI", 15, "bold"),
    ).pack(fill="x", pady=(0, 12))

    tk.Label(
        frame,
        text="\n".join(requirements),
        justify="left",
        bg="#2b0000",
        fg="#ff2a2a",
        wraplength=560,
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w", pady=(0, 14))

    tk.Label(
        frame,
        text="TYPE",
        justify="center",
        bg="#2b0000",
        fg="#ff2a2a",
        font=("Segoe UI", 10, "bold"),
    ).pack(fill="x")

    tk.Label(
        frame,
        text="UNDERSTOOD",
        justify="center",
        bg="#9a6a00",
        fg="#ffffff",
        font=("Segoe UI", 14, "bold"),
        padx=12,
        pady=4,
    ).pack(pady=(4, 8))

    tk.Label(
        frame,
        text="IN BLOCK CAPITALS TO CONTINUE.",
        justify="center",
        bg="#2b0000",
        fg="#ff2a2a",
        font=("Segoe UI", 10, "bold"),
    ).pack(fill="x", pady=(0, 8))

    entry = tk.Entry(
        frame,
        textvariable=typed,
        width=28,
        justify="center",
        font=("Segoe UI", 12, "bold"),
    )
    entry.pack(pady=(0, 14))

    buttons = tk.Frame(frame, bg="#2b0000")
    buttons.pack(fill="x")

    ok_button = tk.Button(buttons, text="OK", width=10, state="disabled")
    cancel_button = tk.Button(buttons, text="Cancel", width=10)

    def update_ok_state(*_):
        state = "normal" if typed.get() == "UNDERSTOOD" else "disabled"
        ok_button.configure(state=state)

    def choose(value):
        confirmed["value"] = value
        dialog.destroy()

    typed.trace_add("write", update_ok_state)
    ok_button.configure(command=lambda: choose(True))
    cancel_button.configure(command=lambda: choose(False))
    cancel_button.pack(side="right", padx=(8, 0))
    ok_button.pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", lambda: choose(False))
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() - width) // 2
    y = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    lift_window_over_splash(dialog)
    entry.focus_set()
    dialog.wait_window()

    return confirmed["value"]


def check_model_password(root, option):
    required_password = option.get("password")

    if not required_password:
        return True

    entered_password = simpledialog.askstring(
        "Password required",
        f"Enter the password to use {option['model_name']}:",
        parent=root,
        show="*",
    )

    if entered_password is None:
        return False

    if entered_password == required_password:
        return True

    messagebox.showerror(
        "Incorrect password",
        "That password is not correct.",
        parent=root,
    )
    return False


def memory_mode_label(option):
    mode = option.get("memory_mode")

    if mode == MEMORY_MODE_OFF:
        return "memory off"

    if mode == MEMORY_MODE_RULES:
        return "fast rule memory"

    return "AI judge memory"


def get_context_length(option):
    if option.get("custom_loaded_model"):
        return DEFAULT_CONTEXT_LENGTH

    try:
        return int(option.get("context_length", DEFAULT_CONTEXT_LENGTH))
    except (TypeError, ValueError):
        return DEFAULT_CONTEXT_LENGTH


def get_gpu_offload(option):
    return str(option.get("gpu_offload", GPU_OFFLOAD_OFF))


def gpu_offload_label(option):
    if option.get("custom_loaded_model"):
        return "LM STUDIO SETTING"

    gpu_offload = get_gpu_offload(option)

    if gpu_offload == GPU_OFFLOAD_HALF:
        return "50% GPU / 50% CPU"

    if gpu_offload.lower() == GPU_OFFLOAD_OFF:
        return "OFF"

    return gpu_offload.upper()


def model_download_size_label(option):
    return option.get("download_size", "varies by selected quant")


def short_download_label(download_query):
    if not download_query:
        return "Already loaded in LM Studio"

    label = download_query

    if label.startswith("https://huggingface.co/"):
        label = "HF: " + label.removeprefix("https://huggingface.co/")

    return label


def display_download_label(download_query):
    label = short_download_label(download_query)

    if len(label) > 58 and label.startswith("HF: "):
        label = label[:55].rstrip() + "..."

    return (
        label.replace("/", " / ")
        .replace("@", " @ ")
        .replace("-", "- ")
        .replace("_", "_ ")
    )


def choose_model(model_statuses=None):
    model_statuses = model_statuses or {}
    selected = {"option": None}
    parent = setup_parent_window()
    root = create_setup_window("MiddAI LM Studio Setup")
    root.resizable(True, True)
    lift_window_over_splash(root)

    choice = tk.IntVar(value=0)
    root_bg = "#0b1117"
    panel_bg = root_bg
    text_fg = "#e5e7eb"
    muted_fg = "#94a3b8"
    root.configure(bg=root_bg)

    try:
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(1580, max(1100, screen_width - 80))
        window_height = min(880, max(640, screen_height - 120))
        root.geometry(f"{window_width}x{window_height}")
        root.minsize(1000, 620)
    except tk.TclError:
        pass

    title = tk.Label(
        root,
        text="Choose the LM Studio model MiddAI should prepare",
        font=("Segoe UI", 12, "bold"),
        bg=root_bg,
        fg=text_fg,
        padx=18,
    )
    title.pack(anchor="w", pady=(12, 4))

    note = tk.Label(
        root,
        justify="left",
        text=(
            "This may download a large model file using LM Studio.\n"
            "LM Studio API will use port 1234. MiddAI chat uses port 5000."
        ),
        bg=root_bg,
        fg=muted_fg,
        padx=18,
    )
    note.pack(anchor="w", pady=(0, 8))

    scroll_shell = tk.Frame(root, bg=root_bg)
    scroll_shell.pack(fill="both", expand=True)

    body_canvas = tk.Canvas(
        scroll_shell,
        bg=root_bg,
        borderwidth=0,
        highlightthickness=0,
    )
    body_scrollbar = ttk.Scrollbar(
        scroll_shell,
        orient="vertical",
        command=body_canvas.yview,
    )
    body_canvas.configure(yscrollcommand=body_scrollbar.set)
    body_scrollbar.pack(side="right", fill="y")
    body_canvas.pack(side="left", fill="both", expand=True)

    body_frame = tk.Frame(body_canvas, bg=root_bg)
    body_window = body_canvas.create_window(
        (0, 0),
        window=body_frame,
        anchor="nw",
    )

    def refresh_scroll_region(_event=None):
        body_canvas.configure(scrollregion=body_canvas.bbox("all"))

    def fit_body_width(event):
        body_canvas.itemconfigure(body_window, width=event.width)

    def scroll_body(event):
        if event.delta:
            body_canvas.yview_scroll(int(-event.delta / 120), "units")

    body_frame.bind("<Configure>", refresh_scroll_region)
    body_canvas.bind("<Configure>", fit_body_width)
    root.bind("<MouseWheel>", scroll_body)

    model_groups = [
        {
            "title": "LAPTOP / LIGHT SYSTEMS",
            "color": "#1f8a43",
            "requirements": (
                "RECOMMENDED: 8 GB+ SYSTEM RAM.\n"
                "PHI USES FAST RULE MEMORY FOR LOW-END PCS.\n"
                "QWEN 4B USES AI JUDGE MEMORY."
            ),
            "options": [0, 1],
        },
        {
            "title": "MID / HIGH SYSTEMS",
            "color": "#c79a00",
            "requirements": (
                "RECOMMENDED: 16 GB-32 GB+ SYSTEM RAM.\n"
                "STRONGER PCS OR DECENT GPU PREFERRED.\n"
                "USES 50% GPU OFFLOAD WHEN SELECTED."
            ),
            "options": [2, 3],
        },
        {
            "title": "EXTREME WORKSTATIONS",
            "color": "#c22b2b",
            "requirements": (
                "RECOMMENDED: 64 GB-128 GB+ RAM.\n"
                "USES 50% GPU OFFLOAD WHEN SELECTED.\n"
                "MAY FREEZE WEAKER PCS."
            ),
            "options": [4, 5],
        },
    ]

    groups_frame = tk.Frame(body_frame, bg=root_bg, padx=16)
    groups_frame.pack(fill="x", expand=False)

    for column in range(3):
        groups_frame.grid_columnconfigure(column, weight=1, uniform="model_groups")

    def add_model_card(parent_frame, index):
        option = MODEL_OPTIONS[index]
        model_key = model_statuses.get(option["model_name"])
        restricted_text = " - PASSWORD REQUIRED" if option.get("password") else ""

        if option.get("custom_loaded_model"):
            status_text = "USES LOADED MODEL"
            status_color = "#38bdf8"
        else:
            status_text = "DOWNLOADED" if model_key else "NOT DOWNLOADED"
            status_color = "#1f7a3f" if model_key else "#a15c00"

        card = tk.Frame(parent_frame, bg=panel_bg, padx=4, pady=4)
        card.pack(fill="x", anchor="n", pady=(0, 7))

        radio = tk.Radiobutton(
            card,
            variable=choice,
            value=index,
            text=f"{option['label']}{restricted_text}",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            justify="left",
            wraplength=320,
            bg=panel_bg,
            fg=text_fg,
            activebackground=panel_bg,
            activeforeground=text_fg,
            selectcolor=panel_bg,
        )
        radio.pack(fill="x", anchor="w")

        status = tk.Label(
            card,
            justify="left",
            text=f"STATUS: {status_text}",
            fg=status_color,
            bg=panel_bg,
            padx=24,
            font=("Segoe UI", 8, "bold"),
        )
        status.pack(fill="x", anchor="w")

        if option.get("custom_loaded_model"):
            detail_text = (
                f"{option['description']}\n"
                f"MEMORY: {memory_mode_label(option).upper()}\n"
                "CONTEXT: CURRENT LM STUDIO SETTING\n"
                "GPU: CURRENT LM STUDIO SETTING\n"
                f"DOWNLOAD SIZE: {model_download_size_label(option).upper()}\n"
                "SOURCE: ALREADY LOADED MODEL"
            )
        else:
            warning_text = (
                f"WARNING: {option['warning']}\n"
                if option.get("warning")
                else ""
            )
            detail_text = (
                f"{option['description']}\n"
                f"{warning_text}"
                f"MEMORY: {memory_mode_label(option).upper()}\n"
                f"CONTEXT: {get_context_length(option)} TOKENS\n"
                f"GPU: {gpu_offload_label(option)}\n"
                f"DOWNLOAD SIZE: {model_download_size_label(option).upper()}\n"
                f"SOURCE: {display_download_label(option['download_query'])}"
            )

        details = tk.Label(
            card,
            justify="left",
            text=detail_text,
            bg=panel_bg,
            fg=muted_fg,
            padx=24,
            wraplength=320,
            font=("Segoe UI", 8),
        )
        details.pack(fill="x", anchor="w")

    for column, group in enumerate(model_groups):
        border = tk.Frame(
            groups_frame,
            bg=group["color"],
            padx=2,
            pady=2,
        )
        border.grid(row=0, column=column, sticky="nsew", padx=5, pady=4)

        inner = tk.Frame(border, bg=panel_bg, padx=8, pady=7)
        inner.pack(fill="both", expand=True)

        tk.Label(
            inner,
            text=group["title"],
            fg=group["color"],
            bg=panel_bg,
            justify="left",
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x", anchor="w")

        tk.Label(
            inner,
            text=group["requirements"],
            fg=text_fg,
            bg=panel_bg,
            justify="left",
            wraplength=320,
            font=("Segoe UI", 8, "bold"),
        ).pack(fill="x", anchor="w", pady=(2, 7))

        for option_index in group["options"]:
            add_model_card(inner, option_index)

    lower_groups_frame = tk.Frame(body_frame, bg=root_bg, padx=16)
    lower_groups_frame.pack(fill="x", expand=False, pady=(0, 6))

    for column in range(3):
        lower_groups_frame.grid_columnconfigure(
            column,
            weight=1,
            uniform="model_groups",
        )

    restricted_border = tk.Frame(lower_groups_frame, bg="#000000", padx=2, pady=2)
    restricted_border.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 0))

    restricted_inner = tk.Frame(restricted_border, bg=panel_bg, padx=8, pady=6)
    restricted_inner.pack(fill="both", expand=True)

    tk.Label(
        restricted_inner,
        text="RESTRICTED MODEL",
        fg=text_fg,
        bg=panel_bg,
        font=("Segoe UI", 9, "bold"),
    ).pack(fill="x", anchor="w")

    tk.Label(
        restricted_inner,
        text="PASSWORD REQUIRED. MEMORY OFF. USE ONLY IF YOU KNOW WHY YOU WANT THIS MODEL.",
        fg=text_fg,
        bg=panel_bg,
        justify="left",
        wraplength=320,
        font=("Segoe UI", 8, "bold"),
    ).pack(fill="x", anchor="w", pady=(2, 6))

    add_model_card(restricted_inner, 9)

    custom_border = tk.Frame(lower_groups_frame, bg="#2563eb", padx=2, pady=2)
    custom_border.grid(row=0, column=1, sticky="nsew", padx=5, pady=(5, 0))

    custom_inner = tk.Frame(custom_border, bg=panel_bg, padx=8, pady=6)
    custom_inner.pack(fill="both", expand=True)

    tk.Label(
        custom_inner,
        text="CUSTOM MODEL",
        fg="#38bdf8",
        bg=panel_bg,
        font=("Segoe UI", 9, "bold"),
    ).pack(fill="x", anchor="w")

    tk.Label(
        custom_inner,
        text="ADVANCED USERS. USES A MODEL ALREADY LOADED IN LM STUDIO.",
        fg=text_fg,
        bg=panel_bg,
        justify="left",
        wraplength=320,
        font=("Segoe UI", 8, "bold"),
    ).pack(fill="x", anchor="w", pady=(2, 6))

    add_model_card(custom_inner, 10)

    image_border = tk.Frame(lower_groups_frame, bg="#ff4fb3", padx=2, pady=2)
    image_border.grid(
        row=0,
        column=2,
        sticky="nsew",
        padx=5,
        pady=(5, 0),
    )

    image_inner = tk.Frame(image_border, bg=panel_bg, padx=8, pady=6)
    image_inner.pack(fill="both", expand=True)

    tk.Label(
        image_inner,
        text="IMAGE ANALYSIS MODE",
        fg="#ff4fb3",
        bg=panel_bg,
        font=("Segoe UI", 9, "bold"),
    ).pack(fill="x", anchor="w")

    tk.Label(
        image_inner,
        text="UPLOAD IMAGES FOR LOCAL ANALYSIS. USES VISION MODELS.",
        fg=text_fg,
        bg=panel_bg,
        justify="left",
        wraplength=320,
        font=("Segoe UI", 8, "bold"),
    ).pack(fill="x", anchor="w", pady=(2, 6))

    tk.Label(
        image_inner,
        text=(
            "LIGHT: 8 GB+ RAM. MEDIUM: 16 GB+ RAM. HIGH: 64 GB+ RAM / STRONG GPU PREFERRED."
        ),
        fg=text_fg,
        bg=panel_bg,
        justify="left",
        wraplength=320,
        font=("Segoe UI", 8, "bold"),
    ).pack(fill="x", anchor="w", pady=(3, 7))

    for option_index in (6, 7, 8):
        add_model_card(image_inner, option_index)

    settings = tk.Label(
        root,
        justify="left",
        text=(
            "Preset models: selected context, selected GPU offload, "
            f"model id {LOCAL_MODEL_IDENTIFIER}. Custom: uses an already loaded "
            "LM Studio model id."
        ),
        bg=root_bg,
        fg=muted_fg,
        padx=18,
        pady=6,
        font=("Segoe UI", 8),
    )
    settings.pack(anchor="w")

    buttons = tk.Frame(root, bg=root_bg, padx=18)
    buttons.pack(fill="x", pady=(4, 12))

    def start():
        option = MODEL_OPTIONS[choice.get()]

        if not check_model_password(root, option):
            return

        selected["option"] = option
        root.destroy()

    def cancel():
        root.destroy()

    start_button = tk.Button(
        buttons,
        text="Prepare model",
        command=start,
        width=14,
        bg="#111827",
        fg=text_fg,
        activebackground="#0f172a",
        activeforeground=text_fg,
    )
    start_button.pack(side="right", padx=(8, 0))

    cancel_button = tk.Button(
        buttons,
        text="Cancel",
        command=cancel,
        width=10,
        bg="#111827",
        fg=text_fg,
        activebackground="#0f172a",
        activeforeground=text_fg,
    )
    cancel_button.pack(side="right")

    root.update_idletasks()
    width = min(max(root.winfo_width(), 1120), root.winfo_screenwidth() - 60)
    height = min(root.winfo_height(), root.winfo_screenheight() - 80)
    x = max((root.winfo_screenwidth() - width) // 2, 0)
    y = max((root.winfo_screenheight() - height) // 2, 0)
    root.geometry(f"{width}x{height}+{x}+{y}")
    lift_window_over_splash(root)

    if parent is not None:
        root.wait_window()
    else:
        root.mainloop()

    return selected["option"]


def find_lm_studio_app():
    possible_paths = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = os.environ.get("PROGRAMFILES")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)")

    if local_app_data:
        possible_paths.append(
            os.path.join(local_app_data, "Programs", "LM Studio", "LM Studio.exe")
        )

    if program_files:
        possible_paths.append(os.path.join(program_files, "LM Studio", "LM Studio.exe"))

    if program_files_x86:
        possible_paths.append(
            os.path.join(program_files_x86, "LM Studio", "LM Studio.exe")
        )

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


def find_lms_command():
    command = shutil.which("lms") or shutil.which("lms.exe")

    if command:
        return command

    bundled_path = Path.home() / ".lmstudio" / "bin" / "lms.exe"

    if bundled_path.exists():
        return str(bundled_path)

    return None


def command_text(command):
    return subprocess.list2cmdline(command)


def hidden_subprocess_kwargs():
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    return {
        "startupinfo": startupinfo,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }


def run_command(command, check=True):
    print()
    print("Running:")
    print(command_text(command))
    refresh_setup_splash()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        text=True,
        **hidden_subprocess_kwargs(),
    )

    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            refresh_setup_splash()

    result = subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    refresh_setup_splash()

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}:\n"
            f"{command_text(command)}\n\n{result.stderr or result.stdout}"
        )

    return result


def run_lms(lms_command, args, check=True):
    return run_command([lms_command, *args], check=check)


def run_command_with_progress(command, title, message, check=True):
    output_queue = queue.Queue()
    process_done = threading.Event()
    result = {"returncode": None, "output": ""}

    def worker():
        output_lines = []

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                text=True,
                **hidden_subprocess_kwargs(),
            )

            for line in process.stdout or []:
                output_lines.append(line)
                output_queue.put(line)

            result["returncode"] = process.wait()
            result["output"] = "".join(output_lines)
        except Exception as error:
            result["returncode"] = 1
            result["output"] = str(error)
            output_queue.put(str(error))
        finally:
            process_done.set()

    print()
    print("Running:")
    print(command_text(command))

    root = create_setup_window(title)
    root.resizable(False, False)
    lift_window_over_splash(root)

    tk.Label(
        root,
        text=message,
        justify="left",
        padx=16,
        wraplength=520,
    ).pack(anchor="w", pady=(14, 8))

    status_var = tk.StringVar(value="Starting...")
    status_label = tk.Label(root, textvariable=status_var, padx=16)
    status_label.pack(anchor="w", pady=(0, 6))

    progress = ttk.Progressbar(root, mode="indeterminate", length=520)
    progress.pack(padx=16, pady=(0, 10))
    progress.start(12)

    log_box = tk.Text(root, width=72, height=10, wrap="word")
    log_box.pack(padx=16, pady=(0, 14))
    log_box.insert("end", command_text(command) + "\n\n")
    log_box.configure(state="disabled")

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    found_percent = False

    while not process_done.is_set() or not output_queue.empty():
        try:
            line = output_queue.get(timeout=0.1)
        except queue.Empty:
            refresh_setup_splash()
            root.update()
            continue

        print(line.rstrip())
        refresh_setup_splash()
        status_var.set(line.strip() or "Working...")

        percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)

        if percent_match:
            percent = max(0, min(100, float(percent_match.group(1))))

            if not found_percent:
                progress.stop()
                progress.configure(mode="determinate", maximum=100, value=0)
                found_percent = True

            progress["value"] = percent
            status_var.set(f"Downloading... {percent:g}%")

        log_box.configure(state="normal")
        log_box.insert("end", line)
        log_box.see("end")
        log_box.configure(state="disabled")
        root.update()

    if not found_percent:
        progress.stop()
        progress.configure(mode="determinate", maximum=100, value=100)
    else:
        progress["value"] = 100

    status_var.set("Complete" if result["returncode"] == 0 else "Failed")
    root.update()

    close_at = time.monotonic() + 0.9

    while time.monotonic() < close_at:
        refresh_setup_splash()

        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            break

        time.sleep(0.05)

    try:
        root.destroy()
    except tk.TclError:
        pass

    completed = subprocess.CompletedProcess(
        command,
        result["returncode"],
        stdout=result["output"],
        stderr="",
    )

    if check and completed.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}:\n"
            f"{command_text(command)}\n\n{completed.stdout}"
        )

    return completed


def run_lms_with_progress(lms_command, args, title, message, check=True):
    return run_command_with_progress(
        [lms_command, *args],
        title=title,
        message=message,
        check=check,
    )


def parse_json_output(text):
    stripped = (text or "").strip()

    for start in (0, stripped.find("{"), stripped.find("[")):
        if start < 0:
            continue

        try:
            return json.loads(stripped[start:])
        except json.JSONDecodeError:
            continue

    return None


def iter_dicts(value):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def collect_strings(value):
    strings = []

    if isinstance(value, dict):
        for child in value.values():
            strings.extend(collect_strings(child))
    elif isinstance(value, list):
        for child in value:
            strings.extend(collect_strings(child))
    elif isinstance(value, str):
        strings.append(value)

    return strings


def model_key_from_entry(entry):
    preferred_keys = [
        "modelKey",
        "model_key",
        "key",
        "path",
        "identifier",
        "name",
        "displayName",
    ]

    for key in preferred_keys:
        value = entry.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    strings = collect_strings(entry)
    return strings[0].strip() if strings else None


def find_downloaded_model_key(lms_command, option):
    set_setup_splash_status(f"Checking for {option['model_name']}...")
    result = run_lms(lms_command, ["ls", "--json"], check=False)
    text = f"{result.stdout}\n{result.stderr}"
    data = parse_json_output(text)
    terms = [term.lower() for term in option["match_terms"]]

    if data is not None:
        for entry in iter_dicts(data):
            blob = " ".join(collect_strings(entry)).lower()

            if any(term in blob for term in terms):
                model_key = model_key_from_entry(entry)

                if model_key:
                    return model_key

    result = run_lms(lms_command, ["ls"], check=False)
    text = f"{result.stdout}\n{result.stderr}".lower()

    if any(term in text for term in terms):
        return option["download_query"]

    return None


def get_model_statuses(lms_command):
    statuses = {}

    for option in MODEL_OPTIONS:
        if option.get("custom_loaded_model"):
            continue

        statuses[option["model_name"]] = find_downloaded_model_key(
            lms_command,
            option,
        )

    return statuses


def ensure_model_downloaded(lms_command, option):
    set_setup_splash_status(f"Preparing {option['model_name']}...")
    model_key = find_downloaded_model_key(lms_command, option)

    if model_key:
        print(f"Model appears to be downloaded: {model_key}")
        set_setup_splash_status(f"Found {option['model_name']}.")
        return model_key

    set_setup_splash_status("Waiting for download choice...")
    confirmed = ask_yes_no(
        "Download model?",
        (
            f"MiddAI could not find {option['model_name']} in LM Studio.\n\n"
            f"Estimated download size: {model_download_size_label(option)}.\n\n"
            "Do you want LM Studio to download it now?\n\n"
            "This may be several GB and may take a while."
        ),
    )

    if not confirmed:
        raise RuntimeError("User cancelled model download.")

    if not confirm_extreme_model_requirements(option):
        raise RuntimeError("User cancelled extreme model warning.")

    set_setup_splash_status(f"Downloading {option['model_name']}...")
    run_lms_with_progress(
        lms_command,
        ["get", option["download_query"], "--gguf", "--yes"],
        title="MiddAI Model Download",
        message=(
            f"Downloading {option['model_name']} with LM Studio.\n\n"
            "This can take a while. Leave this window open."
        ),
        check=True,
    )

    model_key = find_downloaded_model_key(lms_command, option)

    if model_key:
        return model_key

    return option["download_query"]


def server_status_reports_running(status_text):
    text = (status_text or "").lower()

    stopped_markers = [
        "not running",
        "is not running",
        "server is stopped",
        "stopped",
        "offline",
    ]

    if any(marker in text for marker in stopped_markers):
        return False

    return bool(re.search(r"\b(running|listening|started)\b", text))


def lm_studio_api_url(path):
    return f"http://127.0.0.1:{LM_STUDIO_API_PORT}/v1{path}"


def is_lm_studio_api_reachable():
    try:
        request = urllib.request.Request(lm_studio_api_url("/models"))

        with urllib.request.urlopen(request, timeout=2):
            return True
    except (OSError, urllib.error.URLError):
        return False


def get_loaded_lm_studio_model_ids():
    request = urllib.request.Request(lm_studio_api_url("/models"))

    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))

    data = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = []

    for entry in data:
        if not isinstance(entry, dict):
            continue

        model_id = str(entry.get("id") or entry.get("model") or "").strip()

        if model_id and model_id not in model_ids:
            model_ids.append(model_id)

    return model_ids


def choose_loaded_lm_studio_model_id(model_ids):
    if not model_ids:
        raise RuntimeError(
            "No loaded LM Studio model was found.\n\n"
            "Open LM Studio, load a model, make sure the local server is running, "
            "then choose the Custom option again."
        )

    if len(model_ids) == 1:
        return model_ids[0]

    selected = {"model_id": None}
    parent = setup_parent_window()
    root = create_setup_window("Choose loaded model")
    root.resizable(False, False)
    root.configure(bg="#0b1117")
    lift_window_over_splash(root)

    choice = tk.StringVar(value=model_ids[0])

    frame = tk.Frame(root, bg="#0b1117", padx=18, pady=16)
    frame.pack(fill="both", expand=True)

    tk.Label(
        frame,
        text="Choose the loaded LM Studio model MiddAI should use",
        justify="left",
        bg="#0b1117",
        fg="#e5e7eb",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    tk.Label(
        frame,
        text=(
            "MiddAI will not download, unload, or change settings for this model. "
            "It will only use the selected model id when sending chat requests."
        ),
        justify="left",
        bg="#0b1117",
        fg="#94a3b8",
        wraplength=520,
        pady=10,
    ).pack(anchor="w")

    for model_id in model_ids:
        tk.Radiobutton(
            frame,
            variable=choice,
            value=model_id,
            text=model_id,
            anchor="w",
            justify="left",
            wraplength=520,
            bg="#0b1117",
            fg="#e5e7eb",
            activebackground="#0b1117",
            activeforeground="#e5e7eb",
            selectcolor="#111827",
        ).pack(fill="x", anchor="w", pady=2)

    buttons = tk.Frame(frame, bg="#0b1117")
    buttons.pack(fill="x", pady=(12, 0))

    def accept():
        selected["model_id"] = choice.get()
        root.destroy()

    def cancel():
        root.destroy()

    tk.Button(
        buttons,
        text="Use model",
        command=accept,
        width=12,
        bg="#111827",
        fg="#e5e7eb",
        activebackground="#0f172a",
        activeforeground="#e5e7eb",
    ).pack(side="right", padx=(8, 0))

    tk.Button(
        buttons,
        text="Cancel",
        command=cancel,
        width=10,
        bg="#111827",
        fg="#e5e7eb",
        activebackground="#0f172a",
        activeforeground="#e5e7eb",
    ).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.update_idletasks()
    width = min(max(root.winfo_width(), 580), root.winfo_screenwidth() - 60)
    height = min(root.winfo_height(), root.winfo_screenheight() - 80)
    x = max((root.winfo_screenwidth() - width) // 2, 0)
    y = max((root.winfo_screenheight() - height) // 2, 0)
    root.geometry(f"{width}x{height}+{x}+{y}")
    lift_window_over_splash(root)

    if parent is not None:
        root.wait_window()
    else:
        root.mainloop()

    if not selected["model_id"]:
        raise RuntimeError("User cancelled custom loaded model selection.")

    return selected["model_id"]


def is_local_model_loaded():
    try:
        request = urllib.request.Request(lm_studio_api_url("/models"))

        with urllib.request.urlopen(request, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace").lower()

        return LOCAL_MODEL_IDENTIFIER.lower() in body
    except (OSError, urllib.error.URLError):
        return False


def active_model_matches_option(active_model, option):
    if not active_model:
        return False

    option_model_name = str(option.get("model_name", "")).casefold()
    option_label = str(option.get("label", "")).casefold()
    active_model_name = str(active_model.get("model_name", "")).casefold()
    active_label = str(active_model.get("label", "")).casefold()

    model_name_matches = option_model_name and option_model_name == active_model_name
    label_matches = option_label and option_label == active_label
    return bool(model_name_matches or label_matches)


def loaded_model_action(option):
    if not is_local_model_loaded():
        return "load"

    if active_model_matches_option(read_active_model(), option):
        set_setup_splash_status(f"{option['model_name']} is already loaded.")
        return "reuse"

    set_setup_splash_status("Waiting for model switch choice...")
    confirmed = ask_yes_no(
        "Switch loaded model?",
        (
            "LM Studio already has a model loaded as 'local-model'.\n\n"
            f"You selected:\n{option['model_name']}\n\n"
            "Do you want MiddAI to unload the current model and load the "
            "selected model instead?\n\n"
            "Choose No to keep the currently loaded model."
        ),
    )

    return "load" if confirmed else "keep_current"


def wait_for_lm_studio_server(timeout_seconds=25):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        refresh_setup_splash()

        if is_lm_studio_api_reachable():
            return True

        time.sleep(1)

    return False


def start_lm_studio_server(lms_command):
    set_setup_splash_status("Checking LM Studio server...")
    status = run_lms(lms_command, ["server", "status"], check=False)
    status_text = f"{status.stdout}\n{status.stderr}".lower()

    if status.returncode == 0 and server_status_reports_running(status_text):
        if wait_for_lm_studio_server(timeout_seconds=5):
            print("LM Studio server already appears to be running.")
            return

        print(
            "LM Studio reports a running server, but the API is not reachable "
            f"on port {LM_STUDIO_API_PORT}. Trying to start it on the expected port."
        )

    run_lms(
        lms_command,
        ["server", "start", "--port", str(LM_STUDIO_API_PORT)],
        check=True,
    )

    if not wait_for_lm_studio_server():
        raise RuntimeError(
            "LM Studio server start finished, but the API did not become "
            f"reachable at {lm_studio_api_url('/models')}."
        )


def command_failure_message(command, result):
    return (
        f"Command failed with exit code {result.returncode}:\n"
        f"{command_text(command)}\n\n{result.stderr or result.stdout}"
    )


def is_identifier_conflict(result):
    text = f"{result.stdout}\n{result.stderr}".lower()
    return "identifier" in text and "already exists" in text


def wait_after_unload(seconds=1.5):
    deadline = time.time() + seconds

    while time.time() < deadline:
        refresh_setup_splash()
        time.sleep(0.1)


def unload_local_model_identifier(lms_command):
    set_setup_splash_status("Clearing old local-model slot...")
    run_lms(lms_command, ["unload", LOCAL_MODEL_IDENTIFIER], check=False)
    wait_after_unload()


def run_load_with_retry(lms_command, load_args):
    command = [lms_command, *load_args]
    result = run_lms(lms_command, load_args, check=False)

    if result.returncode == 0:
        return

    if not is_identifier_conflict(result):
        raise RuntimeError(command_failure_message(command, result))

    print("The local-model identifier already exists. Retrying after unload.")

    for attempt in range(1, 4):
        set_setup_splash_status(f"Reloading local-model slot ({attempt}/3)...")
        unload_local_model_identifier(lms_command)
        result = run_lms(lms_command, load_args, check=False)

        if result.returncode == 0:
            return

        if not is_identifier_conflict(result):
            raise RuntimeError(command_failure_message(command, result))

    raise RuntimeError(command_failure_message(command, result))


def load_model(lms_command, model_key, option=None):
    label = (option or {}).get("model_name") or model_key
    set_setup_splash_status(f"Loading {label}...")
    unload_local_model_identifier(lms_command)
    context_length = get_context_length(option or {})
    gpu_offload = get_gpu_offload(option or {})

    load_args = [
        "load",
        model_key,
        "--identifier",
        LOCAL_MODEL_IDENTIFIER,
        "--context-length",
        str(context_length),
        "--gpu",
        gpu_offload,
        "--yes",
    ]

    run_load_with_retry(lms_command, load_args)


def main():
    lms_command = find_lms_command()
    lm_studio_app = find_lm_studio_app()

    if not lms_command:
        show_lm_studio_required(lm_studio_app)
        return 1

    show_setup_splash()

    try:
        run_lms(lms_command, ["--help"], check=True)
        model_statuses = get_model_statuses(lms_command)
    except Exception as error:
        close_setup_splash()
        show_error("LM Studio not ready", str(error))
        return 1

    option = choose_model(model_statuses)

    if option is None:
        close_setup_splash()
        print("Setup cancelled.")
        return 1

    completion_model_text = (
        f"The selected model is loaded as '{LOCAL_MODEL_IDENTIFIER}'."
    )

    try:
        start_lm_studio_server(lms_command)

        if option.get("custom_loaded_model"):
            loaded_model_ids = get_loaded_lm_studio_model_ids()
            chat_model_id = choose_loaded_lm_studio_model_id(loaded_model_ids)
            save_active_model(option, chat_model_id, chat_model_id=chat_model_id)
            completion_model_text = (
                f"MiddAI will use the loaded LM Studio model '{chat_model_id}'."
            )
        else:
            action = loaded_model_action(option)

            if action == "load":
                model_key = ensure_model_downloaded(lms_command, option)
                load_model(lms_command, model_key, option)
                save_active_model(option, model_key)
            elif action == "reuse":
                print(f"Selected model is already loaded: {option['model_name']}")
            else:
                print("Keeping the currently loaded local-model.")
                completion_model_text = (
                    f"MiddAI kept the currently loaded '{LOCAL_MODEL_IDENTIFIER}' model."
                )
    except Exception as error:
        close_setup_splash()
        show_error("MiddAI setup failed", str(error))
        return 1

    close_setup_splash()

    show_info(
        "MiddAI first step complete",
        (
            f"LM Studio should now be running on port {LM_STUDIO_API_PORT}.\n"
            f"{completion_model_text}\n\n"
            "Now run MiddAI_open_last.bat to open the chat."
        ),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
