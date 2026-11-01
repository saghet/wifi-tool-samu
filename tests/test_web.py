import pytest
from fastapi.testclient import TestClient

from hackingtool.web.server import app

client = TestClient(app)


def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "HACKINGTOOL" in response.text.upper()


def test_api_system():
    response = client.get("/api/system")
    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "total_tools" in data
    assert data["total_tools"] > 200
    assert data["total_categories"] >= 20


def test_api_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert len(cats) >= 20
    assert any(c["title"] == "Information gathering tools" for c in cats)


def test_api_tools():
    response = client.get("/api/tools")
    assert response.status_code == 200
    tools = response.json()
    assert len(tools) > 200

    # Test search query
    response_search = client.get("/api/tools?search=nmap")
    assert response_search.status_code == 200
    search_results = response_search.json()
    assert len(search_results) >= 1
    assert any("nmap" in t["title"].lower() for t in search_results)


def test_api_tags():
    response = client.get("/api/tags")
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) > 0
    assert any(t["tag"] == "recon" for t in tags)


def test_api_ai_recommend():
    response = client.post("/api/ai/recommend", json={"intent": "crack a wifi password"})
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0


def test_api_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    cfg = response.json()
    assert "tools_dir" in cfg
    assert "ai_provider" in cfg


def test_package_adapter_arch_garuda():
    from hackingtool.web.package_adapter import _adapt_single_step
    arch_cmd = _adapt_single_step("sudo apt-get install -y proxychains4 wireshark build-essential", mgr="pacman", family="arch")
    assert "pacman -S" in arch_cmd
    assert "proxychains-ng" in arch_cmd
    assert "wireshark-qt" in arch_cmd
    assert "base-devel" in arch_cmd


def test_package_adapter_redhat():
    from hackingtool.web.package_adapter import _adapt_single_step
    rhel_cmd = _adapt_single_step("sudo apt-get install -y proxychains4 libssl-dev build-essential", mgr="dnf", family="rhel")
    assert ("dnf install -y" in rhel_cmd or "yum install -y" in rhel_cmd)
    assert "proxychains-ng" in rhel_cmd
    assert "openssl-devel" in rhel_cmd
    assert "gcc" in rhel_cmd


def test_package_adapter_ubuntu_debian():
    from hackingtool.web.package_adapter import _adapt_single_step
    deb_cmd = _adapt_single_step("sudo apt-get install -y proxychains4", mgr="apt-get", family="debian")
    assert "apt-get install -y proxychains4" in deb_cmd


def test_api_system_dependencies():
    response = client.get("/api/system/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert "distro_family" in data
    assert "pkg_manager" in data
    assert "setup_command" in data
    assert "tools" in data
    assert len(data["tools"]) >= 20


def test_package_adapter_idempotent_git():
    from hackingtool.web.package_adapter import adapt_install_command
    cmd = "git clone https://github.com/foo/bar.git && cd bar && ./install.sh"
    adapted = adapt_install_command(cmd)
    assert "git pull" in adapted
    assert "cd bar" in adapted


def test_package_adapter_anonsurf_atomic():
    from hackingtool.web.package_adapter import adapt_install_command
    cmd = "git clone https://github.com/Und3rf10w/kali-anonsurf.git && cd kali-anonsurf && sudo ./installer.sh"
    adapted = adapt_install_command(cmd, pkg_manager="pacman")
    assert "anonsurf-arch" in adapted
    assert "sudo pacman -S --needed --noconfirm" in adapted


def test_api_system_wireshark():
    response = client.get("/api/system/wireshark")
    assert response.status_code == 200
    data = response.json()
    assert "installed" in data
    assert "in_group" in data
    assert "fix_command" in data
    assert "user" in data
