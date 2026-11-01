"""Cross-distribution package manager adapter and resilient execution engine.

Guarantees full compatibility across:
1. Debian / Ubuntu / Kali / Parrot (apt-get, apt, dpkg)
2. Arch Linux / Garuda Linux / Manjaro / CachyOS (pacman, paru, yay)
3. Red Hat Enterprise Linux / Fedora / CentOS / Rocky / AlmaLinux (dnf, yum, rpm)
4. openSUSE / SLES (zypper)
5. Alpine Linux (apk)
6. macOS (brew)
"""
import os
import re
import shutil
from pathlib import Path
from typing import Optional

# ── MAPPINGS: Debian/Ubuntu -> Arch Linux / Garuda ─────────────────────────────
DEBIAN_TO_ARCH_MAP = {
    # Anonymity & Network
    "proxychains4": "proxychains-ng",
    "proxychains": "proxychains-ng",
    "tor": "tor",
    "torsocks": "torsocks",
    "i2p": "i2p",
    "i2p-router": "i2p",
    "secure-delete": "secure-delete",
    "macchanger": "macchanger",
    "sshpass": "sshpass",
    "netcat": "openbsd-netcat",
    "netcat-traditional": "gnu-netcat",
    "socat": "socat",
    "curl": "curl",
    "wget": "wget",
    "git": "git",

    # Scanning & Recon
    "nmap": "nmap",
    "masscan": "masscan",
    "rustscan": "rustscan",
    "hping3": "hping",
    "slowhttptest": "slowhttptest",
    "whatweb": "whatweb",
    "wpscan": "wpscan",
    "nikto": "nikto",
    "feroxbuster": "feroxbuster",
    "gobuster": "gobuster",
    "zaproxy": "zaproxy",

    # Sniffing & Wireless
    "wireshark": "wireshark-qt",
    "wireshark-common": "wireshark-cli",
    "tshark": "wireshark-cli",
    "tcpdump": "tcpdump",
    "aircrack-ng": "aircrack-ng",
    "bettercap": "bettercap",
    "kismet": "kismet",
    "reaver": "reaver",
    "scrot": "scrot",
    "dsniff": "dsniff",
    "scapy": "scapy",
    "ettercap": "ettercap",
    "ettercap-text-only": "ettercap",
    "ettercap-graphical": "ettercap",
    "libbluetooth-dev": "bluez-libs",

    # Exploitation & Cracking
    "metasploit-framework": "metasploit",
    "exploitdb": "exploitdb",
    "sqlmap": "sqlmap",
    "hashcat": "hashcat",
    "john": "john",
    "hydra": "hydra",
    "crunch": "crunch",
    "cewl": "cewl",

    # Stego & Forensics
    "steghide": "steghide",
    "stegseek": "stegseek",
    "outguess": "outguess",
    "foremost": "foremost",
    "binwalk": "binwalk",
    "exiftool": "perl-image-exiftool",
    "libimage-exiftool-perl": "perl-image-exiftool",
    "guymager": "guymager",

    # Reversing & Mobile
    "ghidra": "ghidra",
    "radare2": "radare2",
    "gdb": "gdb",
    "binutils": "binutils",
    "apktool": "android-apktool",
    "adb": "android-tools",
    "neo4j": "neo4j",
    "tilix": "tilix",

    # Languages & Dev libraries
    "build-essential": "base-devel",
    "golang": "go",
    "golang-go": "go",
    "python3": "python",
    "python3-pip": "python-pip",
    "python3-dev": "python",
    "python-is-python3": "",
    "python3-pyqt5": "python-pyqt5",
    "libssl-dev": "openssl",
    "libffi-dev": "libffi",
    "default-jre": "jre-openjdk",
    "default-jdk": "jdk-openjdk",
    "default-jre-headless": "jre-openjdk-headless",
    "php": "php",
    "php-bz2": "php",
    "php-curl": "php",
    "php-mbstring": "php",
}

