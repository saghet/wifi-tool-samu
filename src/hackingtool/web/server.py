import asyncio
import os
import platform
import re
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root to sys.path so hackingtool can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hackingtool import config
from hackingtool.constants import VERSION_DISPLAY, USER_CONFIG_DIR
from hackingtool.config import get_tools_dir
from hackingtool.tags import TAXONOMY
import hackingtool.ai_recommend as ai_recommend
import hackingtool.ai_command as ai_command
import hackingtool.engagement as engagement_mod
import hackingtool.findings as findings_mod
from hackingtool.cli import all_tools, tool_definitions
from hackingtool.web.package_adapter import adapt_install_command, detect_pkg_manager, detect_distro_family

app = FastAPI(
    title="HackingTool Web Suite",
    description="Interfaz web moderna y centro de control para la suite HackingTool",
    version=VERSION_DISPLAY,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", text.lower()).strip("_")
    return re.sub(r"_+", "_", cleaned) or "item"


def serialize_tool(tool: Any, category_title: str, cat_index: int) -> dict[str, Any]:
    cat_slug = slugify(category_title)
    tool_title = getattr(tool, "TITLE", "Unknown Tool")
    tool_slug = slugify(tool_title)
    tool_id = f"{cat_slug}__{tool_slug}"

    usage_list = []
    for item in getattr(tool, "USAGE", []) or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            usage_list.append({"task": item[0], "command": item[1]})

    options_list = []
    for opt in getattr(tool, "OPTIONS", []) or []:
        if isinstance(opt, (list, tuple)) and len(opt) >= 1:
            options_list.append(opt[0])

    raw_install_cmds = list(getattr(tool, "INSTALL_COMMANDS", []) or [])
    system_pkgs = getattr(tool, "SYSTEM_PKGS", {}) or {}

    # If no install commands exist but system_pkgs has apt/which, generate adapted install
    if not raw_install_cmds and system_pkgs:
        apt_pkg = system_pkgs.get("apt") or system_pkgs.get("which")
        if apt_pkg:
            raw_install_cmds = [f"sudo apt-get install -y {apt_pkg}"]

    # Adapt all install commands to host OS package manager (e.g. pacman on Arch)
    adapted_install_cmds = [adapt_install_command(cmd) for cmd in raw_install_cmds]

    raw_run_cmds = list(getattr(tool, "RUN_COMMANDS", []) or [])
    if not raw_run_cmds and usage_list:
        raw_run_cmds = [usage_list[0]["command"]]

    is_installed = bool(getattr(tool, "is_installed", False))
    # Secondary check: if which binary exists in PATH
    which_bin = system_pkgs.get("which")
    if which_bin and shutil.which(which_bin):
        is_installed = True

    return {
        "id": tool_id,
        "title": tool_title,
        "category_title": category_title,
        "category_slug": cat_slug,
        "category_index": cat_index,
        "description": getattr(tool, "DESCRIPTION", "") or "",
        "is_installed": is_installed,
        "kind": getattr(tool, "KIND", "install"),
        "tags": list(getattr(tool, "TAGS", []) or []),
        "project_url": getattr(tool, "PROJECT_URL", "") or "",
        "lab_safe_notes": getattr(tool, "LAB_SAFE_NOTES", "") or "",
        "install_commands": adapted_install_cmds,
        "run_commands": raw_run_cmds,
        "usage": usage_list,
        "options": options_list,
        "archived": bool(getattr(tool, "ARCHIVED", False)),
        "archived_reason": getattr(tool, "ARCHIVED_REASON", "") or "",
    }


def get_catalog_data():
    categories = []
    tools = []
    tags_count: dict[str, int] = {}

    for cat_idx, cat in enumerate(all_tools):
        cat_title = getattr(cat, "TITLE", "Other")
        cat_slug = slugify(cat_title)
        cat_desc = getattr(cat, "DESCRIPTION", "") or ""
        cat_tools_raw = getattr(cat, "TOOLS", []) or []

        icon = "🛠"
        menu_label = cat_title
        for item in tool_definitions:
            if len(item) >= 3 and item[0] == cat_title:
                icon = item[1].strip()
                menu_label = item[2]
                break

        installed_count = 0
        cat_serialized_tools = []
        for t in cat_tools_raw:
            s_tool = serialize_tool(t, cat_title, cat_idx)
            tools.append(s_tool)
            cat_serialized_tools.append(s_tool)
            if s_tool["is_installed"]:
                installed_count += 1
            for tag in s_tool["tags"]:
                tags_count[tag] = tags_count.get(tag, 0) + 1

        categories.append({
            "id": cat_slug,
            "index": cat_idx,
            "title": cat_title,
            "menu_label": menu_label,
            "icon": icon,
            "description": cat_desc,
            "total_tools": len(cat_tools_raw),
            "installed_tools": installed_count,
        })

    return categories, tools, tags_count


# ── REST API Models ────────────────────────────────────────────────────────────

class IntentRequest(BaseModel):
    intent: str


class ConfigUpdateRequest(BaseModel):
    theme: Optional[str] = None
    tools_dir: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_model: Optional[str] = None
    ai_key: Optional[str] = None


class EngagementCreateRequest(BaseModel):
    name: str
    targets: list[str] = []
    scope_in: list[str] = []
    scope_out: list[str] = []


class ManualFindingRequest(BaseModel):
    kind: str = "vulnerability"
    target: str
    name: str
    severity: str = "info"
    source_tool: str = "manual"
    details: dict[str, Any] = {}
    raw: str = ""


# ── REST Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/system")
def get_system_info():
    _cats, tools, _tags = get_catalog_data()
    installed = sum(1 for t in tools if t["is_installed"])

    cfg = config.load()
    ai_prov = cfg.get("ai_provider", "auto")
    ai_mdl = cfg.get("ai_model", "")
    has_key = bool(config.ai_key())

    return {
        "hostname": socket.gethostname(),
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_machine": platform.machine(),
        "pkg_manager": detect_pkg_manager(),
        "distro_family": detect_distro_family(),
        "python_version": platform.python_version(),
        "hackingtool_version": VERSION_DISPLAY,
        "total_categories": len(_cats),
        "total_tools": len(tools),
        "installed_tools": installed,
        "tools_dir": str(get_tools_dir()),
        "ai_provider": ai_prov,
        "ai_model": ai_mdl,
        "has_ai_key": has_key,
        "server_time": datetime.now().isoformat(),
    }


@app.get("/api/categories")
def get_categories():
    cats, _tools, _tags = get_catalog_data()
    return cats


@app.get("/api/tools")
def get_tools(category: Optional[str] = None, search: Optional[str] = None,
              tag: Optional[str] = None, installed_only: bool = False):
    _cats, tools, _tags = get_catalog_data()
    results = tools

    if category:
        category_lower = category.lower()
        results = [t for t in results if t["category_slug"] == category_lower or t["category_title"].lower() == category_lower]

    if tag:
        tag_lower = tag.lower()
        results = [t for t in results if tag_lower in [tg.lower() for tg in t["tags"]]]

    if installed_only:
        results = [t for t in results if t["is_installed"]]

    if search:
        q = search.lower().strip()
        filtered = []
        for t in results:
            match_score = 0
            if q in t["title"].lower():
                match_score += 5
            if q in t["description"].lower():
                match_score += 2
            if any(q in tg.lower() for tg in t["tags"]):
                match_score += 3
            if any(q in u["task"].lower() or q in u["command"].lower() for u in t["usage"]):
                match_score += 2
            if match_score > 0:
                filtered.append((match_score, t))
        filtered.sort(key=lambda x: -x[0])
        results = [x[1] for x in filtered]

    return results


@app.get("/api/tools/{tool_id}")
def get_tool_detail(tool_id: str):
    _cats, tools, _tags = get_catalog_data()
    for t in tools:
        if t["id"] == tool_id:
            return t
    raise HTTPException(status_code=404, detail="Tool not found")


@app.get("/api/tags")
def get_tags():
    _cats, _tools, tags_count = get_catalog_data()
    return [{"tag": t, "count": tags_count.get(t, 0)} for t in sorted(TAXONOMY)]


@app.post("/api/ai/recommend")
def recommend_tools(payload: IntentRequest):
    intent = payload.intent.strip()
    if not intent:
        return {"tags": [], "recommendations": []}

    picked_tags = ai_recommend.resolve(intent, TAXONOMY)
    _cats, all_tools_data, _tags = get_catalog_data()

    scored = []
    intent_words = set(re.findall(r"[a-z0-9]+", intent.lower()))

    for tool in all_tools_data:
        score = 0
        matching_tags = [t for t in tool["tags"] if t in picked_tags]
        score += len(matching_tags) * 4

        tool_words = set(re.findall(r"[a-z0-9]+", (tool["title"] + " " + tool["description"]).lower()))
        overlap = intent_words.intersection(tool_words)
        score += len(overlap) * 2

        if tool["is_installed"]:
            score += 1

        if score > 0:
            suggested_cmd = None
            if tool["usage"]:
                raw_usage = [(u["task"], u["command"]) for u in tool["usage"]]
                cmd_match = ai_command.build_command(tool["title"], raw_usage, intent)
                if cmd_match:
                    suggested_cmd = {
                        "source": cmd_match[0],
                        "command": cmd_match[1]
                    }

            scored.append({
                "score": score,
                "tool": tool,
                "matching_tags": matching_tags,
                "suggested_command": suggested_cmd,
            })

    scored.sort(key=lambda x: -x["score"])
    top = scored[:8]

    return {
        "intent": intent,
        "tags": picked_tags,
        "recommendations": top,
    }


# ── Engagements & Reports ──────────────────────────────────────────────────────

@app.get("/api/engagements")
def list_engagements():
    root = engagement_mod.ENGAGEMENTS_ROOT
    if not root.exists():
        return []

    result = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "engagement.json").exists():
            eng = engagement_mod.load(d.name)
            if eng:
                findings_file = eng.findings_file
                f_count = 0
                if findings_file.exists():
                    try:
                        import json
                        f_count = len(json.loads(findings_file.read_text(encoding="utf-8")))
                    except Exception:
                        pass
                result.append({
                    "name": eng.name,
                    "created": eng.created,
                    "targets": eng.targets,
                    "runs_count": len(eng.runs),
                    "findings_count": f_count,
                    "has_report": eng.report_file.exists(),
                })
    return result


