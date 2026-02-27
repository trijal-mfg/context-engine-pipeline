import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from transform.config import MONGO_URI, MONGO_DB_NAME

async def seed_schemas():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB_NAME]
    schemas_col = db["schemas"]
    
    schemas = [
        {
            "_id": "general_doc_v1",
            "description": "General purpose documentation",
            "schema_version": 1,
            "json_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the document"},
                    "summary": {"type": "string", "description": "Brief summary of the content"},
                    "unmapped_content": {"type": "string", "description": "Main body content"}
                },
                "required": ["title", "summary", "unmapped_content"],
                "additionalProperties": False
            }
        },
        {
            "_id": "runbook_v1",
            "description": "Operational runbook",
            "schema_version": 1,
            "json_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "unmapped_content": {"type": "string"}
                },
                "required": ["title", "steps", "unmapped_content"],
                "additionalProperties": False
            }
        },
        {
            "_id": "incident_ticket_v1",
            "description": "Incident report or ticket",
            "schema_version": 1,
            "json_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["sev1", "sev2", "sev3", "unknown"]},
                    "status": {"type": "string"},
                    "unmapped_content": {"type": "string"}
                },
                "required": ["title", "severity", "status", "unmapped_content"],
                "additionalProperties": False
            }
        }
    ]
    
    for schema in schemas:
        await schemas_col.replace_one({"_id": schema["_id"]}, schema, upsert=True)
        print(f"Seeded schema: {schema['_id']}")

if __name__ == "__main__":
    asyncio.run(seed_schemas())
