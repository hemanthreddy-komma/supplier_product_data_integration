from collections import defaultdict
import logging
import uuid
from typing import Dict, List, Set
from backend.models.schemas import StandardizedRecord

logger = logging.getLogger(__name__)


def _normalize(val: str) -> str:
    if not val:
        return ""
    return "".join(val.lower().strip().split())


class EntityResolutionService:
    """
    Tier 2 Service: Resolves multi-supplier records into golden product clusters.
    Order:
      1. Exact valid GTIN match
      2. Normalized brand + MPN fallback
      3. Uncertain matches are kept separate
    """

    @classmethod
    def resolve_clusters(cls, records: List[StandardizedRecord]) -> Dict[str, List[StandardizedRecord]]:
        if not records:
            return {}

        # 1. Map (brand, mpn) -> GTINs
        brand_mpn_to_gtins: Dict[str, Set[str]] = defaultdict(set)
        for r in records:
            if r.gtin and r.brand and r.manufacturer_part_number:
                b_key = f"{_normalize(r.brand)}::{_normalize(r.manufacturer_part_number)}"
                brand_mpn_to_gtins[b_key].add(r.gtin)

        # 2. Cluster grouping
        clusters: Dict[str, List[StandardizedRecord]] = defaultdict(list)
        for r in records:
            if r.gtin:
                cluster_key = f"gtin:{r.gtin}"
            elif r.brand and r.manufacturer_part_number:
                b_key = f"{_normalize(r.brand)}::{_normalize(r.manufacturer_part_number)}"
                known_gtins = brand_mpn_to_gtins.get(b_key, set())
                # Unambiguous single GTIN cross-reference
                if len(known_gtins) == 1:
                    cluster_key = f"gtin:{next(iter(known_gtins))}"
                else:
                    cluster_key = f"brand_mpn:{b_key}"
            else:
                # Do not merge uncertain matches automatically
                cluster_key = f"unmatched:{r.raw_record_id}"

            # Deterministic product_id (UUIDv5)
            product_id = str(uuid.uuid5(uuid.NAMESPACE_OID, cluster_key))
            clusters[product_id].append(r)

        logger.info(f"Grouped {len(records)} valid records into {len(clusters)} canonical product clusters.")
        return clusters
