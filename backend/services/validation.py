import logging
from typing import Optional, Tuple
from backend.models.schemas import StandardizedRecord

logger = logging.getLogger(__name__)

VALID_GTIN_LENGTHS = {8, 12, 13, 14}


def validate_gs1_checksum(barcode: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates GS1 Modulo 10 check digit for GTIN-8, GTIN-12 (UPC), GTIN-13 (EAN), GTIN-14.
    Returns (is_valid, normalized_gtin14_str).
    """
    if not barcode:
        return False, None
    
    cleaned = barcode.replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) not in VALID_GTIN_LENGTHS:
        return False, None

    payload = cleaned[:-1]
    expected_check = int(cleaned[-1])

    # Multiply digits alternating by 3 and 1 from right
    total = 0
    multiplier = 3
    for digit in reversed(payload):
        total += int(digit) * multiplier
        multiplier = 1 if multiplier == 3 else 3

    calc_check = (10 - (total % 10)) % 10
    if calc_check == expected_check:
        return True, cleaned.zfill(14)
    
    return False, None


class ValidationService:
    """Validates standardized records and quarantines data quality failures."""

    @classmethod
    def validate_record(cls, record: StandardizedRecord) -> Tuple[bool, Optional[str]]:
        rejection_reasons = []

        # 1. Required Product Name
        if not record.product_name or len(record.product_name.strip()) == 0:
            rejection_reasons.append("MISSING_PRODUCT_NAME: Product name cannot be blank")

        # 2. Positive Price
        if record.price <= 0:
            rejection_reasons.append(f"INVALID_PRICE: Price must be positive, got {record.price}")

        # 3. Non-negative Stock
        if record.stock_quantity < 0:
            rejection_reasons.append(f"INVALID_STOCK: Stock cannot be negative, got {record.stock_quantity}")

        # 4. Valid GTIN or Brand+MPN Combination
        is_valid_gtin, normalized_gtin = validate_gs1_checksum(record.gtin)
        if is_valid_gtin:
            record.gtin = normalized_gtin
        else:
            record.gtin = None

        has_brand_mpn = bool(
            record.brand and record.manufacturer_part_number and
            len(record.brand.strip()) > 0 and len(record.manufacturer_part_number.strip()) > 0
        )

        if not is_valid_gtin and not has_brand_mpn:
            rejection_reasons.append(
                "MISSING_IDENTIFIER: Record must have either a valid GTIN or both Brand and MPN"
            )

        # 5. Timestamp validation
        if not record.observed_at:
            rejection_reasons.append("INVALID_TIMESTAMP: Missing source observation timestamp")

        if rejection_reasons:
            reason_text = " | ".join(rejection_reasons)
            return False, reason_text

        return True, None
