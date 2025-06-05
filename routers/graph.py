from fastapi import APIRouter, HTTPException
import logging
import time

from db import Neo4jDatabase
from models import (
    GraphPayload, QueryRequest, QueryResponse, IngestResponse, 
    MultiInstanceSyncResponse, InstanceSyncResponse
)

# Configure router
router = APIRouter(prefix="/api/graph", tags=["graph"])

# Configure logging
logger = logging.getLogger(__name__)

@router.post("/ingest", response_model=IngestResponse)
async def ingest_graph(payload: MultiInstanceSyncResponse):
    """Ingest nodes and edges into the graph database following the exact schema conventions"""
    try:
        total_modules_created = 0
        total_dependencies_created = 0
        processed_instances = 0
        
        # Process each instance response
        for instance_response in payload.responses:
            if instance_response.status != "success" or not instance_response.data:
                logger.warning(f"Skipping instance '{instance_response.instance}': {instance_response.error or 'No data'}")
                continue
            
            graph_data = instance_response.data
            instance_name = instance_response.instance
            
            # Convert graph_sync format to schema-compliant format
            modules = []
            for node in graph_data.nodes:
                modules.append({
                    "name": node.label,  # Module name
                    "version": getattr(node, 'version', 'unknown'),  # Module version if available
                    "id": str(node.id)  # Keep original ID for edge mapping
                })
            
            # Create a mapping from node ID to module name for edge processing
            id_to_name = {str(node.id): node.label for node in graph_data.nodes}
            
            edges = []
            for edge in graph_data.edges:
                from_name = id_to_name.get(str(edge.from_))
                to_name = id_to_name.get(str(edge.to))
                
                if from_name and to_name:
                    edges.append({
                        "from_name": from_name,
                        "to_name": to_name,
                        "from_version": "unknown",  # Could be extracted from node data if available
                        "to_version": "unknown",    # Could be extracted from node data if available
                        "type": edge.type or "dependency"
                    })
                else:
                    logger.warning(f"Skipping edge with missing nodes: {edge.from_} -> {edge.to}")
            
            # Log the ingestion request
            logger.info(f"Ingesting graph from instance '{instance_name}' with {len(modules)} modules and {len(edges)} dependencies")
            
            # Process the ingestion using the new schema
            result = await Neo4jDatabase.ingest_graph(instance_name, modules, edges)
            
            total_modules_created += result["modules_created"]
            total_dependencies_created += result["dependencies_created"]
            processed_instances += 1
        
        return IngestResponse(
            status="success",
            processed_instances=processed_instances,
            nodes_created=total_modules_created,  # Now represents modules created
            edges_created=total_dependencies_created,  # Now represents dependencies created
            message=f"Successfully ingested data from {processed_instances} instances following schema conventions"
        )
    except Exception as e:
        logger.error(f"Error in graph ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """Execute a Cypher query with parameters"""
    try:
        start_time = time.time()
        
        # Execute the query
        results = await Neo4jDatabase.execute_query(request.query, request.parameters)
        
        execution_time = time.time() - start_time
        
        return QueryResponse(
            results=results,
            execution_time=execution_time
        )
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))