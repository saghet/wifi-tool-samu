"""Cross-distribution package manager adapter for HackingTool.

Translates Debian/Ubuntu-centric apt-get install commands into the host's native
package manager (e.g. pacman / paru on Arch Linux, dnf on Fedora, brew on macOS).
"""
import os
import re
import shutil
from pathlib import Path
from typing import Optional

# Mappings for common security tools from Debian/Ubuntu package names to Arch Linux
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


def detect_pkg_manager() -> str:
    """Detect the most appropriate package manager on the host."""
    for mgr in ("pacman", "paru", "yay", "apt-get", "apt", "dnf", "zypper", "apk", "brew"):
        if shutil.which(mgr):
            return mgr
    return "unknown"


def _adapt_single_step(cmd: str, mgr: str) -> str:
    """Translate a single command step to host package manager."""
    step = cmd.strip()
    if not step:
        return ""

    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    venv_pip = base_dir / ".venv" / "bin" / "pip"

    # Adapt pip calls to virtualenv if available
    if "pip install" in step or "pip3 install" in step:
        if venv_pip.exists():
            step = re.sub(r"(?:sudo\s+)?pip3?\s+install", f"{venv_pip} install", step)
            step = step.replace("--user", "")

    # Handle Special Case 1: Anonymously Surf (kali-anonsurf -> anonsurf-arch on Arch)
    if mgr in ("pacman", "paru", "yay"):
        if "kali-anonsurf.git" in step:
            return "git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf-arch"
        if "installer.sh" in step and ("kali-anonsurf" in step or "anonsurf" in step):
            return (
                "cd anonsurf-arch && "
                "sudo pacman -S --needed --noconfirm tor iptables curl && "
                "sudo install -Dm755 anonsurf /usr/local/bin/anonsurf && "
                "sudo install -Dm755 pandora /usr/local/bin/pandora && "
                "sudo install -Dm644 torrc.anon /etc/tor/torrc.anon && "
                "sudo install -Dm644 onion.pac /etc/tor/onion.pac"
            )

        # Handle Special Case 2: RustScan .deb download + dpkg
        if "rustscan" in step.lower() and (".deb" in step.lower() or "dpkg" in step.lower()):
            return "sudo pacman -S --needed --noconfirm rustscan || cargo install rustscan"

    # If host is Debian/Ubuntu, return as-is
    if mgr in ("apt-get", "apt"):
        return step

    # Translate apt/apt-get to pacman
    if mgr in ("pacman", "paru", "yay"):
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            arch_pkgs = []
            for p in raw_pkgs:
                if p.startswith("-"):
                    continue
                arch_name = DEBIAN_TO_ARCH_MAP.get(p.lower(), p.lower())
                if arch_name:
                    arch_pkgs.append(arch_name)
            arch_pkgs = list(dict.fromkeys(arch_pkgs))  # deduplicate
            if arch_pkgs:
                pkgs_str = " ".join(arch_pkgs)
                new_cmd = f"sudo pacman -S --noconfirm --needed {pkgs_str}"
                step = re.sub(apt_pattern, new_cmd, step)

    # Translate apt to dnf for Fedora/RHEL
    elif mgr == "dnf":
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            if pkgs:
                new_cmd = f"sudo dnf install -y {' '.join(pkgs)}"
                step = re.sub(apt_pattern, new_cmd, step)

    # Translate apt to brew for macOS
    elif mgr == "brew":
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            pkgs = [p for p in raw_pkgs if not p.startswith("-")]
            if pkgs:
                new_cmd = f"brew install {' '.join(pkgs)}"
                step = re.sub(apt_pattern, new_cmd, step)

    return step


def adapt_install_command(full_cmd: str, pkg_manager: Optional[str] = None) -> str:
    """Translate an installation command line (potentially chained with && or ;)
    to the host's operating system package manager.
    """
    if not full_cmd:
        return full_cmd

    mgr = pkg_manager or detect_pkg_manager()

    # Split chained commands by '&&'
    if "&&" in full_cmd:
        parts = full_cmd.split("&&")
        adapted_parts = [_adapt_single_step(p, mgr) for p in parts]
        return " && ".join(filter(None, adapted_parts))

    # Split chained commands by ';'
    if ";" in full_cmd:
        parts = full_cmd.split(";")
        adapted_parts = [_adapt_single_step(p, mgr) for p in parts]
        return " ; ".join(filter(None, adapted_parts))

    return _adapt_single_step(full_cmd, mgr)
