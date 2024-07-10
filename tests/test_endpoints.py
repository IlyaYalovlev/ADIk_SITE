import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_read_main(ac: AsyncClient):
    response = await ac.get("/")
    assert response.status_code == 200
    assert "products" in response.text

@pytest.mark.asyncio
async def test_login_form(ac: AsyncClient):
    response = await ac.get("/login")
    assert response.status_code == 200
    assert "<form" in response.text

@pytest.mark.asyncio
async def test_login(ac: AsyncClient):
    login_data = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    response = await ac.post("/login", data=login_data)
    assert response.status_code == 401
    assert response.json()["error"] == "Неверные учетные данные"
