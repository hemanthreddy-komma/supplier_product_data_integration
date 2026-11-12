"""
Enterprise-Grade Real-Time Supplier Feed Generator
Generates substantial, highly realistic, multi-supplier e-commerce feeds with:
- Recognized commercial brand products (Apple, Sony, Samsung, Dell, Bose, LG, Nintendo, Logitech, DJI, GoPro, Canon, Dyson, Asus, Lenovo)
- Valid GS1 Modulo-10 GTIN/UPC/EAN barcodes
- Multi-supplier price and timestamp conflicts (TechCorp vs GlobalSupply vs ApexGoods)
- Tier 2 Brand+MPN fallback matching (where GTIN is omitted by one supplier)
- Missing attribute fallback test cases (descriptions supplied by secondary vendor)
- Deliberate quarantine test records (corrupted check digit, inverted billing, negative stock)
"""

import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

random.seed(42)

WORKSPACE_ROOT = Path(r"C:\CandidateWorkspace\supplier_product_integration\supplier_product_integration")
SCRATCH_ROOT = Path(r"C:\Users\mahit\.gemini\antigravity\scratch\supplier_product_integration")


def make_gs1_gtin13(prefix_12: str) -> str:
    total = 0
    multiplier = 3
    for d in reversed(prefix_12):
        total += int(d) * multiplier
        multiplier = 1 if multiplier == 3 else 3
    check = (10 - (total % 10)) % 10
    return prefix_12 + str(check)


