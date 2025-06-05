from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class Node(BaseModel):
    """Model for a graph node - simplified to only require id and name"""
    id: str
    name: str  # This will be the module name/label
    properties: Dict[str, Any] = Field(default_factory=dict)  # Optional additional properties

class Edge(BaseModel):
    """Model for a graph edge - simplified to only require from and to"""
    from_: str = Field(alias="from")  # Source node id
    to: str  # Target node id
    properties: Dict[str, Any] = Field(default_factory=dict)  # Optional additional properties

class GraphPayload(BaseModel):
    """Model for the graph payload containing nodes and edges"""
    nodes: List[Node]
    edges: List[Edge]

class QueryRequest(BaseModel):
    """Model for a Cypher query request"""
    query: str
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)

class QueryResponse(BaseModel):
    """Model for a Cypher query response"""
    results: List[Dict[str, Any]]
    execution_time: float

class IngestResponse(BaseModel):
    """Model for a graph ingestion response"""
    status: str
    processed_instances: int
    nodes_created: int  # Now represents modules created
    edges_created: int  # Now represents dependencies created
    message: str

# Models for handling graph_sync response format
class ModuleNode(BaseModel):
    """Model for a module node from graph-sync response"""
    id: int
    label: str  # This becomes the module name
    state: Optional[str] = None
    depth: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    version: Optional[str] = None  # Added to support module versioning

class ModuleEdge(BaseModel):
    """Model for a module dependency edge from graph-sync response"""
    from_: int = Field(alias="from")
    to: int
    type: Optional[str] = "dependency"

class GraphSyncData(BaseModel):
    """Model for the graph-sync data structure"""
    nodes: List[ModuleNode]
    edges: List[ModuleEdge]

class InstanceSyncResponse(BaseModel):
    """Model for a single instance sync response"""
    instance: str  # This becomes the instance name
    status: str
    data: Optional[GraphSyncData] = None
    error: Optional[str] = None

class MultiInstanceSyncResponse(BaseModel):
    """Model for multiple instance sync responses"""
    responses: List[InstanceSyncResponse]