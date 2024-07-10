import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register(ac: AsyncClient):
    register_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": "testuser@example.com",
        "phone": "1234567890",
        "password": "TestPassword123!",
        "confirm_password": "TestPassword123!",
        "role": "customer"
    }
    response = await ac.post("/register", data=register_data)
    assert response.status_code == 200
    assert "Перейдите в почту для завершения регистрации" in response.json()["message"]

@pytest.mark.asyncio
async def test_user_info_unauthorized(ac: AsyncClient):
    response = await ac.get("/user-info")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid Authorization header"
