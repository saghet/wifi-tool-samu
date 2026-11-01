import os

from hackingtool.core import HackingTool, HackingToolsCollection, console
from hackingtool.os_detect import CURRENT_OS

_is_arch = (
    CURRENT_OS.distro_id in ("arch", "cachyos", "manjaro", "endeavouros")
    or CURRENT_OS.pkg_manager in ("pacman", "paru", "yay")
)

_anonsurf_install = [
    "git clone https://github.com/quantumcore/anonsurf-arch.git anonsurf-arch",
    (
        "cd anonsurf-arch && "
        "sudo pacman -S --needed --noconfirm tor iptables curl && "
        "sudo install -Dm755 anonsurf /usr/local/bin/anonsurf && "
        "sudo install -Dm755 pandora /usr/local/bin/pandora && "
        "sudo install -Dm644 torrc.anon /etc/tor/torrc.anon && "
        "sudo install -Dm644 onion.pac /etc/tor/onion.pac"
    ),
] if _is_arch else [
    "git clone https://github.com/Und3rf10w/kali-anonsurf.git",
    "cd kali-anonsurf && sudo ./installer.sh",
]


class AnonymouslySurf(HackingTool):
    TITLE = "Anonymously Surf"
    DESCRIPTION = (
        "It automatically overwrites the RAM when the system shuts down\n"
        "and also changes your IP address."
    )
    INSTALL_COMMANDS = _anonsurf_install
    RUN_COMMANDS = ["sudo anonsurf start"]
    PROJECT_URL = "https://github.com/quantumcore/anonsurf-arch" if _is_arch else "https://github.com/Und3rf10w/kali-anonsurf"
    SUPPORTED_OS = ["linux"]

    def __init__(self):
        super().__init__([("Stop", self.stop)])

    def stop(self):
        import subprocess
        console.print("[bold magenta]Stopping Anonsurf...[/bold magenta]")
        subprocess.run(["sudo", "anonsurf", "stop"])


class Multitor(HackingTool):
    TITLE = "Multitor"
    DESCRIPTION = "How to stay in multi places at the same time."
    INSTALL_COMMANDS = [
        "git clone https://github.com/trimstray/multitor.git",
        "cd multitor && sudo bash setup.sh install",
    ]
    RUN_COMMANDS = [
        "multitor --init 2 --user debian-tor --socks-port 9000 --control-port 9900 --proxy privoxy --haproxy"
    ]
    PROJECT_URL = "https://github.com/trimstray/multitor"
    SUPPORTED_OS = ["linux"]

    def __init__(self):
        super().__init__(runnable=False)


class AnonSurfTools(HackingToolsCollection):
    TITLE = "Anonymously Hiding Tools"
    TOOLS = [
        AnonymouslySurf(),
        Multitor(),
    ]


if __name__ == "__main__":
    tools = AnonSurfTools()
    tools.show_options()