# ── MAPPINGS: Debian/Ubuntu -> Red Hat / Fedora / CentOS / Rocky ───────────────
DEBIAN_TO_RHEL_MAP = {
    # Anonymity & Network
    "proxychains4": "proxychains-ng",
    "proxychains": "proxychains-ng",
    "tor": "tor",
    "torsocks": "torsocks",
    "i2p": "i2p",
    "secure-delete": "secure-delete",
    "macchanger": "macchanger",
    "sshpass": "sshpass",
    "netcat": "nmap-ncat",
    "netcat-traditional": "nc",
    "socat": "socat",
    "curl": "curl",
    "wget": "wget",
    "git": "git",

    # Scanning & Recon
    "nmap": "nmap",
    "masscan": "masscan",
    "rustscan": "rustscan",
    "hping3": "hping3",
    "slowhttptest": "slowhttptest",
    "whatweb": "whatweb",
    "wpscan": "wpscan",
    "nikto": "nikto",
    "feroxbuster": "feroxbuster",
    "gobuster": "gobuster",
    "zaproxy": "zaproxy",

    # Sniffing & Wireless
    "wireshark": "wireshark",
    "wireshark-common": "wireshark-cli",
    "tshark": "wireshark-cli",
    "tcpdump": "tcpdump",
    "aircrack-ng": "aircrack-ng",
    "bettercap": "bettercap",
    "kismet": "kismet",
    "reaver": "reaver",
    "scrot": "scrot",
    "dsniff": "dsniff",
    "scapy": "scapy",
    "ettercap": "ettercap",
    "ettercap-text-only": "ettercap",
    "ettercap-graphical": "ettercap-gtk",
    "libbluetooth-dev": "bluez-libs-devel",

    # Exploitation & Cracking
    "metasploit-framework": "metasploit-framework",
    "exploitdb": "exploitdb",
    "sqlmap": "sqlmap",
    "hashcat": "hashcat",
    "john": "john",
    "hydra": "hydra",
    "crunch": "crunch",
    "cewl": "cewl",

    # Stego & Forensics
    "steghide": "steghide",
    "stegseek": "stegseek",
    "outguess": "outguess",
    "foremost": "foremost",
    "binwalk": "binwalk",
    "exiftool": "perl-Image-ExifTool",
    "libimage-exiftool-perl": "perl-Image-ExifTool",
    "guymager": "guymager",

    # Reversing & Mobile
    "ghidra": "ghidra",
    "radare2": "radare2",
    "gdb": "gdb",
    "binutils": "binutils",
    "apktool": "apktool",
    "adb": "android-tools",
    "neo4j": "neo4j",
    "tilix": "tilix",

    # Languages & Dev libraries
    "build-essential": "gcc gcc-c++ make",
    "golang": "golang",
    "golang-go": "golang",
    "python3": "python3",
    "python3-pip": "python3-pip",
    "python3-dev": "python3-devel",
    "python-is-python3": "",
    "python3-pyqt5": "python3-qt5",
    "libssl-dev": "openssl-devel",
    "libffi-dev": "libffi-devel",
    "default-jre": "java-17-openjdk",
    "default-jdk": "java-17-openjdk-devel",
    "default-jre-headless": "java-17-openjdk-headless",
    "php": "php",
    "php-bz2": "php-common",
    "php-curl": "php-common",
    "php-mbstring": "php-mbstring",
}

# ── MAPPINGS: Debian/Ubuntu -> openSUSE / SLES ─────────────────────────────────
DEBIAN_TO_SUSE_MAP = {
    "proxychains4": "proxychains-ng",
    "proxychains": "proxychains-ng",
    "tor": "tor",
    "torsocks": "torsocks",
    "nmap": "nmap",
    "sqlmap": "sqlmap",
    "hashcat": "hashcat",
    "john": "john",
    "hydra": "hydra",
    "nikto": "nikto",
    "wireshark": "wireshark",
    "tshark": "wireshark-ui-qt",
    "aircrack-ng": "aircrack-ng",
    "build-essential": "devel_basis",
    "curl": "curl",
    "wget": "wget",
    "git": "git",
    "default-jre": "java-17-openjdk",
    "libssl-dev": "libopenssl-devel",
    "adb": "android-tools",
}


