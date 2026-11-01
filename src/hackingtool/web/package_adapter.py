"""Cross-distribution package manager adapter for HackingTool.

Guarantees full compatibility across:
1. Debian / Ubuntu / Kali / Parrot (apt-get, apt, dpkg)
2. Arch Linux / Garuda Linux / Manjaro / CachyOS (pacman, paru, yay)
3. Red Hat Enterprise Linux / Fedora / CentOS / Rocky / AlmaLinux (dnf, yum, rpm)
4. macOS (brew)
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


def detect_distro_family() -> str:
    """Identify host distribution family: 'debian', 'arch' (includes Garuda), 'rhel', 'macos'."""
    from hackingtool.os_detect import CURRENT_OS

    did = CURRENT_OS.distro_id.lower()
    dlike = CURRENT_OS.distro_like.lower()
    mgr = CURRENT_OS.pkg_manager.lower()

    if "garuda" in did or "arch" in did or "cachyos" in did or "manjaro" in did or "arch" in dlike:
        return "arch"
    if "rhel" in did or "fedora" in did or "centos" in did or "rocky" in did or "almalinux" in did or "rhel" in dlike or "fedora" in dlike:
        return "rhel"
    if "ubuntu" in did or "debian" in did or "kali" in did or "parrot" in did or "debian" in dlike:
        return "debian"
    if CURRENT_OS.system == "macos":
        return "macos"

    if mgr in ("pacman", "paru", "yay"):
        return "arch"
    if mgr in ("dnf", "yum"):
        return "rhel"
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


def _adapt_single_step(cmd: str, mgr: str, family: str) -> str:
    """Translate a single command step into the host's native environment."""
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

    # ── 1. ARCH LINUX / GARUDA SPECIAL CASES ──────────────────────────────────
    if family == "arch" or mgr in ("pacman", "paru", "yay"):
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

        if "rustscan" in step.lower() and (".deb" in step.lower() or "dpkg" in step.lower()):
            return "sudo pacman -S --needed --noconfirm rustscan || cargo install rustscan"

        # Translate apt/apt-get pattern to pacman
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
            arch_pkgs = list(dict.fromkeys(arch_pkgs))
            if arch_pkgs:
                pkgs_str = " ".join(arch_pkgs)
                new_cmd = f"sudo pacman -S --noconfirm --needed {pkgs_str}"
                step = re.sub(apt_pattern, new_cmd, step)

        return step

    # ── 2. RED HAT / FEDORA / CENTOS / ROCKY (dnf / yum) ──────────────────────
    if family == "rhel" or mgr in ("dnf", "yum"):
        rhel_cmd = "dnf" if shutil.which("dnf") else "yum"

        if "kali-anonsurf.git" in step:
            # Fallback for anonsurf on RHEL/Fedora
            return "git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf"
        if "installer.sh" in step and ("kali-anonsurf" in step or "anonsurf" in step):
            return (
                f"cd anonsurf && sudo {rhel_cmd} install -y tor iptables curl && "
                "sudo install -Dm755 anonsurf /usr/local/bin/anonsurf && "
                "sudo install -Dm755 pandora /usr/local/bin/pandora && "
                "sudo install -Dm644 torrc.anon /etc/tor/torrc.anon && "
                "sudo install -Dm644 onion.pac /etc/tor/onion.pac"
            )

        if "rustscan" in step.lower() and (".deb" in step.lower() or "dpkg" in step.lower()):
            return f"sudo {rhel_cmd} install -y rustscan || cargo install rustscan"

        # Translate apt/apt-get pattern to dnf/yum
        apt_pattern = r"(?:sudo\s+)?apt(?:-get)?\s+(?:-y\s+)?install(?:\s+-[a-zA-Z]+)*\s+([\w\-\.\s]+)"
        match = re.search(apt_pattern, step)
        if match:
            raw_pkgs = match.group(1).split()
            rhel_pkgs = []
            for p in raw_pkgs:
                if p.startswith("-"):
                    continue
                mapped = DEBIAN_TO_RHEL_MAP.get(p.lower(), p.lower())
                if mapped:
                    rhel_pkgs.append(mapped)
            rhel_pkgs = list(dict.fromkeys(rhel_pkgs))
            if rhel_pkgs:
                pkgs_str = " ".join(rhel_pkgs)
                new_cmd = f"sudo {rhel_cmd} install -y {pkgs_str}"
                step = re.sub(apt_pattern, new_cmd, step)

        return step

    # ── 3. DEBIAN / UBUNTU (apt-get / apt) ────────────────────────────────────
    if family == "debian" or mgr in ("apt-get", "apt"):
        return step

    # ── 4. MACOS (brew) ───────────────────────────────────────────────────────
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
    with Ubuntu, Garuda (Arch), and Red Hat (dnf).
    """
    if not full_cmd:
        return full_cmd

    mgr = pkg_manager or detect_pkg_manager()
    family = detect_distro_family()

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
