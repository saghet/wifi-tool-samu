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


def test_package_adapter_arch():
    from hackingtool.web.package_adapter import adapt_install_command
    arch_cmd = adapt_install_command("sudo apt-get install -y proxychains4", pkg_manager="pacman")
    assert "pacman -S" in arch_cmd
    assert "proxychains-ng" in arch_cmd
