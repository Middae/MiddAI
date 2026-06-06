from pathlib import Path
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


ROOT_DIR = Path(__file__).resolve().parent
CHAT_DIR = ROOT_DIR / "chat_program"
SETUP_DIR = ROOT_DIR / "lmstudio_setup"

sys.path.insert(0, str(CHAT_DIR))
sys.path.insert(0, str(SETUP_DIR))

from config import APP_DEBUG, APP_HOST, APP_PORT, LM_STUDIO_BASE_URL, LM_STUDIO_MODEL
from setup_lmstudio import (
    choose_model,
    close_setup_splash,
    ensure_model_downloaded,
    find_lm_studio_app,
    find_lms_command,
    get_model_statuses,
    loaded_model_action,
    load_model,
    refresh_setup_splash,
    run_lms,
    save_active_model,
    set_setup_splash_status,
    show_error,
    show_setup_splash,
    show_info,
    show_lm_studio_required,
    start_lm_studio_server,
)
from chat import app
from search_tools import extract_evidence, search_images, search_web


def hidden_subprocess_kwargs():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}

    return {}


def self_test():
    print("MiddAI self-test")
    print(f"Chat app import: OK")
    print(f"LM Studio API URL: {LM_STUDIO_BASE_URL}")
    print(f"Expected model id: {LM_STUDIO_MODEL}")
    print(f"Chat URL: http://{APP_HOST}:{APP_PORT}")
    print("Self-test complete.")
    return 0


def search_self_test():
    question = "can dogs look up?"

    print("MiddAI search self-test")
    print(f"Question: {question}")

    try:
        results = search_web(question, "balanced")
        print(f"Search results: {len(results)}")
        evidence = extract_evidence(question, results, "balanced")
        images = search_images(question)
    except Exception as error:
        print(f"Search self-test failed: {error}")
        return 1

    print(f"Evidence sources: {len(evidence)}")
    print(f"Image results: {len(images)}")

    for source in evidence:
        print(f"- {source['url']} ({len(source['text'])} chars)")

    if not evidence:
        print("Search self-test failed: no readable evidence.")
        return 1

    if len(images) < 3:
        print("Search self-test failed: fewer than 3 usable image results.")
        return 1

    print("Search self-test complete.")
    return 0


def api_url(path):
    base_url = LM_STUDIO_BASE_URL.rstrip("/")

    if base_url.endswith("/v1"):
        return f"{base_url}{path}"

    return f"{base_url}/v1{path}"


def is_local_model_ready():
    try:
        request = urllib.request.Request(api_url("/models"))

        with urllib.request.urlopen(request, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace").lower()

        return LM_STUDIO_MODEL.lower() in body
    except (OSError, urllib.error.URLError):
        return False


def wait_for_local_model(timeout_seconds=120):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        refresh_setup_splash()

        if is_local_model_ready():
            return True

        time.sleep(1)

    return False


def chat_health_url():
    return f"http://{APP_HOST}:{APP_PORT}/api/health"


def is_chat_server_ready():
    try:
        request = urllib.request.Request(chat_health_url())

        with urllib.request.urlopen(request, timeout=1.5) as response:
            body = response.read().decode("utf-8", errors="replace").lower()

        return '"app":"middai"' in body.replace(" ", "") or '"app": "middai"' in body
    except (OSError, urllib.error.URLError):
        return False


def wait_for_chat_server(timeout_seconds=15):
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        refresh_setup_splash()

        if is_chat_server_ready():
            return True

        time.sleep(0.2)

    return False


def port_owner_pids(port):
    if os.name != "nt":
        return []

    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=8,
            **hidden_subprocess_kwargs(),
        )
    except Exception:
        return []

    pids = []

    for line in result.stdout.splitlines():
        parts = line.split()

        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue

        local_address = parts[1]
        state = parts[-2].upper()
        pid_text = parts[-1]

        if state != "LISTENING":
            continue

        if not (
            local_address.endswith(f":{port}")
            or local_address.endswith(f".{port}")
            or local_address.endswith(f"]:{port}")
        ):
            continue

        try:
            pid = int(pid_text)
        except ValueError:
            continue

        if pid not in pids:
            pids.append(pid)

    return pids


def process_command_line(pid):
    if os.name != "nt":
        return ""

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "$process = Get-CimInstance Win32_Process "
            f"-Filter \"ProcessId={int(pid)}\"; "
            "if ($process) { $process.CommandLine }"
        ),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=8,
            **hidden_subprocess_kwargs(),
        )
    except Exception:
        return ""

    return f"{result.stdout}\n{result.stderr}".strip()


def is_stale_middai_server_process(command_line):
    normalized = (command_line or "").lower()

    if not normalized:
        return False

    has_middai_context = (
        "middai" in normalized
        or "chat.py" in normalized
        or "ai internet search" in normalized
    )
    has_chat_server_context = (
        "middai.exe" in normalized
        or "middai_launcher" in normalized
        or "chat.py" in normalized
        or "chat_program" in normalized
    )

    return has_middai_context and has_chat_server_context