# 25 High-Profile Commercial Products
PRODUCTS = [
    {
        "gtin": make_gs1_gtin13("019425391234"),
        "brand": "Apple",
        "mpn": "MU773LL/A",
        "name": "Apple iPhone 15 Pro Max 256GB Natural Titanium",
        "category": "Smartphones & Mobile Devices",
        "price_a": 1199.00,
        "price_b": 1149.00,
        "price_c": 1099.99,
        "stock_a": 120, "stock_b": 95, "stock_c": 50,
        "desc": "6.7-inch Super Retina XDR display with ProMotion, A17 Pro chip, Titanium design with textured matte glass back, and 5x Telephoto camera."
    },
    {
        "gtin": make_gs1_gtin13("002724292341"),
        "brand": "Sony",
        "mpn": "WH1000XM5/B",
        "name": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones Black",
        "category": "Audio & Headphones",
        "price_a": 399.99,
        "price_b": 379.50,
        "price_c": 348.00,
        "stock_a": 240, "stock_b": 180, "stock_c": 110,
        "desc": "Two processors control 8 microphones for unprecedented noise cancellation, Auto NC Optimizer, and up to 30-hour battery life."
    },
    {
        "gtin": make_gs1_gtin13("088411643120"),
        "brand": "Dell",
        "mpn": "XPS9530-7412SLV",
        "name": "Dell XPS 15 9530 15.6-inch OLED 3.5K Intel Core i9-13900H 32GB RAM 1TB SSD RTX 4070",
        "category": "Computers & Laptops",
        "price_a": 2499.00,
        "price_b": 2349.00,
        "price_c": 2299.00,
        "stock_a": 45, "stock_b": 30, "stock_c": 20,
        "desc": "Stunning 3.5K OLED InfinityEdge touch display, machined aluminum chassis, carbon fiber palm rest, and NVIDIA GeForce RTX 4070 graphics."
    },
    {
        "gtin": make_gs1_gtin13("088727678129"),
        "brand": "Samsung",
        "mpn": "SM-S928UZKEXAA",
        "name": "Samsung Galaxy S24 Ultra 512GB Titanium Black Unlocked",
        "category": "Smartphones & Mobile Devices",
        "price_a": 1419.99,
        "price_b": 1369.00,
        "price_c": 1320.00,
        "stock_a": 95, "stock_b": 140, "stock_c": 60,
        "desc": "6.8-inch Dynamic AMOLED 2X flat display, Galaxy AI features, titanium frame, embedded S Pen, and 200MP camera with 100x Space Zoom."
    },
    {
        "gtin": make_gs1_gtin13("071919266124"),
        "brand": "LG",
        "mpn": "OLED65C3PUA",
        "name": "LG 65-Inch Class C3 Series OLED evo 4K Processor Smart TV",
        "category": "Televisions & Home Theater",
        "price_a": 1596.99,
        "price_b": 1549.00,
        "price_c": 1499.99,
        "stock_a": 60, "stock_b": 80, "stock_c": 45,
        "desc": "Self-lit OLED evo pixels with Brightness Booster, a9 AI Processor Gen6, 120Hz refresh rate, Dolby Vision, and webOS 23."
    },
    {
        "gtin": make_gs1_gtin13("004549688271"),
        "brand": "Nintendo",
        "mpn": "HEGSKAAAA",
        "name": "Nintendo Switch OLED Model with White Joy-Con",
        "category": "Gaming Consoles",
        "price_a": 349.99,
        "price_b": 329.99,
        "price_c": 319.00,
        "stock_a": 180, "stock_b": 210, "stock_c": 90,
        "desc": "Vibrant 7-inch OLED screen, wide adjustable stand, wired LAN dock, 64GB internal storage, and enhanced audio in handheld mode."
    },
    {
        "gtin": make_gs1_gtin13("019594901235"),
        "brand": "Apple",
        "mpn": "MUW63LL/A",
        "name": "Apple MacBook Pro 16-inch M3 Max 36GB Unified Memory 1TB SSD Space Black",
        "category": "Computers & Laptops",
        "price_a": 3499.00,
        "price_b": 3399.00,
        "price_c": 3299.00,
        "stock_a": 35, "stock_b": 25, "stock_c": 15,
        "desc": "Liquid Retina XDR display with extreme dynamic range, M3 Max chip with 14-core CPU and 30-core GPU, up to 22 hours of battery life."
    },
    {
        "gtin": make_gs1_gtin13("001781784318"),
        "brand": "Bose",
        "mpn": "880066-0100",
        "name": "Bose QuietComfort Ultra Wireless Over-Ear Noise Cancelling Headphones",
        "category": "Audio & Headphones",
        "price_a": 429.00,
        "price_b": 399.00,
        "price_c": 379.00,
        "stock_a": 150, "stock_b": 110, "stock_c": 75,
        "desc": "World-class noise cancellation, breakthrough spatialized audio with Bose Immersive Audio, and CustomTune technology."
    },
    {
        "gtin": make_gs1_gtin13("009785517457"),
        "brand": "Logitech",
        "mpn": "910-006556",
        "name": "Logitech MX Master 3S Performance Wireless Ergonomic Mouse Graphite",
        "category": "Computer Accessories",
        "price_a": 99.99,
        "price_b": 89.99,
        "price_c": 84.50,
        "stock_a": 320, "stock_b": 290, "stock_c": 160,
        "desc": "8K DPI sensor tracks on glass, Quiet Clicks technology, MagSpeed electromagnetic scrolling, and multi-device Flow cross-computer control."
    },
    {
        "gtin": make_gs1_gtin13("002724292558"),
        "brand": "Sony",
        "mpn": "CFI-2000A01",
        "name": "Sony PlayStation 5 Slim Console Disk Edition 1TB",
        "category": "Gaming Consoles",
        "price_a": 499.99,
        "price_b": 479.00,
        "price_c": 469.00,
        "stock_a": 110, "stock_b": 140, "stock_c": 80,
        "desc": "Slimmer profile with 1TB SSD storage, ultra-high speed SSD, ray tracing, 4K-TV gaming, HDR technology, and DualSense haptic feedback."
    },
    {
        "gtin": make_gs1_gtin13("019002100812"),
        "brand": "DJI",
        "mpn": "CP.MA.00000731.01",
        "name": "DJI Mini 4 Pro Drone with DJI RC 2 Controller Fly More Combo",
        "category": "Drones & Aerial Imaging",
        "price_a": 1099.00,
        "price_b": 1049.00,
        "price_c": 999.00,
        "stock_a": 55, "stock_b": 40, "stock_c": 25,
        "desc": "Sub-249g ultralight drone with omnidirectional obstacle sensing, 4K/60fps HDR true vertical shooting, and 20km FHD video transmission."
    },
    {
        "gtin": make_gs1_gtin13("081827902994"),
        "brand": "GoPro",
        "mpn": "CHDHX-121-CN",
        "name": "GoPro HERO12 Black Waterproof Action Camera 5.3K60 Video",
        "category": "Cameras & Camcorders",
        "price_a": 399.99,
        "price_b": 369.00,
        "price_c": 349.00,
        "stock_a": 140, "stock_b": 170, "stock_c": 85,
        "desc": "HyperSmooth 6.0 video stabilization, HDR video and photo, 5.3K60 resolution, rugged waterproof design down to 33ft, and Bluetooth audio support."
    },
    {
        "gtin": make_gs1_gtin13("001380334816"),
        "brand": "Canon",
        "mpn": "5122C002",
        "name": "Canon EOS R6 Mark II Full-Frame Mirrorless Camera Body",
        "category": "Cameras & Camcorders",
        "price_a": 2299.00,
        "price_b": 2199.00,
        "price_c": 2099.00,
        "stock_a": 40, "stock_b": 35, "stock_c": 18,
        "desc": "24.2 MP full-frame CMOS sensor, 40 fps electronic shutter, Dual Pixel CMOS AF II with subject tracking, and 4K60p 10-bit internal video."
    },
    {
        "gtin": make_gs1_gtin13("088560902813"),
        "brand": "Dyson",
        "mpn": "368340-01",
        "name": "Dyson V15 Detect Absolute Cordless Vacuum Cleaner Yellow/Iron",
        "category": "Home Appliances",
        "price_a": 749.99,
        "price_b": 699.99,
        "price_c": 679.00,
        "stock_a": 75, "stock_b": 90, "stock_c": 40,
        "desc": "Laser reveals invisible microscopic dust, piezo sensor measures dust particles, LCD screen shows proof of deep clean, up to 60 min runtime."
    },
    {
        "gtin": make_gs1_gtin13("019710543217"),
        "brand": "Asus",
        "mpn": "GU605MY-XS96",
        "name": "Asus ROG Zephyrus G16 OLED 240Hz Gaming Laptop Intel Core Ultra 9 32GB 2TB RTX 4080",
        "category": "Computers & Laptops",
        "price_a": 2899.99,
        "price_b": 2799.00,
        "price_c": 2699.00,
        "stock_a": 30, "stock_b": 22, "stock_c": 12,
        "desc": "16-inch 2.5K OLED 240Hz ROG Nebula Display, CNC aluminum unibody with Slash Lighting, and vapor chamber cooling."
    },
    {
        "gtin": make_gs1_gtin13("019589201994"),
        "brand": "Lenovo",
        "mpn": "21KC0008US",
        "name": "Lenovo ThinkPad X1 Carbon Gen 12 Intel Core Ultra 7 155H 32GB 1TB SSD",
        "category": "Computers & Laptops",
        "price_a": 1899.00,
        "price_b": 1799.00,
        "price_c": 1749.00,
        "stock_a": 65, "stock_b": 50, "stock_c": 30,
        "desc": "Legendary carbon fiber and magnesium ultralight chassis, Communications Bar with 8MP MIPI camera, Intel Evo platform, and OLED display."
    },
    {
        "gtin": make_gs1_gtin13("088727675548"),
        "brand": "Samsung",
        "mpn": "LS49CG954SNXZA",
        "name": "Samsung 49-Inch Odyssey OLED G9 Curved Dual QHD 240Hz 0.03ms Gaming Monitor",
        "category": "Computer Accessories",
        "price_a": 1399.99,
        "price_b": 1329.00,
        "price_c": 1279.00,
        "stock_a": 40, "stock_b": 35, "stock_c": 20,
        "desc": "Curved 1800R OLED screen with Neo Quantum Processor Pro, 240Hz refresh rate, 0.03ms response time, DisplayHDR True Black 400."
    },
    {
        "gtin": make_gs1_gtin13("084806106625"),
        "brand": "Anker",
        "mpn": "A1336011",
        "name": "Anker Prime 20000mAh Power Bank 200W Output with Smart Digital Display",
        "category": "Accessories & Power",
        "price_a": 129.99,
        "price_b": 119.00,
        "price_c": 109.99,
        "stock_a": 260, "stock_b": 310, "stock_c": 190,
        "desc": "200W total output with dual USB-C ports delivering up to 100W each, ultra-compact design, and smart digital display showing battery telemetry."
    },
    {
        "gtin": make_gs1_gtin13("061510435889"),
        "brand": "Sennheiser",
        "mpn": "700019",
        "name": "Sennheiser HD 660S2 Open-Back High-End Audiophile Headphones",
        "category": "Audio & Headphones",
        "price_a": 599.95,
        "price_b": 569.00,
        "price_c": 539.00,
        "stock_a": 50, "stock_b": 42, "stock_c": 25,
        "desc": "Refined acoustic transducers delivering intimate sound with deep, impactful sub-bass and exceptional resolution for studio mastering."
    },
    {
        "gtin": make_gs1_gtin13("019638820418"),
        "brand": "Microsoft",
        "mpn": "EP2-00001",
        "name": "Microsoft Surface Pro 10 for Business 13-inch Core Ultra 7 165U 16GB 512GB Platinum",
        "category": "Computers & Laptops",
        "price_a": 1699.99,
        "price_b": 1629.00,
        "price_c": 1589.00,
        "stock_a": 70, "stock_b": 85, "stock_c": 35,
        "desc": "Ultra-versatile 2-in-1 with Intel Core Ultra processing, NPU for AI workloads, PixelSense Flow touchscreen with anti-reflective coating."
    },
    {
        "gtin": make_gs1_gtin13("019425389146"),
        "brand": "Apple",
        "mpn": "MRFW3LL/A",
        "name": "Apple Watch Ultra 2 GPS + Cellular 49mm Titanium Case with Ocean Band",
        "category": "Wearables & Smartwatches",
        "price_a": 799.00,
        "price_b": 769.00,
        "price_c": 749.00,
        "stock_a": 90, "stock_b": 115, "stock_c": 55,
        "desc": "Rugged 49mm aerospace-grade titanium case, brightest 3000-nit display, precision dual-frequency GPS, and up to 36-hour normal battery life."
    },
    {
        "gtin": make_gs1_gtin13("002724292882"),
        "brand": "Sony",
        "mpn": "HT-A9000",
        "name": "Sony BRAVIA Theatre Bar 9 Flagship Dolby Atmos Soundbar with 13 Speaker Units",
        "category": "Televisions & Home Theater",
        "price_a": 1399.99,
        "price_b": 1349.00,
        "price_c": 1299.00,
        "stock_a": 35, "stock_b": 40, "stock_c": 15,
        "desc": "360 Spatial Sound Mapping with 13 speaker units, Dolby Atmos, DTS:X, HDMI 2.1 pass-through with 8K and 4K120 support."
    },
    {
        "gtin": make_gs1_gtin13("084013603417"),
        "brand": "Sonos",
        "mpn": "E30G1US1BLK",
        "name": "Sonos Era 300 Premium Smart Speaker with Dolby Atmos Spatial Audio Black",
        "category": "Audio & Headphones",
        "price_a": 449.00,
        "price_b": 429.00,
        "price_c": 399.00,
        "stock_a": 115, "stock_b": 95, "stock_c": 60,
        "desc": "Revolutionary design with six optimal drivers projecting sound from wall to wall and floor to ceiling for true spatial audio."
    },
    {
        "gtin": make_gs1_gtin13("004240605178"),
        "brand": "Shure",
        "mpn": "SM7B",
        "name": "Shure SM7B Vocal Dynamic Cardioid Studio Microphone",
        "category": "Audio & Headphones",
        "price_a": 399.00,
        "price_b": 389.00,
        "price_c": 369.00,
        "stock_a": 160, "stock_b": 190, "stock_c": 95,
        "desc": "Legendary smooth, flat, wide-range frequency response suitable for broadcast, podcasting, voiceover, and studio vocal recording."
    },
    {
        "gtin": make_gs1_gtin13("084000664019"),
        "brand": "Elgato",
        "mpn": "10GBA9901",
        "name": "Elgato Stream Deck MK.2 Studio Controller with 15 Customizable LCD Keys",
        "category": "Computer Accessories",
        "price_a": 149.99,
        "price_b": 139.00,
        "price_c": 129.99,
        "stock_a": 220, "stock_b": 180, "stock_c": 130,
        "desc": "15 customizable LCD keys to trigger unlimited actions, tactile feedback, swappable faceplates, and seamless integration with streaming tools."
    }
]


