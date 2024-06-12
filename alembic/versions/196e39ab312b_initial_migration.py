"""initial migration

Revision ID: 196e39ab312b
Revises: 
Create Date: 2024-06-12 17:25:31.281791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '196e39ab312b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Получаем объект MetaData
    metadata = sa.MetaData()
    connection = op.get_bind()
    metadata.reflect(bind=connection)

    # Проверяем наличие таблицы и ее структуру
    if 'adidas_products' in metadata.tables:
        adidas_products = metadata.tables['adidas_products']

        # Проверяем, что структура столбцов соответствует ожидаемой
        expected_columns = {
            'product_id': sa.String(),
            'brand': sa.String(),
            'category': sa.String(),
            'model_name': sa.String(),
            'color': sa.String(),
            'price': sa.String(),
            'discount': sa.String(),
            'image_side_url': sa.String(),
            'image_top_url': sa.String(),
            'image_34_url': sa.String(),
            'gender': sa.String()
        }

        for column in adidas_products.columns:
            if column.name not in expected_columns or not isinstance(column.type, expected_columns[column.name].__class__):
                return  # Если структура не соответствует ожидаемой, выходим

def downgrade() -> None:
    # Ничего не делаем при откате миграции
    pass
