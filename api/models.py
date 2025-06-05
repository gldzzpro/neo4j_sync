from pydantic import BaseModel, Field
from typing import List

class Node(BaseModel):
    name: str
    version: str

class Edge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    since: str

class InstanceData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

class InstancePayload(BaseModel):
    instance: str
    data: InstanceData
    status: str

class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool

class IngestResponse(BaseModel):
    status: str
    processed_instances: int
    message: str