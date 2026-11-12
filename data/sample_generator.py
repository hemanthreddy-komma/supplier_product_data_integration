import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Fix random seed for strict determinism
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def calculate_gs1_check_digit(digits_without_check: str) -> int:
    """Calculates GS1 modulo-10 check digit."""
    total = 0
    multiplier = 3
    for d in reversed(digits_without_check):
        total += int(d) * multiplier
        multiplier = 1 if multiplier == 3 else 3
    return (10 - (total % 10)) % 10


def generate_valid_gtin13(prefix: int, item_idx: int) -> str:
    core = f"{prefix:03d}{item_idx:09d}"
    check = calculate_gs1_check_digit(core)
    return f"{core}{check}"


def generate_sample_feeds(scale: int = 20):
    print(f"Generating realistic supplier feed datasets (scale={scale})...")
    now = datetime.now(timezone.utc)

    # Identifiers for shared products across suppliers
    gtin_sony = generate_valid_gtin13(300, 101)      # Sony Headphones (GTIN match A & B)
    gtin_macbook = generate_valid_gtin13(300, 102)   # Apple MacBook (GTIN match A, B, C)
    gtin_dell = generate_valid_gtin13(300, 103)      # Dell Monitor (GTIN match B & C)
    # Brand + MPN items (No GTIN):
    # Logitech Mouse: B & C
    # Samsung SSD: A & C

    # =========================================================================
    # 1. Supplier A (TechCorp Electronics - JSON)
    # Priority 1 (Highest)
    # =========================================================================
    supplier_a_items = [
        # Normal Shared Product 1 (Sony Headphones)
        {
            "sku_id": "TC-SONY-001",
            "product_title": "Sony WH-1000XM5 Noise Canceling Headphones (Black)",
            "barcode_gtin": gtin_sony,
            "brand_name": "Sony",
            "manufacturer_pn": "WH1000XM5-BLK",
            "cost_usd": 398.00,
            "inventory_count": 50,
            "category_hierarchy": "Audio > Headphones > Over-Ear",
            "timestamp": (now - timedelta(hours=3)).isoformat(),
            "description": "Premium Sony headphones with dual processors for industry-leading noise cancellation."
        },
        # Normal Shared Product 2 (Apple MacBook) - Supplier A missing description
        {
            "sku_id": "TC-APPL-002",
            "product_title": "Apple MacBook Air 13-inch M2 (Midnight)",
            "barcode_gtin": gtin_macbook,
            "brand_name": "Apple",
            "manufacturer_pn": "MLY33LL/A",
            "cost_usd": 1099.00,
            "inventory_count": 15,
            "category_hierarchy": "Computers > Laptops",
            "timestamp": (now - timedelta(hours=4)).isoformat(),
            "description": None  # Missing description, will fallback to Supplier B
        },
        # Shared Product 3 (Samsung SSD) - No GTIN, test Brand+MPN fallback
        {
            "sku_id": "TC-SMSG-003",
            "product_title": "Samsung 990 PRO 2TB NVMe SSD",
            "barcode_gtin": None,
            "brand_name": "Samsung",
            "manufacturer_pn": "MZ-V9P2T0B/AM",
            "cost_usd": 179.99,
            "inventory_count": 75,
            "category_hierarchy": "Components > Storage > SSD",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "description": "PCIe Gen 4.0 NVMe M.2 internal gaming SSD."
        },
        # Unique Product 4
        {
            "sku_id": "TC-BOSE-004",
            "product_title": "Bose QuietComfort Ultra Wireless Earbuds",
            "barcode_gtin": generate_valid_gtin13(300, 104),
            "brand_name": "Bose",
            "manufacturer_pn": "QC-ULTRA-EARBUD",
            "cost_usd": 299.00,
            "inventory_count": 30,
            "category_hierarchy": "Audio > Earbuds",
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "description": "Breakthrough spatial audio and world-class quiet."
        },
        # Duplicate record within same supplier to test intra-batch idempotency
        {
            "sku_id": "TC-SONY-001-DUP",
            "product_title": "Sony WH-1000XM5 Noise Canceling Headphones (Black)",
            "barcode_gtin": gtin_sony,
            "brand_name": "Sony",
            "manufacturer_pn": "WH1000XM5-BLK",
            "cost_usd": 398.00,
            "inventory_count": 50,
            "category_hierarchy": "Audio > Headphones > Over-Ear",
            "timestamp": (now - timedelta(hours=3)).isoformat(),
            "description": "Duplicate item."
        },
        # Deliberate Invalid 1: Blank Product Name -> QUARANTINE
        {
            "sku_id": "TC-ERR-001",
            "product_title": "   ",
            "barcode_gtin": generate_valid_gtin13(300, 105),
            "brand_name": "Anker",
            "manufacturer_pn": "ANK-737",
            "cost_usd": 99.99,
            "inventory_count": 20,
            "category_hierarchy": "Accessories > Power",
            "timestamp": now.isoformat()
        },
        # Deliberate Invalid 2: Bad GTIN Checksum & Missing MPN -> QUARANTINE
        {
            "sku_id": "TC-ERR-002",
            "product_title": "Belkin USB-C Fast Charger",
            "barcode_gtin": "1234567890128",  # Invalid checksum
            "brand_name": "",
            "manufacturer_pn": "",
            "cost_usd": 24.99,
            "inventory_count": 40,
            "category_hierarchy": "Cables",
            "timestamp": now.isoformat()
        }
    ]

    # =========================================================================
    # 2. Supplier B (GlobalSupply Components - CSV)
    # Priority 2
    # =========================================================================
    supplier_b_rows = [
        # Shared Sony Headphones (Supplier B offers cheaper price $389.00, but A has Priority 1 -> A wins price!)
        {
            "part_number": "GS-SONY-5",
            "product_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headset",
            "upc": gtin_sony,
            "make": "Sony",
            "model_no": "WH1000XM5-BLK",
            "wholesale_price": "389.00",
            "stock_level": "40",
            "product_dept": "Electronics / Consumer Audio",
            "last_updated": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Premium wireless headset with auto noise cancelling optimizer."
        },
        # Shared Apple MacBook (Supplier B provides full description missing in Supplier A)
        {
            "part_number": "GS-APPL-M2",
            "product_description": "Apple MacBook Air 13\" (M2 Chip, 8GB, 256GB SSD) - Midnight",
            "upc": gtin_macbook,
            "make": "Apple",
            "model_no": "MLY33LL/A",
            "wholesale_price": "1049.50",
            "stock_level": "22",
            "product_dept": "Computers / Notebooks",
            "last_updated": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Strikingly thin design with fast M2 processor and up to 18 hours battery life."
        },
        # Shared Dell Monitor with C
        {
            "part_number": "GS-DELL-U27",
            "product_description": "Dell UltraSharp 27 4K USB-C Hub Monitor U2723QE",
            "upc": gtin_dell,
            "make": "Dell",
            "model_no": "U2723QE",
            "wholesale_price": "520.00",
            "stock_level": "18",
            "product_dept": "Displays / Monitors",
            "last_updated": (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Brilliant visuals and contrast on the 27-inch 4K monitor."
        },
        # Shared Logitech Mouse (No GTIN! Matches on Brand + MPN with C)
        {
            "part_number": "GS-LOGI-MX3S",
            "product_description": "Logitech MX Master 3S Performance Wireless Mouse",
            "upc": "",
            "make": "Logitech",
            "model_no": "910-006556",
            "wholesale_price": "92.00",
            "stock_level": "115",
            "product_dept": "Computer Peripherals",
            "last_updated": (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Quiet clicks and 8K DPI tracking on glass surface."
        },
        # Unique Product in B
        {
            "part_number": "GS-KEYB-K380",
            "product_description": "Logitech K380 Multi-Device Bluetooth Keyboard",
            "upc": generate_valid_gtin13(300, 106),
            "make": "Logitech",
            "model_no": "920-007558",
            "wholesale_price": "34.99",
            "stock_level": "60",
            "product_dept": "Computer Peripherals",
            "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Compact wireless keyboard for PC, Mac, iPad, and phone."
        },
        # Deliberate Invalid 3: Negative Price -> QUARANTINE
        {
            "part_number": "GS-ERR-NEGPRICE",
            "product_description": "Defective Hardware Part with Negative Price",
            "upc": generate_valid_gtin13(300, 107),
            "make": "GenericFault",
            "model_no": "FLT-001",
            "wholesale_price": "-29.99",
            "stock_level": "10",
            "product_dept": "Misc",
            "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Must be rejected."
        },
        # Deliberate Invalid 4: Negative Stock -> QUARANTINE
        {
            "part_number": "GS-ERR-NEGSTOCK",
            "product_description": "Hardware with Negative Inventory Level",
            "upc": generate_valid_gtin13(300, 108),
            "make": "GenericFault",
            "model_no": "FLT-002",
            "wholesale_price": "19.99",
            "stock_level": "-5",
            "product_dept": "Misc",
            "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
            "long_description": "Must be rejected."
        }
    ]

    # =========================================================================
    # 3. Supplier C (ApexGoods Consumer Tech - JSON)
    # Priority 3
    # =========================================================================
    supplier_c_items = [
        # Shared Apple MacBook with A and B
        {
            "item_ref": "AG-APPL-M2-MID",
            "name": "Apple MacBook Air Laptop M2 (Midnight 2023)",
            "ean_13": gtin_macbook,
            "brand": "Apple",
            "mpn": "MLY33LL/A",
            "retail_price": 1149.00,
            "qty_available": 10,
            "category_path": "Laptops & Notebooks > Apple Mac",
            "feed_timestamp": (now - timedelta(hours=1)).isoformat(),
            "item_details": "ApexGoods stock of 13-inch Apple Air."
        },
        # Shared Dell Monitor with B
        {
            "item_ref": "AG-DELL-U2723",
            "name": "Dell 27-inch 4K UHD UltraSharp Monitor",
            "ean_13": gtin_dell,
            "brand": "Dell",
            "mpn": "U2723QE",
            "retail_price": 579.99,
            "qty_available": 25,
            "category_path": "Monitors > Professional 4K",
            "feed_timestamp": (now - timedelta(hours=2)).isoformat(),
            "item_details": "4K IPS Black technology with USB hub."
        },
        # Shared Logitech Mouse with B (No GTIN! Brand + MPN matching)
        {
            "item_ref": "AG-LOGI-MX3S-GRY",
            "name": "Logitech MX Master 3S Wireless Mouse - Pale Grey",
            "ean_13": None,
            "brand": "Logitech",
            "mpn": "910-006556",
            "retail_price": 99.99,
            "qty_available": 45,
            "category_path": "Peripherals > Mice",
            "feed_timestamp": (now - timedelta(hours=1)).isoformat(),
            "item_details": "Ergonomic wireless mouse with ultra-fast scroll wheel."
        },
        # Shared Samsung SSD with A (Brand + MPN matching)
        {
            "item_ref": "AG-SMSG-990P",
            "name": "Samsung SSD 990 PRO 2TB Internal Solid State Drive",
            "ean_13": None,
            "brand": "Samsung",
            "mpn": "MZ-V9P2T0B/AM",
            "retail_price": 189.99,
            "qty_available": 70,
            "category_path": "Hard Drives > SSDs",
            "feed_timestamp": (now - timedelta(hours=2)).isoformat(),
            "item_details": "Internal M.2 SSD for gamers and tech professionals."
        },
        # Unique Product in C
        {
            "item_ref": "AG-SONY-V10",
            "name": "Sony PlayStation 5 DualSense Wireless Controller",
            "ean_13": generate_valid_gtin13(300, 109),
            "brand": "Sony",
            "mpn": "CFI-ZCT1W",
            "retail_price": 69.99,
            "qty_available": 35,
            "category_path": "Gaming > Controllers",
            "feed_timestamp": now.isoformat(),
            "item_details": "Haptic feedback and dynamic trigger effects."
        },
        # Deliberate Invalid 5: Missing all identifiers -> QUARANTINE
        {
            "item_ref": "AG-ERR-NO-ID",
            "name": "Mystery Cable with Zero Identifiers",
            "ean_13": None,
            "brand": "",
            "mpn": "",
            "retail_price": 9.99,
            "qty_available": 100,
            "category_path": "Accessories",
            "feed_timestamp": now.isoformat(),
            "item_details": "Lacks GTIN, Brand, and MPN."
        }
    ]

    # Configurable scale generation for 100,000+ performance testing
    if scale > 20:
        categories = ["Electronics > Audio", "Computers > Laptops", "Components > Storage", "Accessories > Cables"]
        brands = ["Apple", "Samsung", "Sony", "Dell", "HP", "Lenovo", "Logitech", "Asus", "Bose", "Anker"]
        for i in range(110, 110 + scale):
            gtin = generate_valid_gtin13(300, i)
            brand = random.choice(brands)
            mpn = f"{brand[:3].upper()}-{i:05d}"
            name = f"{brand} Professional Device Series {i}"
            price = round(random.uniform(25.0, 1800.0), 2)
            stock = random.randint(5, 300)

            supplier_a_items.append({
                "sku_id": f"TC-GEN-{i}",
                "product_title": name,
                "barcode_gtin": gtin,
                "brand_name": brand,
                "manufacturer_pn": mpn,
                "cost_usd": price,
                "inventory_count": stock,
                "category_hierarchy": random.choice(categories),
                "timestamp": now.isoformat(),
                "description": f"Generated product item {i}."
            })

            supplier_b_rows.append({
                "part_number": f"GS-GEN-{i}",
                "product_description": f"{name} (Wholesale Catalog)",
                "upc": gtin,
                "make": brand,
                "model_no": mpn,
                "wholesale_price": str(round(price * 0.94, 2)),
                "stock_level": str(stock + 15),
                "product_dept": "General / Wholesale",
                "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
                "long_description": f"Wholesale description for item {i}."
            })

    # Write Supplier A JSON
    file_a = RAW_DIR / "supplier_a.json"
    with open(file_a, "w", encoding="utf-8") as f:
        json.dump(supplier_a_items, f, indent=2)
    print(f"  -> Written {len(supplier_a_items)} records to {file_a}")

    # Write Supplier B CSV
    file_b = RAW_DIR / "supplier_b.csv"
    with open(file_b, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "part_number", "product_description", "upc", "make", "model_no",
            "wholesale_price", "stock_level", "product_dept", "last_updated", "long_description"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(supplier_b_rows)
    print(f"  -> Written {len(supplier_b_rows)} records to {file_b}")

    # Write Supplier C JSON
    file_c = RAW_DIR / "supplier_c.json"
    with open(file_c, "w", encoding="utf-8") as f:
        json.dump(supplier_c_items, f, indent=2)
    print(f"  -> Written {len(supplier_c_items)} records to {file_c}")

    print("Sample dataset generation successfully finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic supplier product feeds.")
    parser.add_argument("--scale", type=int, default=20, help="Number of records to generate.")
    args = parser.parse_args()
    generate_sample_feeds(scale=args.scale)
