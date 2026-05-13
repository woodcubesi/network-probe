#!/usr/bin/env python3
"""
Windows service host for Network Probe.

Examples:
    python service.py debug --port 8081
    python service.py install --startup auto --host 127.0.0.1 --port 8081
    python service.py start
    python service.py stop
    python service.py uninstall
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app import TcpingHandler


SERVICE_NAME = "NetworkProbe"
DISPLAY_NAME = "Network Probe"
DESCRIPTION = "Network Probe web application for TCP, UDP and ICMP tests."
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8081

SERVICE_STOPPED = 0x00000001
SERVICE_START_PENDING = 0x00000002
SERVICE_STOP_PENDING = 0x00000003
SERVICE_RUNNING = 0x00000004
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_ACCEPT_SHUTDOWN = 0x00000004
SERVICE_CONTROL_STOP = 0x00000001
SERVICE_CONTROL_SHUTDOWN = 0x00000005
SERVICE_WIN32_OWN_PROCESS = 0x00000010
NO_ERROR = 0

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.environ.get("ProgramData", str(BASE_DIR))) / "NetworkProbe"
LOG_FILE = LOG_DIR / "networkprobe-service.log"


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", ctypes.c_ulong),
        ("dwCurrentState", ctypes.c_ulong),
        ("dwControlsAccepted", ctypes.c_ulong),
        ("dwWin32ExitCode", ctypes.c_ulong),
        ("dwServiceSpecificExitCode", ctypes.c_ulong),
        ("dwCheckPoint", ctypes.c_ulong),
        ("dwWaitHint", ctypes.c_ulong),
    ]


HandlerEx = ctypes.WINFUNCTYPE(
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_void_p,
    ctypes.c_void_p,
)
ServiceMain = ctypes.WINFUNCTYPE(None, ctypes.c_ulong, ctypes.POINTER(ctypes.c_wchar_p))


class SERVICE_TABLE_ENTRY(ctypes.Structure):
    _fields_ = [
        ("lpServiceName", ctypes.c_wchar_p),
        ("lpServiceProc", ServiceMain),
    ]


advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
advapi32.StartServiceCtrlDispatcherW.argtypes = [ctypes.POINTER(SERVICE_TABLE_ENTRY)]
advapi32.StartServiceCtrlDispatcherW.restype = wintypes.BOOL
advapi32.RegisterServiceCtrlHandlerExW.argtypes = [wintypes.LPCWSTR, HandlerEx, wintypes.LPVOID]
advapi32.RegisterServiceCtrlHandlerExW.restype = wintypes.HANDLE
advapi32.SetServiceStatus.argtypes = [wintypes.HANDLE, ctypes.POINTER(SERVICE_STATUS)]
advapi32.SetServiceStatus.restype = wintypes.BOOL
_service_status_handle = None
_status = SERVICE_STATUS()
_stop_event = threading.Event()
_server: ThreadingHTTPServer | None = None
_service_main_ref = None
_handler_ref = None


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    for log_dir in (LOG_DIR, BASE_DIR / "logs"):
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / LOG_FILE.name).open("a", encoding="utf-8") as handle:
                handle.write(line)
            return
        except OSError:
            continue


def raise_last_error(context: str) -> None:
    error = ctypes.get_last_error()
    raise ctypes.WinError(error, context)


def report_status(state: int, exit_code: int = NO_ERROR, wait_hint: int = 0) -> None:
    if not _service_status_handle:
        return

    _status.dwServiceType = SERVICE_WIN32_OWN_PROCESS
    _status.dwCurrentState = state
    _status.dwControlsAccepted = 0 if state == SERVICE_START_PENDING else SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN
    _status.dwWin32ExitCode = exit_code
    _status.dwServiceSpecificExitCode = 0
    _status.dwCheckPoint = 0
    _status.dwWaitHint = wait_hint
    if not advapi32.SetServiceStatus(_service_status_handle, ctypes.byref(_status)):
        raise_last_error("SetServiceStatus")


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), TcpingHandler)
    server.quiet = True  # type: ignore[attr-defined]
    return server


def run_server(host: str, port: int) -> None:
    global _server
    _server = create_server(host, port)
    log(f"Network Probe listening on http://{host}:{port}")
    try:
        _server.serve_forever()
    finally:
        _server.server_close()
        log("Network Probe server stopped")


def stop_server() -> None:
    global _server
    _stop_event.set()
    if _server is not None:
        threading.Thread(target=_server.shutdown, daemon=True).start()


def service_handler(control: int, event_type: int, event_data: Any, context: Any) -> int:
    del event_type, event_data, context
    if control in {SERVICE_CONTROL_STOP, SERVICE_CONTROL_SHUTDOWN}:
        log("Stop requested by Service Control Manager")
        report_status(SERVICE_STOP_PENDING, wait_hint=5000)
        stop_server()
        return NO_ERROR
    return NO_ERROR


def make_service_main(service_name: str, host: str, port: int) -> ServiceMain:
    def service_main(argc: int, argv: ctypes.POINTER(ctypes.c_wchar_p)) -> None:
        del argc, argv
        global _service_status_handle, _handler_ref
        try:
            _handler_ref = HandlerEx(service_handler)
            _service_status_handle = advapi32.RegisterServiceCtrlHandlerExW(service_name, _handler_ref, None)
            if not _service_status_handle:
                raise_last_error("RegisterServiceCtrlHandlerExW")

            report_status(SERVICE_START_PENDING, wait_hint=5000)
            worker = threading.Thread(target=run_server, args=(host, port), daemon=True)
            worker.start()
            report_status(SERVICE_RUNNING)
            _stop_event.wait()
            worker.join(timeout=10)
            report_status(SERVICE_STOPPED)
        except Exception as exc:
            log(f"Service failed: {exc}")
            try:
                report_status(SERVICE_STOPPED, exit_code=1)
            except Exception:
                pass

    return ServiceMain(service_main)


def run_service(service_name: str, host: str, port: int) -> None:
    global _service_main_ref
    _service_main_ref = make_service_main(service_name, host, port)
    service_table = (SERVICE_TABLE_ENTRY * 2)()
    service_table[0].lpServiceName = service_name
    service_table[0].lpServiceProc = _service_main_ref

    if not advapi32.StartServiceCtrlDispatcherW(service_table):
        raise_last_error("StartServiceCtrlDispatcherW")


def run_debug(host: str, port: int) -> None:
    log(f"Debug run requested on http://{host}:{port}")
    try:
        run_server(host, port)
    except KeyboardInterrupt:
        stop_server()


def run_sc(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["sc.exe", *args], capture_output=True)
    completed.stdout = decode_process_output(completed.stdout)  # type: ignore[assignment]
    completed.stderr = decode_process_output(completed.stderr)  # type: ignore[assignment]
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(message or f"sc.exe failed with code {completed.returncode}")
    return completed


def decode_process_output(data: bytes) -> str:
    for encoding in ("utf-8", "cp850", "cp437", "mbcs"):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode(errors="replace").replace("\ufffd", "?")


def set_description(name: str, description: str) -> None:
    try:
        run_sc(["description", name, description])
    except RuntimeError as exc:
        log(f"Could not set service description: {exc}")


def install_service(args: argparse.Namespace) -> None:
    if getattr(sys, "frozen", False):
        service_exe = Path(sys.executable).resolve()
        bin_path = f'"{service_exe}" run --name {args.name} --host {args.host} --port {args.port}'
    else:
        python_exe = Path(args.python or sys.executable).resolve()
        script = Path(__file__).resolve()
        bin_path = f'"{python_exe}" "{script}" run --name {args.name} --host {args.host} --port {args.port}'
    startup = "auto" if args.startup == "auto" else "demand"

    run_sc(
        [
            "create",
            args.name,
            "binPath=",
            bin_path,
            "DisplayName=",
            args.display_name,
            "start=",
            startup,
        ]
    )
    set_description(args.name, DESCRIPTION)
    print(f"Servico instalado: {args.name}")


def uninstall_service(args: argparse.Namespace) -> None:
    try:
        run_sc(["stop", args.name])
        time.sleep(1)
    except RuntimeError:
        pass
    run_sc(["delete", args.name])
    print(f"Servico removido: {args.name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows service host for Network Probe.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="executa como servico pelo Windows SCM")
    run_parser.add_argument("--name", default=SERVICE_NAME)
    run_parser.add_argument("--host", default=DEFAULT_HOST)
    run_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    debug_parser = subparsers.add_parser("debug", help="executa em primeiro plano para teste")
    debug_parser.add_argument("--host", default=DEFAULT_HOST)
    debug_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    install_parser = subparsers.add_parser("install", help="instala o servico")
    install_parser.add_argument("--name", default=SERVICE_NAME)
    install_parser.add_argument("--display-name", default=DISPLAY_NAME)
    install_parser.add_argument("--startup", choices=["auto", "demand"], default="auto")
    install_parser.add_argument("--host", default=DEFAULT_HOST)
    install_parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    install_parser.add_argument("--python", default=None, help="python.exe que sera usado pelo servico")

    uninstall_parser = subparsers.add_parser("uninstall", help="remove o servico")
    uninstall_parser.add_argument("--name", default=SERVICE_NAME)

    start_parser = subparsers.add_parser("start", help="inicia o servico")
    start_parser.add_argument("--name", default=SERVICE_NAME)

    stop_parser = subparsers.add_parser("stop", help="para o servico")
    stop_parser.add_argument("--name", default=SERVICE_NAME)

    status_parser = subparsers.add_parser("status", help="mostra status do servico")
    status_parser.add_argument("--name", default=SERVICE_NAME)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "run":
        run_service(args.name, args.host, args.port)
        return 0
    if args.command == "debug":
        run_debug(args.host, args.port)
        return 0
    if args.command == "install":
        install_service(args)
        return 0
    if args.command == "uninstall":
        uninstall_service(args)
        return 0
    if args.command == "start":
        print(run_sc(["start", args.name]).stdout)
        return 0
    if args.command == "stop":
        print(run_sc(["stop", args.name]).stdout)
        return 0
    if args.command == "status":
        print(run_sc(["query", args.name]).stdout)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
