import uuid
from typing import Any, Dict, List
from backend.database.models import AttributeLineage


class LineageService:
    """Tier 2 Service: Builds and manages attribute-level lineage entities."""

    @staticmethod
    def build_lineage_models(lineage_data_list: List[Dict[str, Any]], run_id: str) -> List[AttributeLineage]:
        models = []
        for item in lineage_data_list:
            models.append(
                AttributeLineage(
                    lineage_id=str(uuid.uuid4()),
                    product_id=item["product_id"],
                    attribute_name=item["attribute_name"],
                    selected_value=item["selected_value"],
                    original_source_value=item.get("original_source_value"),
                    supplier_name=item["supplier_name"],
                    source_file=item["source_file"],
                    source_record_id=item.get("source_record_id"),
                    source_timestamp=item.get("source_timestamp"),
                    run_id=run_id,
                    selection_reason=item["selection_reason"]
                )
            )
        return models
