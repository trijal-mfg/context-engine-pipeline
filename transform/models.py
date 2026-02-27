from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal

class CanonicalDocument(BaseModel):
    source_id: str
    title: str = Field(description="Title of the document")
    content: str = Field(description="Main content of the document")
    metadata: dict = Field(default_factory=dict)

class Runbook(BaseModel):
    schema_type: Literal["runbook"] = "runbook"
    title: str = Field(description="Title of the runbook")
    steps: List[str] = Field(description="List of steps in the runbook")
    unmapped_content: List[str] = Field(default_factory=list, description="Content not mapped to specific fields")

class IncidentTicket(BaseModel):
    schema_type: Literal["incident_ticket"] = "incident_ticket"
    title: str = Field(description="Title of the incident ticket")
    severity: Literal["sev1", "sev2", "sev3", "unknown"] = Field(description="Severity level of the incident")
    status: str = Field(description="Current status of the incident")
    unmapped_content: List[str] = Field(default_factory=list, description="Content not mapped to specific fields")

class GeneralDoc(BaseModel):
    schema_type: Literal["general_doc"] = "general_doc"
    title: str = Field(description="Title of the document")
    summary: str = Field(description="Brief summary of the document")
    unmapped_content: List[str] = Field(default_factory=list, description="Main body content sections")

# Union type for single-pass extraction
ExtractionResponse = Union[Runbook, IncidentTicket, GeneralDoc]
