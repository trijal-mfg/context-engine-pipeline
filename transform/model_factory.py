from typing import Dict, Any, Type, List, Optional
from pydantic import BaseModel, create_model, Field

class ModelFactory:
    """
    Dynamically creates Pydantic models from JSON Schemas stored in MongoDB.
    """
    
    @staticmethod
    def create_pydantic_model(schema_doc: Dict[str, Any]) -> Type[BaseModel]:
        """
        Converts a MongoDB schema document into a Pydantic model class.
        """
        schema_id = schema_doc["_id"]
        json_schema = schema_doc.get("json_schema", {})
        properties = json_schema.get("properties", {})
        required_fields = json_schema.get("required", [])
        
        # Field definitions for create_model
        fields = {}
        
        # Always inject the schema_type explicitly so the Union discriminator works
        # We use a Literal type for the schema_id to help Instructor/Pydantic distinguish them
        fields["schema_type"] = (str, Field(default=schema_id, description="The type of the document"))

        for field_name, field_def in properties.items():
            field_type = ModelFactory._map_json_type_to_python(field_def)
            description = field_def.get("description", "")
            
            # Determine if required
            if field_name in required_fields:
                fields[field_name] = (field_type, Field(description=description))
            else:
                fields[field_name] = (Optional[field_type], Field(default=None, description=description))
                
        # Create the dynamic class
        # We sanitize the class name to be valid Python identifier
        class_name = "".join(x.capitalize() for x in schema_id.split("_"))
        
        model = create_model(class_name, **fields)
        return model

    @staticmethod
    def _map_json_type_to_python(field_def: Dict[str, Any]) -> Type:
        """
        Maps JSON schema types to Python types.
        """
        json_type = field_def.get("type", "string")
        
        if json_type == "string":
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            items = field_def.get("items", {})
            item_type = ModelFactory._map_json_type_to_python(items)
            return List[item_type]
        elif json_type == "object":
            return Dict[str, Any] # nested models not fully supported in this simple factory yet
            
        return Any
