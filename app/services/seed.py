"""Demo data seeding."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus
from app.core.time import utcnow
from app.repositories.models import OrderItemRow, OrderRow, ProductRow


async def seed_demo_data(session: AsyncSession) -> None:
    """Insert missing demo rows without changing existing orders or products."""
    now = utcnow()
    products = [
        ProductRow(
            sku="SKU-HEADSET",
            name="Noise-Canceling Headphones",
            category="Electronics",
            price_cents=29900,
            inventory=42,
            tags="headphones,noise-canceling",
            description="Over-ear wireless headphones with active noise cancellation",
        ),
        ProductRow(
            sku="SKU-MUG-CUSTOM",
            name="Custom Ceramic Mug",
            category="Home",
            price_cents=3900,
            inventory=200,
            tags="custom,mug",
            description="Personalized ceramic mug; custom items are not eligible for change-of-mind returns after production begins",
        ),
        ProductRow(
            sku="SKU-TEE",
            name="Cotton T-Shirt",
            category="Apparel",
            price_cents=7900,
            inventory=0,
            tags="apparel,basic",
            description="Classic short-sleeve cotton t-shirt",
        ),
    ]
    for product in products:
        if await session.get(ProductRow, product.sku) is None:
            session.add(product)
    orders = [
        OrderRow(
            order_id="ORD10001",
            user_id="u_demo",
            status=OrderStatus.SHIPPED.value,
            total_cents=29900,
            created_at=now - timedelta(days=3),
            paid_at=now - timedelta(days=3),
            shipped_at=now - timedelta(days=2),
            tracking_no="SF1234567890",
            receiver_city="Seattle",
        ),
        OrderRow(
            order_id="ORD10002",
            user_id="u_demo",
            status=OrderStatus.DELIVERED.value,
            total_cents=3900,
            created_at=now - timedelta(days=20),
            paid_at=now - timedelta(days=20),
            shipped_at=now - timedelta(days=19),
            delivered_at=now - timedelta(days=12),
            tracking_no="YT998877",
            receiver_city="New York",
        ),
        OrderRow(
            order_id="ORD10003",
            user_id="u_demo",
            status=OrderStatus.PAID.value,
            total_cents=7900,
            created_at=now - timedelta(hours=5),
            paid_at=now - timedelta(hours=5),
            receiver_city="Austin",
        ),
    ]
    for order in orders:
        if await session.get(OrderRow, order.order_id) is None:
            session.add(order)
    items = [
        OrderItemRow(
            order_id="ORD10001",
            sku="SKU-HEADSET",
            name="Noise-Canceling Headphones",
            quantity=1,
            unit_price_cents=29900,
            customized=False,
        ),
        OrderItemRow(
            order_id="ORD10002",
            sku="SKU-MUG-CUSTOM",
            name="Custom Ceramic Mug",
            quantity=1,
            unit_price_cents=3900,
            customized=True,
        ),
        OrderItemRow(
            order_id="ORD10003",
            sku="SKU-TEE",
            name="Cotton T-Shirt",
            quantity=1,
            unit_price_cents=7900,
            customized=False,
        ),
    ]
    existing_items = set(
        (await session.execute(select(OrderItemRow.order_id, OrderItemRow.sku))).all()
    )
    session.add_all(item for item in items if (item.order_id, item.sku) not in existing_items)