def detect_distro_family() -> str:
    """Identify host distribution family: 'debian', 'arch' (includes Garuda), 'rhel', 'suse', 'alpine', 'macos'."""
    from hackingtool.os_detect import CURRENT_OS

    did = CURRENT_OS.distro_id.lower()
    dlike = CURRENT_OS.distro_like.lower()
    mgr = CURRENT_OS.pkg_manager.lower()

    if "garuda" in did or "arch" in did or "cachyos" in did or "manjaro" in did or "arch" in dlike:
        return "arch"
    if "rhel" in did or "fedora" in did or "centos" in did or "rocky" in did or "almalinux" in did or "rhel" in dlike or "fedora" in dlike:
        return "rhel"
    if "suse" in did or "opensuse" in did or "sles" in did or "suse" in dlike:
        return "suse"
    if "alpine" in did or "alpine" in dlike:
        return "alpine"
    if "ubuntu" in did or "debian" in did or "kali" in did or "parrot" in did or "debian" in dlike:
        return "debian"
    if CURRENT_OS.system == "macos":
        return "macos"

    if mgr in ("pacman", "paru", "yay"):
        return "arch"
    if mgr in ("dnf", "yum"):
        return "rhel"
    if mgr == "zypper":
        return "suse"
    if mgr == "apk":
        return "alpine"
    if mgr in ("apt-get", "apt"):
        return "debian"
    if mgr == "brew":
        return "macos"

    return "unknown"


def detect_pkg_manager() -> str:
    """Detect the most appropriate package manager on the host."""
    for mgr in ("pacman", "paru", "yay", "apt-get", "apt", "dnf", "yum", "zypper", "apk", "brew"):
        if shutil.which(mgr):
            return mgr
    return "unknown"


def make_git_idempotent(step: str) -> str:
    """Transform git clone into a resilient, idempotent command.
    Avoids code 128 failure ('destination path already exists').
    """
    m = re.search(r"git\s+clone(?:\s+-[^\s]+|\s+--[^\s]+(?:\s+[^\s]+)?)*\s+(https?://[^\s]+?)(?:\.git)?(?:\s+([\w\.\-]+))?(?=\s*(?:&&|;|$))", step)
    if not m:
        return step

    url = m.group(1)
    url_git = url if url.endswith(".git") else f"{url}.git"
    repo = url.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
    target = m.group(2) if m.group(2) else repo

    replacement = (
        f'(if [ -d "{target}/.git" ]; then (cd "{target}" && git pull --quiet || true); '
        f'elif [ -d "{target}" ]; then rm -rf "{target}" && git clone {url_git} {target}; '
        f'else git clone {url_git} {target}; fi)'
    )
    return step[:m.start()] + replacement + step[m.end():]


def resolve_command_binary(cmd: str) -> str:
    """Resolve minor binary naming discrepancies between Linux distributions.
    E.g. proxychains4 vs proxychains, python vs python3.
    """
    stripped = cmd.strip()
    if not stripped:
        return cmd

    tokens = stripped.split()
    idx = 0
    if tokens[0] == "sudo":
        idx = 1
    if idx >= len(tokens):
        return cmd

    bin_name = tokens[idx]

    # Proxychains binary name resolution
    if bin_name == "proxychains4" and not shutil.which("proxychains4") and shutil.which("proxychains"):
        tokens[idx] = "proxychains"
        return " ".join(tokens)
    elif bin_name == "proxychains" and not shutil.which("proxychains") and shutil.which("proxychains4"):
        tokens[idx] = "proxychains4"
        return " ".join(tokens)

    # Exiftool binary name resolution
    if bin_name == "exiftool" and not shutil.which("exiftool") and shutil.which("perl-image-exiftool"):
        tokens[idx] = "perl-image-exiftool"
        return " ".join(tokens)

    return cmd


