"""
Assignment 3: Order Data Processing System
"""

import csv
import json
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────
# PART 1: Data Modeling
# ──────────────────────────────────────────────

@dataclass
class Product:
    """Бір өнімді сипаттайтын класс."""
    product_id: str
    name: str
    category: str
    price: float
    is_active: bool


@dataclass
class Order:
    """Бір тапсырысты сипаттайтын класс."""
    order_id: str
    user_id: str
    product_id: str
    quantity: int
    timestamp: str
    price_at_purchase: Optional[float]  # болмауы мүмкін (None)
    effective_price: float = field(default=0.0, init=False)  # шешілген баға


def load_products(filepath: str) -> dict[str, Product]:
    """
    products.json файлын оқып, {product_id: Product} сөздігін қайтарады.
    O(1) іздеу үшін dict қолданамыз.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    products: dict[str, Product] = {}
    for item in data:
        p = Product(
            product_id=item["product_id"],
            name=item["name"],
            category=item["category"],
            price=float(item["price"]),
            is_active=item["is_active"],
        )
        products[p.product_id] = p
    return products


def load_orders(filepath: str) -> list[Order]:
    """
    orders.csv файлын оқып, Order объектілер тізімін қайтарады.
    Бұзылған жолдарды өткізіп жібереді.
    """
    orders: list[Order] = []

    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                quantity = int(row["quantity"])
            except (ValueError, KeyError):
                quantity = 0  # сандық емес болса 0 деп санаймыз → кейін invalid болады

            # price_at_purchase: бос немесе қате болуы мүмкін
            raw_price = row.get("price_at_purchase", "").strip()
            try:
                price_at_purchase = float(raw_price) if raw_price else None
            except ValueError:
                price_at_purchase = None

            order = Order(
                order_id=row.get("order_id", ""),
                user_id=row.get("user_id", ""),
                product_id=row.get("product_id", ""),
                quantity=quantity,
                timestamp=row.get("timestamp", ""),
                price_at_purchase=price_at_purchase,
            )
            orders.append(order)

    return orders


# ──────────────────────────────────────────────
# PART 2: Validation and Price Resolution
# ──────────────────────────────────────────────

def validate_and_resolve(
    orders: list[Order],
    products: dict[str, Product],
) -> tuple[list[Order], list[Order]]:
    """
    Тапсырыстарды тексеріп, жарамды және жарамсыздарға бөледі.

    Жарамсыз болатын жағдайлар:
      - product_id каталогта жоқ
      - баға екеуі де жоқ немесе жарамсыз
      - quantity <= 0
    """
    valid: list[Order] = []
    invalid: list[Order] = []

    for order in orders:
        # 1) Өнім каталогта бар ма?
        product = products.get(order.product_id)
        if product is None:
            invalid.append(order)
            continue

        # 2) Саны дұрыс па?
        if order.quantity <= 0:
            invalid.append(order)
            continue

        # 3) Бағаны шешу
        if order.price_at_purchase is not None and order.price_at_purchase > 0:
            order.effective_price = order.price_at_purchase
        elif product.price and product.price > 0:
            order.effective_price = product.price
        else:
            # Екі жерде де баға жоқ → жарамсыз
            invalid.append(order)
            continue

        valid.append(order)

    return valid, invalid


# ──────────────────────────────────────────────
# PART 3: Aggregation and Reporting
# ──────────────────────────────────────────────

def compute_report(
    valid_orders: list[Order],
    products: dict[str, Product],
) -> dict:
    """
    Жарамды тапсырыстар бойынша есеп есептейді.
    Бір ғана өтімде (single pass) барлығын есептейді — тиімді!
    """
    total_revenue = 0.0
    revenue_by_category: dict[str, float] = {}
    revenue_by_product: dict[str, float] = {}

    for order in valid_orders:
        product = products[order.product_id]  # O(1)
        revenue = order.effective_price * order.quantity

        # Жалпы табыс
        total_revenue += revenue

        # Санат бойынша табыс
        revenue_by_category[product.category] = (
            revenue_by_category.get(product.category, 0.0) + revenue
        )

        # Өнім бойынша табыс
        revenue_by_product[order.product_id] = (
            revenue_by_product.get(order.product_id, 0.0) + revenue
        )

    # Ең жоғары табысты 3 өнім
    top3_ids = sorted(revenue_by_product, key=lambda pid: revenue_by_product[pid], reverse=True)[:3]
    top_products = [
        {
            "product_id": pid,
            "name": products[pid].name,
            "revenue": round(revenue_by_product[pid], 2),
        }
        for pid in top3_ids
    ]

    return {
        "total_revenue": round(total_revenue, 2),
        "revenue_by_category": {k: round(v, 2) for k, v in revenue_by_category.items()},
        "top_products": top_products,
    }


def export_report(report: dict, filepath: str) -> None:
    """Есепті JSON файлына жазады."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Есеп сақталды: {filepath}")


# ──────────────────────────────────────────────
# MAIN — бәрін біріктіреміз
# ──────────────────────────────────────────────

def main():
    # Файл жолдары (қажет болса өзгерт)
    products_path = "products.json"
    orders_path = "orders.csv"
    report_path = "report.json"

    # 1. Деректерді жүктеу
    print("Деректер жүктелуде...")
    products = load_products(products_path)
    orders = load_orders(orders_path)
    print(f"  Өнімдер: {len(products)}, Тапсырыстар: {len(orders)}")

    # 2. Тексеру және баға шешу
    valid_orders, invalid_orders = validate_and_resolve(orders, products)
    print(f"  Жарамды: {len(valid_orders)}, Жарамсыз: {len(invalid_orders)}")

    # 3. Есеп есептеу
    report = compute_report(valid_orders, products)
    print(f"  Жалпы табыс: {report['total_revenue']}")

    # 4. Файлға шығару
    export_report(report, report_path)


if __name__ == "__main__":
    main()