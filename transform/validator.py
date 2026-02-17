"""
only json validation for now, TODO: add content validation using: word/char freq, sematic search etc
"""
import jsonschema
from jsonschema import validate, ValidationError
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Validator:
    """
    Enforces strict JSON schema validation.
    """
    def validate(self, document: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validates the document against the provided JSON schema.
        Raises ValidationError if validation fails.
        """
        try:
            # Extract the actual JSON schema definition from the Mongo document
            json_schema = schema.get("json_schema")
            if not json_schema:
                 raise ValueError(f"Schema {schema.get('_id')} missing 'json_schema' field")

            validate(instance=document, schema=json_schema)
            return True
            
        except ValidationError as e:
            logger.error(f"Validation failed for schema {schema.get('_id')}: {e.message}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            raise e