def _adapt_single_step(cmd: str, mgr: str, family: str) -> str:
    """Translate a single command step into the host's native environment."""
    step = cmd.strip()
    if not step:
        return ""

    # Always make any git clone idempotent
    if "git clone" in step:
        step = make_git_idempotent(step)

    # Skip sudo if already root
    if os.name != "nt" and os.geteuid() == 0 and step.startswith("sudo "):
        step = step[5:].strip()

    # ── 1. ARCH LINUX / GARUDA SPECIAL CASES ──────────────────────────────────
    if family == "arch" or mgr in ("pacman", "paru", "yay"):
        # Fix anonsurf path consistency
        if "kali-anonsurf" in step or "anonsurf-arch" in step:
            return (
                '(if [ -d "anonsurf-arch/.git" ]; then (cd "anonsurf-arch" && git pull --quiet || true); '
                'elif [ -d "anonsurf-arch" ]; then rm -rf "anonsurf-arch" && git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf-arch; '
                'else git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf-arch; fi) && '
                'cd anonsurf-arch && '
                'sudo pacman -S --needed --noconfirm tor iptables curl && '
                'sudo install -Dm755 anonsurf /usr/local/bin/anonsurf && '
                'sudo install -Dm755 pandora /usr/local/bin/pandora && '
                'sudo install -Dm644 torrc.anon /etc/tor/torrc.anon && '
                'sudo install -Dm644 onion.pac /etc/tor/onion.pac'
            )

        if "rustscan" in step.lower() and (".deb" in step.lower() or "dpkg" in step.lower()):
            return "sudo pacman -S --noconfirm --needed rustscan || cargo install rustscan"

        # Translate apt/apt-get pattern to pacman
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            arch_pkgs = []
            for p in pkgs:
                mapped = DEBIAN_TO_ARCH_MAP.get(p.lower(), p)
                if mapped:
                    arch_pkgs.append(mapped)

            if arch_pkgs:
                pkgs_str = " ".join(arch_pkgs)
                new_cmd = f"sudo pacman -S --noconfirm --needed {pkgs_str}"
                step = re.sub(apt_pattern, new_cmd, step)

        return step

    # ── 2. RED HAT / FEDORA / CENTOS / ROCKY (dnf / yum) ──────────────────────
    if family == "rhel" or mgr in ("dnf", "yum"):
        rhel_cmd = "dnf" if shutil.which("dnf") else "yum"

        if "kali-anonsurf" in step or "anonsurf-arch" in step:
            return (
                f'(if [ -d "anonsurf/.git" ]; then (cd "anonsurf" && git pull --quiet || true); '
                f'else git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf; fi) && '
                f'cd anonsurf && sudo {rhel_cmd} install -y tor iptables curl && '
                'sudo install -Dm755 anonsurf /usr/local/bin/anonsurf && '
                'sudo install -Dm755 pandora /usr/local/bin/pandora && '
                'sudo install -Dm644 torrc.anon /etc/tor/torrc.anon && '
                'sudo install -Dm644 onion.pac /etc/tor/onion.pac'
            )

        if "rustscan" in step.lower() and (".deb" in step.lower() or "dpkg" in step.lower()):
            return f"sudo {rhel_cmd} install -y rustscan || cargo install rustscan"

        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            rhel_pkgs = []
            for p in pkgs:
                mapped = DEBIAN_TO_RHEL_MAP.get(p.lower(), p)
                if mapped:
                    for sub in mapped.split():
                        rhel_pkgs.append(sub)

            if rhel_pkgs:
                pkgs_str = " ".join(rhel_pkgs)
                new_cmd = f"sudo {rhel_cmd} install -y {pkgs_str}"
                step = re.sub(apt_pattern, new_cmd, step)

        return step

    # ── 3. OPENSUSE (zypper) ──────────────────────────────────────────────────
    if family == "suse" or mgr == "zypper":
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            suse_pkgs = [DEBIAN_TO_SUSE_MAP.get(p.lower(), p) for p in pkgs]
            if suse_pkgs:
                step = re.sub(apt_pattern, f"sudo zypper install -y {' '.join(suse_pkgs)}", step)
        return step

    # ── 4. ALPINE LINUX (apk) ─────────────────────────────────────────────────
    if family == "alpine" or mgr == "apk":
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            if pkgs:
                step = re.sub(apt_pattern, f"sudo apk add {' '.join(pkgs)}", step)
        return step

    # ── 5. DEBIAN / UBUNTU (apt-get / apt) ────────────────────────────────────
    if family == "debian" or mgr in ("apt-get", "apt"):
        return step

    # ── 6. MACOS (brew) ───────────────────────────────────────────────────────
    if family == "macos" or mgr == "brew":
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            if pkgs:
                step = re.sub(apt_pattern, f"brew install {' '.join(pkgs)}", step)
        return step

    return step


