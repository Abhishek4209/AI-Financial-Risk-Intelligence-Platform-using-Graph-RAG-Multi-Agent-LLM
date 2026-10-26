"""Run local Docker Compose operations with configuration and API preflight checks."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def compose_command(arguments):
    return ["docker", "compose", "-f", str(ROOT / "docker-compose.yml")] + arguments
def preflight(require_api):
    problems = []
    if shutil.which("docker") is None:
        problems.append("Docker CLI is not installed or not on PATH")
    if not (ROOT / "docker-compose.yml").is_file():
        problems.append("docker-compose.yml is missing")
    if not (ROOT / ".env").is_file():
        problems.append(".env is missing; copy .env.example and set local credentials")
    if require_api:
        entrypoint = ROOT / "src" / "main.py"
        if not entrypoint.is_file() or not entrypoint.read_text(encoding="utf-8").strip():
            problems.append("src/main.py does not yet export the FastAPI application; backend startup is in
complete")
    return problems
def _report_issues(title, issues):
    if not issues:
        return False
    print(title, file=sys.stderr)
    for issue in issues:
        print("- " + issue, file=sys.stderr)
    return True
def _run_check():
    if _report_issues("Preflight issues:", preflight(require_api=False)):
        return 1
    result = subprocess.run(compose_command(["config", "--quiet"]), cwd=ROOT, check=False)
    if result.returncode == 0:
        print("Docker Compose configuration is valid.")
    return result.returncode
def _run_up(args):
    issues = preflight(require_api=not args.allow_incomplete_backend)
    if _report_issues("Cannot start the full stack:", issues):
        return 1
    command = ["up"]
    if args.build:
        command.append("--build")
    if not args.foreground:
        command.append("--detach")
    return subprocess.run(compose_command(command), cwd=ROOT, check=False).returncode
def _run_action(args):
    if args.action == "check":
        return _run_check()
    if args.action == "up":
        return _run_up(args)
    commands = {"down": ["down"], "status": ["ps"], "logs": ["logs"]}
    command = list(commands[args.action])
    if args.action == "logs" and args.follow:
        command.append("--follow")
    return subprocess.run(compose_command(command), cwd=ROOT, check=False).returncode
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "up", "down", "status", "logs"])
    parser.add_argument("--build", action="store_true", help="Build the backend image when starting service
s")
    parser.add_argument("--foreground", action="store_true", help="Keep Compose attached while starting")
    parser.add_argument("--follow", action="store_true", help="Follow logs")
    parser.add_argument("--allow-incomplete-backend", action="store_true", help="Do not block on the known 
empty API entry point")
    return _run_action(parser.parse_args())
if __name__ == "__main__":
    raise SystemExit(main())
