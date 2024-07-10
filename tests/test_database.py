import pytest
from sqlalchemy import select
from app.models import Users, Stock, Product
from app.database import get_db

@pytest.mark.asyncio
async def test_create_user(prepare_database, async_session_maker_fixture, clear_database):
    async with async_session_maker_fixture() as session:
        new_user = Users(
            email="testuser@example.com",
            first_name="Test",
            last_name="User",
            phone="1234567890",
            password_hash="hashedpassword",
            user_type="customer"
        )
        session.add(new_user)
        await session.commit()

        query = await session.execute(select(Users).filter_by(email="testuser@example.com"))
        user = query.scalars().first()
        assert user is not None
        assert user.first_name == "Test"

@pytest.mark.asyncio
async def test_create_stock(prepare_database, async_session_maker_fixture, clear_database):
    async with async_session_maker_fixture() as session:
        # Создаем продукт для использования в тесте
        new_product = Product(
            product_id="test_product",
            brand="TestBrand",
            category="TestCategory",
            model_name="TestModel",
            color="TestColor",
            price="100.0",
            discount="80.0",
            image_side_url="http://example.com/side.jpg",
            image_top_url="http://example.com/top.jpg",
            image_34_url="http://example.com/34.jpg",
            gender="unisex"
        )
        session.add(new_product)
        await session.commit()

        # Создаем пользователя для использования в тесте
        new_user = Users(
            email="seller@example.com",
            first_name="Seller",
            last_name="User",
            phone="0987654321",
            password_hash="hashedpassword",
            user_type="seller"
        )
        session.add(new_user)
        await session.commit()

        query = await session.execute(select(Users).filter_by(email="seller@example.com"))
        user = query.scalars().first()

        new_stock = Stock(
            product_id=new_product.product_id,
            seller_id=user.id,  # Используем id созданного пользователя
            size=10.0,
            quantity=10,
            price=100.0,
            discount_price=80.0
        )
        session.add(new_stock)
        await session.commit()

        query = await session.execute(select(Stock).filter_by(product_id="test_product"))
        stock = query.scalars().first()
        assert stock is not None
        assert stock.size == 10.0