def adapt_install_command(full_cmd: str, pkg_manager: Optional[str] = None) -> str:
    """Translate an installation command line (potentially chained with && or ;)
    to the host's operating system package manager, guaranteeing cross-compatibility
    with Ubuntu, Garuda (Arch), Red Hat (dnf), openSUSE (zypper), and Alpine (apk).
    """
    if not full_cmd:
        return full_cmd

    mgr = pkg_manager or detect_pkg_manager()
    family = detect_distro_family()

    # Special unified intercept for Anonymously Surf to prevent any broken sub-step
    if "kali-anonsurf" in full_cmd or "anonsurf-arch" in full_cmd:
        return _adapt_single_step("kali-anonsurf", mgr, family)

    # Split chained commands by '&&'
    if "&&" in full_cmd:
        parts = full_cmd.split("&&")
        adapted_parts = [_adapt_single_step(p, mgr, family) for p in parts]
        return " && ".join(filter(None, adapted_parts))

    # Split chained commands by ';'
    if ";" in full_cmd:
        parts = full_cmd.split(";")
        adapted_parts = [_adapt_single_step(p, mgr, family) for p in parts]
        return " ; ".join(filter(None, adapted_parts))

    return _adapt_single_step(full_cmd, mgr, family)


# ── System Dependencies Check & Setup Helper ──────────────────────────────────

BASE_SECURITY_PACKAGES = {
    "arch": [
        "proxychains-ng", "torsocks", "tor", "nmap", "sqlmap", "hashcat",
        "john", "hydra", "nikto", "wireshark-cli", "wireshark-qt", "bettercap",
        "php", "jre-openjdk", "masscan", "perl-image-exiftool", "steghide",
        "android-tools", "base-devel", "curl", "wget", "git"
    ],
    "rhel": [
        "proxychains-ng", "torsocks", "tor", "nmap", "sqlmap", "hashcat",
        "john", "hydra", "nikto", "wireshark", "wireshark-cli",
        "php", "java-17-openjdk", "masscan", "perl-Image-ExifTool", "steghide",
        "android-tools", "gcc", "gcc-c++", "make", "curl", "wget", "git"
    ],
    "debian": [
        "proxychains4", "torsocks", "tor", "nmap", "sqlmap", "hashcat",
        "john", "hydra", "nikto", "tshark", "wireshark", "bettercap",
        "php", "default-jre", "masscan", "libimage-exiftool-perl", "steghide",
        "adb", "build-essential", "curl", "wget", "git"
    ],
    "suse": [
        "proxychains-ng", "torsocks", "tor", "nmap", "sqlmap", "hashcat",
        "john", "hydra", "nikto", "wireshark", "wireshark-ui-qt",
        "php", "java-17-openjdk", "curl", "wget", "git"
    ],
    "alpine": [
        "proxychains-ng", "tor", "nmap", "sqlmap", "john", "hydra",
        "nikto", "wireshark", "curl", "wget", "git", "build-base"
    ]
}