def generate_feeds():
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # =========================================================================
    # 1. SUPPLIER A (TechCorp Electronics - JSON)
    # Priority 1 (High Trust Catalog)
    # =========================================================================
    feed_a = []
    # Include 22 normal products
    for i, p in enumerate(PRODUCTS[:22]):
        feed_a.append({
            "sku_id": f"TC-{p['brand'][:3].upper()}-{i+101}",
            "product_title": p["name"],
            "barcode_gtin": p["gtin"],
            "brand_name": p["brand"],
            "manufacturer_pn": p["mpn"],
            "cost_usd": p["price_a"],
            "inventory_count": p["stock_a"],
            "category_hierarchy": p["category"],
            "timestamp": now_iso,
            "description": p["desc"]
        })

    # Intentional Quarantine Cases for Supplier A:
    # QA-1: Corrupted GTIN Checksum with no fallback
    feed_a.append({
        "sku_id": "TC-ERR-CHECKSUM",
        "product_title": "Defective Barcode Item With Altered Last Digit",
        "barcode_gtin": "019425391238", # Checksum should be 5, not 8!
        "brand_name": None,
        "manufacturer_pn": None,
        "cost_usd": 899.00,
        "inventory_count": 10,
        "category_hierarchy": "Smartphones & Mobile Devices",
        "timestamp": now_iso,
        "description": "Should be quarantined because GS1 modulo-10 checksum fails."
    })
    # QA-2: Missing Mandatory Product Title
    feed_a.append({
        "sku_id": "TC-ERR-NONAME",
        "product_title": "   ", # Blank name!
        "barcode_gtin": make_gs1_gtin13("099999999999"),
        "brand_name": "GenericCo",
        "manufacturer_pn": "ERR-NONAME",
        "cost_usd": 150.00,
        "inventory_count": 5,
        "category_hierarchy": "General",
        "timestamp": now_iso,
        "description": "Should be quarantined because product title is empty."
    })

    # =========================================================================
    # 2. SUPPLIER B (GlobalSupply Wholesale - CSV)
    # Priority 2 (Wholesale Catalog)
    # =========================================================================
    feed_b = []
    # Include 23 products, overlapping with A
    for i, p in enumerate(PRODUCTS[2:25]):
        # Test Tier 2 fallback: For 3 products, omit UPC so matching must rely on Brand + MPN!
        upc_val = "" if i in [2, 5, 8] else p["gtin"]
        feed_b.append({
            "part_number": f"GS-{p['mpn']}",
            "product_description": f"{p['name']} (Commercial Pack)",
            "upc": upc_val,
            "make": p["brand"],
            "model_no": p["mpn"],
            "wholesale_price": p["price_b"],
            "stock_level": p["stock_b"],
            "product_dept": f"Wholesale / {p['category']}",
            "last_updated": now_str,
            "long_description": f"Bulk distributor packaged: {p['desc']}"
        })

    # Intentional Quarantine Cases for Supplier B:
    # QB-1: Inverted Billing (Negative Price)
    feed_b.append({
        "part_number": "GS-ERR-NEGPRICE",
        "product_description": "Inverted Accounting Defective Hardware",
        "upc": make_gs1_gtin13("088888888888"),
        "make": "HardwareCo",
        "model_no": "ERR-NEG-P",
        "wholesale_price": -189.99,
        "stock_level": 25,
        "product_dept": "Clearance",
        "last_updated": now_str,
        "long_description": "Should be quarantined because price is negative."
    })
    # QB-2: Negative Stock / Backorder glitch
    feed_b.append({
        "part_number": "GS-ERR-NEGSTOCK",
        "product_description": "Backorder Overdraft Inventory Error",
        "upc": make_gs1_gtin13("077777777777"),
        "make": "LogisticsCo",
        "model_no": "ERR-NEG-S",
        "wholesale_price": 49.99,
        "stock_level": -45,
        "product_dept": "Clearance",
        "last_updated": now_str,
        "long_description": "Should be quarantined because stock cannot be negative."
    })

    # =========================================================================
    # 3. SUPPLIER C (ApexGoods Discount - JSON)
    # Priority 3 (Discount Retailer)
    # =========================================================================
    feed_c = []
    # Overlapping products with conflicting discount prices
    for i, p in enumerate(PRODUCTS[5:23]):
        # Test attribute fallback: For some products, leave item_details empty so it falls back to Supplier A or B
        desc_val = None if i in [1, 4, 7] else f"Apex discounted deal: {p['name']}"
        feed_c.append({
            "item_ref": f"APEX-{p['mpn'][:6]}-{i+50}",
            "name": f"{p['name']} [Promo]",
            "ean_13": p["gtin"],
            "brand": p["brand"],
            "mpn": p["mpn"],
            "retail_price": p["price_c"],
            "qty_available": p["stock_c"],
            "category_path": p["category"],
            "feed_timestamp": now_iso,
            "item_details": desc_val
        })

    # Intentional Quarantine Cases for Supplier C:
    # QC-1: Missing all identifiers (no GTIN, brand, or MPN)
    feed_c.append({
        "item_ref": "APEX-ERR-NOIDENT",
        "name": "Mystery Clearance Gadget With Zero Identifiers",
        "ean_13": None,
        "brand": None,
        "mpn": None,
        "retail_price": 29.99,
        "qty_available": 100,
        "category_path": "Clearance",
        "feed_timestamp": now_iso,
        "item_details": "Should be quarantined because no barcode or Brand+MPN exists."
    })

    # =========================================================================
    # 4. EXCEL DISTRIBUTOR FEED (.xlsx)
    # Enterprise Distributor Spreadsheet
    # =========================================================================
    feed_excel = []
    for i, p in enumerate(PRODUCTS[:16]):
        feed_excel.append({
            "part_number": f"DIST-{p['mpn']}",
            "product_description": f"{p['name']} (Distributor Lot)",
            "upc": p["gtin"],
            "make": p["brand"],
            "model_no": p["mpn"],
            "wholesale_price": round(p["price_b"] * 0.98, 2),
            "stock_level": p["stock_b"] + 50,
            "product_dept": p["category"],
            "last_updated": now_str,
            "long_description": p["desc"]
        })

    # Write files to both workspace and scratch
    targets = [WORKSPACE_ROOT, SCRATCH_ROOT]
    for root in targets:
        raw_dir = root / "data" / "raw"
        demo_dir = root / "demo_feeds"
        raw_dir.mkdir(parents=True, exist_ok=True)
        demo_dir.mkdir(parents=True, exist_ok=True)

        # 1. Supplier A JSON
        for pth in [raw_dir / "supplier_a.json", demo_dir / "realtime_supplier_a_techcorp.json"]:
            with open(pth, "w", encoding="utf-8") as f:
                json.dump(feed_a, f, indent=2)

        # 2. Supplier B CSV
        for pth in [raw_dir / "supplier_b.csv", demo_dir / "realtime_supplier_b_globalsupply.csv"]:
            with open(pth, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(feed_b[0].keys()))
                writer.writeheader()
                writer.writerows(feed_b)

        # 3. Supplier C JSON
        for pth in [raw_dir / "supplier_c.json", demo_dir / "realtime_supplier_c_apexgoods.json"]:
            with open(pth, "w", encoding="utf-8") as f:
                json.dump(feed_c, f, indent=2)

        # 4. Supplier Excel Feed
        df_excel = pd.DataFrame(feed_excel)
        for pth in [demo_dir / "realtime_supplier_excel_distributor.xlsx", demo_dir / "supplier_feed_sample.xlsx"]:
            with pd.ExcelWriter(pth, engine="openpyxl") as writer:
                df_excel.to_excel(writer, index=False, sheet_name="Distributor Products")

    print(f"Generated enterprise real-world feeds successfully!")
    print(f"  • Supplier A: {len(feed_a)} records (22 valid commercial, 2 quarantined)")
    print(f"  • Supplier B: {len(feed_b)} records (23 valid commercial, 2 quarantined, 3 Tier-2 Brand+MPN)")
    print(f"  • Supplier C: {len(feed_c)} records (18 valid commercial, 1 quarantined, attribute fallbacks)")
    print(f"  • Excel Feed: {len(feed_excel)} records (16 commercial products)")


if __name__ == "__main__":
    generate_feeds()
