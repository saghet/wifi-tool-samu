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
    "proxychains4": "proxychains-ng",
    "proxychains": "proxychains-ng",
    "wireshark": "wireshark-qt",
    "wireshark-common": "wireshark-cli",
    "default-jre": "jre-openjdk",
    "default-jdk": "jdk-openjdk",
    "default-jre-headless": "jre-openjdk-headless",
    "golang-go": "go",
    "python3-pip": "python-pip",
    "python-is-python3": "",
    "libssl-dev": "openssl",
    "build-essential": "base-devel",
    "git": "git",
    "curl": "curl",
    "wget": "wget",
    "nmap": "nmap",
    "sqlmap": "sqlmap",
    "aircrack-ng": "aircrack-ng",
    "hydra": "hydra",
    "john": "john",
    "hashcat": "hashcat",
    "nikto": "nikto",
    "gobuster": "gobuster",
    "metasploit-framework": "metasploit",
    "tshark": "wireshark-cli",
    "tcpdump": "tcpdump",
    "netcat": "openbsd-netcat",
    "netcat-traditional": "gnu-netcat",
    "socat": "socat",
    "tor": "tor",
    "torsocks": "torsocks",
    "macchanger": "macchanger",
    "ettercap-text-only": "ettercap",
    "ettercap-graphical": "ettercap",
    "dsniff": "dsniff",
    "scapy": "scapy",
    "radare2": "radare2",
    "ghidra": "ghidra",
    "binwalk": "binwalk",
    "exiftool": "perl-image-exiftool",
    "foremost": "foremost",
    "steghide": "steghide",
}


def detect_pkg_manager() -> str:
    """Detect the most appropriate package manager on the host."""
    for mgr in ("pacman", "paru", "yay", "apt-get", "apt", "dnf", "zypper", "apk", "brew"):
        if shutil.which(mgr):
            return mgr
    return "unknown"


def adapt_install_command(cmd: str, pkg_manager: Optional[str] = None) -> str:
    """Translate an installation command line to the local operating system."""
    if not cmd:
        return cmd

    mgr = pkg_manager or detect_pkg_manager()

    # 1. Adapt pip commands if system Python enforces PEP 668 (externally managed)
    if "pip install" in cmd:
        # Use virtualenv pip if available
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        venv_pip = base_dir / ".venv" / "bin" / "pip"
        if venv_pip.exists():
            return cmd.replace("pip install", f"{venv_pip} install")

    # If host is Debian/Ubuntu and uses apt, return as-is
    if mgr in ("apt-get", "apt"):
        return cmd

    # 2. Adapt apt/apt-get commands for Arch Linux (pacman/paru/yay)
    if mgr in ("pacman", "paru", "yay"):
        apt_match = re.search(r"(?:sudo\s+)?apt(?:-get)?\s+install\s+(?:-[a-zA-Z]+\s+)*([\w\-\.\s]+)", cmd)
        if apt_match:
            raw_pkgs = apt_match.group(1).split()
            arch_pkgs = []
            for p in raw_pkgs:
                if p.startswith("-"):
                    continue
                arch_name = DEBIAN_TO_ARCH_MAP.get(p.lower(), p)
                if arch_name:
                    arch_pkgs.append(arch_name)

            if arch_pkgs:
                pkgs_str = " ".join(arch_pkgs)
                if mgr == "pacman":
                    return f"sudo pacman -S --noconfirm --needed {pkgs_str}"
                else:
                    # paru or yay handles both official and AUR packages
                    return f"{mgr} -S --noconfirm --needed {pkgs_str}"

    # 3. Adapt apt/apt-get for Fedora / RedHat (dnf)
    if mgr == "dnf":
        apt_match = re.search(r"(?:sudo\s+)?apt(?:-get)?\s+install\s+(?:-[a-zA-Z]+\s+)*([\w\-\.\s]+)", cmd)
        if apt_match:
            raw_pkgs = apt_match.group(1).split()
            return f"sudo dnf install -y {' '.join(p for p in raw_pkgs if not p.startswith('-'))}"

    # 4. Adapt for macOS Homebrew
    if mgr == "brew":
        apt_match = re.search(r"(?:sudo\s+)?apt(?:-get)?\s+install\s+(?:-[a-zA-Z]+\s+)*([\w\-\.\s]+)", cmd)
        if apt_match:
            raw_pkgs = apt_match.group(1).split()
            return f"brew install {' '.join(p for p in raw_pkgs if not p.startswith('-'))}"

    return cmd