def get_system_setup_command() -> str:
    """Return the one-liner command to install all missing base packages for this distro."""
    family = detect_distro_family()
    mgr = detect_pkg_manager()
    pkgs = BASE_SECURITY_PACKAGES.get(family, BASE_SECURITY_PACKAGES.get("arch", []))
    pkgs_str = " ".join(pkgs)

    if family == "arch" or mgr in ("pacman", "paru", "yay"):
        return f"sudo pacman -S --needed --noconfirm {pkgs_str}"
    elif family == "rhel" or mgr in ("dnf", "yum"):
        rhel_cmd = "dnf" if shutil.which("dnf") else "yum"
        return f"sudo {rhel_cmd} install -y {pkgs_str}"
    elif family == "debian" or mgr in ("apt-get", "apt"):
        return f"sudo apt-get update && sudo apt-get install -y {pkgs_str}"
    elif family == "suse" or mgr == "zypper":
        return f"sudo zypper install -y {pkgs_str}"
    elif family == "alpine" or mgr == "apk":
        return f"sudo apk add {pkgs_str}"
    return f"echo 'Unsupported automated package manager: {mgr}'"


def check_host_dependencies() -> dict:
    """Inspect all key cybersecurity tools and components on the host system."""
    key_tools = [
        {"name": "git", "binaries": ["git"], "category": "Base"},
        {"name": "curl", "binaries": ["curl"], "category": "Base"},
        {"name": "wget", "binaries": ["wget"], "category": "Base"},
        {"name": "python3", "binaries": ["python3", "python"], "category": "Base"},
        {"name": "gcc / make", "binaries": ["gcc", "make"], "category": "Build"},
        {"name": "proxychains", "binaries": ["proxychains4", "proxychains"], "category": "Anonymity"},
        {"name": "tor", "binaries": ["tor"], "category": "Anonymity"},
        {"name": "anonsurf", "binaries": ["anonsurf"], "category": "Anonymity"},
        {"name": "nmap", "binaries": ["nmap"], "category": "Recon"},
        {"name": "masscan", "binaries": ["masscan"], "category": "Recon"},
        {"name": "sqlmap", "binaries": ["sqlmap"], "category": "Exploitation"},
        {"name": "hashcat", "binaries": ["hashcat"], "category": "Cracking"},
        {"name": "john the ripper", "binaries": ["john"], "category": "Cracking"},
        {"name": "hydra", "binaries": ["hydra"], "category": "Cracking"},
        {"name": "nikto", "binaries": ["nikto"], "category": "Scanning"},
        {"name": "wireshark / tshark", "binaries": ["wireshark", "tshark"], "category": "Sniffing"},
        {"name": "aircrack-ng", "binaries": ["aircrack-ng"], "category": "Wireless"},
        {"name": "bettercap", "binaries": ["bettercap"], "category": "Sniffing"},
        {"name": "steghide", "binaries": ["steghide"], "category": "Forensics"},
        {"name": "exiftool", "binaries": ["exiftool", "perl-image-exiftool"], "category": "Forensics"},
        {"name": "adb (Android Tools)", "binaries": ["adb"], "category": "Mobile"},
        {"name": "apktool", "binaries": ["apktool", "android-apktool"], "category": "Mobile"},
    ]

    results = []
    installed_count = 0
    missing_count = 0

    for item in key_tools:
        found_bin = None
        for b in item["binaries"]:
            loc = shutil.which(b)
            if loc:
                found_bin = loc
                break
        is_inst = found_bin is not None
        if is_inst:
            installed_count += 1
        else:
            missing_count += 1
        results.append({
            "name": item["name"],
            "category": item["category"],
            "installed": is_inst,
            "path": found_bin or "No encontrado",
        })

    return {
        "distro_family": detect_distro_family(),
        "pkg_manager": detect_pkg_manager(),
        "total": len(key_tools),
        "installed_count": installed_count,
        "missing_count": missing_count,
        "setup_command": get_system_setup_command(),
        "tools": results,
    }