def stop_stale_chat_servers():
    current_pid = os.getpid()

    for pid in port_owner_pids(APP_PORT):
        if pid == current_pid:
            continue

        command_line = process_command_line(pid)

        if not is_stale_middai_server_process(command_line):
            continue

        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
                timeout=10,
                **hidden_subprocess_kwargs(),
            )
        except Exception:
            continue

    deadline = time.time() + 5

    while time.time() < deadline:
        remaining = [
            pid for pid in port_owner_pids(APP_PORT) if pid != current_pid
        ]

        if not remaining:
            return True

        time.sleep(0.2)

    return not any(pid != current_pid for pid in port_owner_pids(APP_PORT))


def prepare_lm_studio():
    lms_command = find_lms_command()
    lm_studio_app = find_lm_studio_app()

    if not lms_command:
        show_lm_studio_required(lm_studio_app)
        return False

    try:
        show_setup_splash()
        set_setup_splash_status("Checking LM Studio...")
        run_lms(lms_command, ["--help"], check=True)
        set_setup_splash_status("Checking downloaded models...")
        model_statuses = get_model_statuses(lms_command)
    except Exception as error:
        close_setup_splash()
        show_error("LM Studio not ready", str(error))
        return False

    option = choose_model(model_statuses)

    if option is None:
        close_setup_splash()
        print("Setup cancelled.")
        return False

    action = "load"

    try:
        set_setup_splash_status(f"Preparing {option['model_name']}...")
        start_lm_studio_server(lms_command)
        action = loaded_model_action(option)

        if action == "load":
            model_key = ensure_model_downloaded(lms_command, option)
            load_model(lms_command, model_key, option)
            save_active_model(option, model_key)
        elif action == "reuse":
            print(f"Selected model is already loaded: {option['model_name']}")
        else:
            print("Keeping the currently loaded local-model.")
    except Exception as error:
        close_setup_splash()
        show_error("MiddAI setup failed", str(error))
        return False

    if not wait_for_local_model():
        close_setup_splash()
        show_error(
            "LM Studio not ready",
            (
                "MiddAI loaded the model, but LM Studio did not report "
                "local-model as ready in time. The model may still be loading "
                "or the LM Studio server may not be reachable. Try opening LM "
                "Studio, checking the server, then running MiddAI again."
            ),
        )
        return False

    set_setup_splash_status("Opening MiddAI chat...")

    notes = []

    if action == "reuse":
        notes.append("Selected model was already loaded. MiddAI reused it.")

    if action == "keep_current":
        notes.append("MiddAI kept the currently loaded model and did not switch.")

    if notes:
        show_info(
            "LM Studio prepared",
            "LM Studio is ready. MiddAI will open now.\n\n" + "\n\n".join(notes),
        )

    return True


def wait_with_splash(seconds):
    deadline = time.time() + seconds

    while time.time() < deadline:
        refresh_setup_splash()
        time.sleep(0.1)


def open_chat_window():
    wait_with_splash(2)
    url = f"http://{APP_HOST}:{APP_PORT}"

    if open_app_window(url):
        return

    webbrowser.open(url)


def open_app_window(url):
    width, height = primary_screen_size()

    for browser_path in candidate_app_browsers():
        if browser_path.exists():
            subprocess.Popen(
                [
                    str(browser_path),
                    f"--app={url}",
                    "--new-window",
                    "--start-maximized",
                    "--start-fullscreen",
                    "--window-position=0,0",
                    f"--window-size={width},{height}",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

    return False


def primary_screen_size():
    if os.name == "nt":
        try:
            import ctypes

            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

            width = int(ctypes.windll.user32.GetSystemMetrics(0))
            height = int(ctypes.windll.user32.GetSystemMetrics(1))

            if width > 0 and height > 0:
                return width, height
        except Exception:
            pass

    return 1920, 1080


def candidate_app_browsers():
    program_files = [
        Path(os.environ.get("PROGRAMFILES", "")),
        Path(os.environ.get("PROGRAMFILES(X86)", "")),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
    ]
    browser_parts = [
        ("Microsoft", "Edge", "Application", "msedge.exe"),
        ("Google", "Chrome", "Application", "chrome.exe"),
    ]

    for base_path in program_files:
        if not str(base_path):
            continue

        for parts in browser_parts:
            yield base_path.joinpath(*parts)


def main():
    if "--self-test" in sys.argv:
        return self_test()

    if "--search-self-test" in sys.argv:
        return search_self_test()

    if not prepare_lm_studio():
        return 1

    set_setup_splash_status("Starting MiddAI chat server...")
    stop_stale_chat_servers()
    server_errors = []

    def run_chat_server():
        try:
            app.run(
                host=APP_HOST,
                port=APP_PORT,
                debug=APP_DEBUG,
                use_reloader=False,
            )
        except Exception as error:
            server_errors.append(error)

    server_thread = threading.Thread(
        target=run_chat_server,
        daemon=True,
    )
    server_thread.start()

    if not wait_for_chat_server():
        close_setup_splash()

        if server_errors:
            detail = str(server_errors[-1])
        else:
            detail = (
                f"MiddAI could not start its chat server at "
                f"http://{APP_HOST}:{APP_PORT}. Close other MiddAI windows and try again."
            )

        show_error("MiddAI chat failed", detail)
        return 1

    open_chat_window()
    close_setup_splash()
    server_thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