@app.post("/api/engagements")
def create_engagement(payload: EngagementCreateRequest):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    name = slugify(payload.name)
    eng = engagement_mod.create(
        name=name,
        targets=payload.targets,
        scope_in=payload.scope_in,
        scope_out=payload.scope_out
    )
    return {
        "name": eng.name,
        "created": eng.created,
        "targets": eng.targets,
        "workspace": str(eng.workspace),
    }


@app.get("/api/engagements/{name}")
def get_engagement_details(name: str):
    eng = engagement_mod.load(name)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings = []
    if eng.findings_file.exists():
        try:
            import json
            findings = json.loads(eng.findings_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    report_text = ""
    if eng.report_file.exists():
        report_text = eng.report_file.read_text(encoding="utf-8")
    elif eng.report_draft_file.exists():
        report_text = eng.report_draft_file.read_text(encoding="utf-8")

    return {
        "name": eng.name,
        "created": eng.created,
        "targets": eng.targets,
        "scope_in": eng.scope_in,
        "scope_out": eng.scope_out,
        "runs": eng.runs,
        "findings": findings,
        "report": report_text,
    }


@app.post("/api/engagements/{name}/finding")
def add_finding(name: str, finding_req: ManualFindingRequest):
    eng = engagement_mod.load(name)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    import json
    from dataclasses import asdict

    findings = []
    if eng.findings_file.exists():
        try:
            findings = json.loads(eng.findings_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    new_finding = findings_mod.Finding(
        kind=finding_req.kind,
        target=finding_req.target,
        name=finding_req.name,
        severity=finding_req.severity,
        source_tool=finding_req.source_tool,
        details=finding_req.details,
        raw=finding_req.raw or f"Added manually via Web GUI at {datetime.now().isoformat()}",
        timestamp=datetime.now().isoformat(),
    )
    findings.append(asdict(new_finding))
    from hackingtool.storage import write_json
    write_json(eng.findings_file, findings, indent=2)

    return {"status": "success", "findings_count": len(findings)}


# ── Configuration & AI Test ────────────────────────────────────────────────────

@app.get("/api/config")
def get_configuration():
    cfg = config.load()
    return {
        "theme": cfg.get("theme", "purple"),
        "tools_dir": str(get_tools_dir()),
        "ai_provider": cfg.get("ai_provider", "auto"),
        "ai_base_url": cfg.get("ai_base_url", "https://api.openai.com/v1"),
        "ai_model": cfg.get("ai_model", "gpt-4o-mini"),
        "has_ai_key": bool(config.ai_key()),
    }


@app.post("/api/config")
def update_configuration(update: ConfigUpdateRequest):
    cfg = config.load()
    if update.theme:
        cfg["theme"] = update.theme
    if update.tools_dir:
        cfg["tools_dir"] = update.tools_dir
    if update.ai_provider:
        cfg["ai_provider"] = update.ai_provider
    if update.ai_base_url:
        cfg["ai_base_url"] = update.ai_base_url
    if update.ai_model:
        cfg["ai_model"] = update.ai_model
    config.save(cfg)

    if update.ai_key is not None:
        env_file = USER_CONFIG_DIR / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        if env_file.exists():
            lines = env_file.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("HACKINGTOOL_AI_KEY="):
                new_lines.append(f"HACKINGTOOL_AI_KEY={update.ai_key}")
                found = True
            else:
                new_lines.append(line)
        if not found and update.ai_key:
            new_lines.append(f"HACKINGTOOL_AI_KEY={update.ai_key}")
        env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        try:
            env_file.chmod(0o600)
        except OSError:
            pass
        os.environ["HACKINGTOOL_AI_KEY"] = update.ai_key

    return {"status": "saved", "config": get_configuration()}


@app.post("/api/config/test-ai")
def test_ai_connection():
    ok, detail = ai_recommend.test_connection()
    return {"connected": ok, "detail": detail}


# ── WebSocket Terminal Runner ──────────────────────────────────────────────────

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()
    current_proc: Optional[asyncio.subprocess.Process] = None

    async def read_stream(stream, stream_name: str):
        try:
            while True:
                # Read chunks up to 2048 bytes for instant unbuffered response
                chunk = await stream.read(2048)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                try:
                    await websocket.send_json({"type": stream_name, "data": text})
                except Exception:
                    break
        except Exception:
            pass

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "run":
                raw_command = msg.get("command", "").strip()
                if not raw_command:
                    await websocket.send_json({"type": "stderr", "data": "Error: Empty command\n"})
                    continue

                if current_proc and current_proc.returncode is None:
                    await websocket.send_json({"type": "stderr", "data": "A process is already running. You can send input or interrupt it (Kill).\n"})
                    continue

                # Automatically adapt package manager commands (e.g. apt -> pacman)
                command = adapt_install_command(raw_command)
                if command != raw_command:
                    await websocket.send_json({
                        "type": "stdout",
                        "data": f"\x1b[33m[Adaptador de Sistema]\x1b[0m Comando adaptado para {detect_pkg_manager()}:\n  \x1b[32m{command}\x1b[0m\n\n"
                    })

                cwd = msg.get("cwd") or str(get_tools_dir())

                # If command expects a subfolder in tools_dir (e.g. git repo), cd into it if exists
                match_clone = re.search(r"git clone\s+(?:https?://[^\s]+/)?([\w\-]+)(?:\.git)?", command)
                if match_clone:
                    repo_folder = match_clone.group(1)
                else:
                    repo_folder = None

                await websocket.send_json({
                    "type": "start",
                    "command": command,
                    "cwd": cwd,
                    "timestamp": datetime.now().isoformat()
                })

                try:
                    # Enriched environment with PATH including venv and local binaries
                    env = os.environ.copy()
                    venv_bin = str(PROJECT_ROOT / ".venv" / "bin")
                    user_bin = str(Path.home() / ".local" / "bin")
                    env["PATH"] = f"{venv_bin}:{user_bin}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{env.get('PATH', '')}"
                    env["PYTHONUNBUFFERED"] = "1"
                    env["TERM"] = "xterm-256color"

                    current_proc = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        stdin=asyncio.subprocess.PIPE,
                        cwd=cwd,
                        executable="/bin/bash",
                        env=env,
                    )

                    stdout_task = asyncio.create_task(read_stream(current_proc.stdout, "stdout"))
                    stderr_task = asyncio.create_task(read_stream(current_proc.stderr, "stderr"))

                    returncode = await current_proc.wait()
                    await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

                    await websocket.send_json({
                        "type": "exit",
                        "code": returncode,
                        "command": command
                    })
                except Exception as exc:
                    await websocket.send_json({
                        "type": "stderr",
                        "data": f"Execution error: {exc}\n"
                    })
                    await websocket.send_json({"type": "exit", "code": 1})

            elif action == "kill":
                if current_proc and current_proc.returncode is None:
                    try:
                        current_proc.terminate()
                        await asyncio.sleep(0.5)
                        if current_proc.returncode is None:
                            current_proc.kill()
                        await websocket.send_json({"type": "stderr", "data": "\n\x1b[31m[Proceso Interrumpido por el usuario]\x1b[0m\n"})
                    except Exception as e:
                        await websocket.send_json({"type": "stderr", "data": f"\nFailed to terminate: {e}\n"})
                else:
                    await websocket.send_json({"type": "stderr", "data": "No active process to terminate.\n"})

            elif action == "input":
                data = msg.get("data", "")
                if current_proc and current_proc.stdin and current_proc.returncode is None:
                    try:
                        current_proc.stdin.write(data.encode())
                        await current_proc.stdin.drain()
                        # Echo input back to terminal window
                        await websocket.send_json({"type": "stdout", "data": data})
                    except Exception as e:
                        await websocket.send_json({"type": "stderr", "data": f"\nInput error: {e}\n"})
                else:
                    await websocket.send_json({"type": "stderr", "data": "\nNo active process listening for input.\n"})

    except WebSocketDisconnect:
        if current_proc and current_proc.returncode is None:
            try:
                current_proc.terminate()
            except Exception:
                pass


# ── Mount Static Files & Frontend ──────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>HackingTool Web Interface loading...</h1>")
