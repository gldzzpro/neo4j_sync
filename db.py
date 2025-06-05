from neo4j_client import AsyncNeo4jClient
import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class Neo4jDatabase:
    """Neo4j database interface using the async client"""
    
    client: Optional[AsyncNeo4jClient] = None
    
    @classmethod
    async def initialize(cls):
        """Initialize the Neo4j client"""
        logger.info("Initializing Neo4j database...")
        
        try:
            cls.client = AsyncNeo4jClient()
            await cls.client.connect()
            logger.info("Neo4j database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j database: {e}")
            cls.client = None
            raise
    
    @classmethod
    async def close(cls):
        """Close the Neo4j client"""
        if cls.client:
            await cls.client.close()
            cls.client = None
            logger.info("Neo4j database closed")
    
    @classmethod
    async def ingest_graph(cls, instance_name: str, modules: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, int]:
        """Ingest instance, modules and dependencies into Neo4j following the exact schema conventions"""
        if not cls.client or not cls.client.is_connected:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        logger.info(f"Starting graph ingestion for instance '{instance_name}' with {len(modules)} modules and {len(edges)} edges")
        
        try:
            # Step 1: Create/merge Instance node
            instance_query = """
            MERGE (i:Instance { name: $instance_name }) 
            ON CREATE SET i.created = timestamp()
            RETURN count(i) as instances_processed
            """
            
            instance_result = await cls.client.execute_query(instance_query, {"instance_name": instance_name})
            instances_processed = instance_result[0]["instances_processed"] if instance_result else 0
            
            # Step 2: Create/merge Module nodes and Instance->Module relationships
            modules_created = 0
            instance_module_relationships = 0
            
            for module in modules:
                module_query = """
                MERGE (i:Instance { name: $instance_name }) 
                ON CREATE SET i.created = timestamp()
                MERGE (m:Module { name: $module_name }) 
                ON CREATE SET m.version = $module_version, m.created = timestamp()
                MERGE (i)-[:DEPLOYS]->(m)
                MERGE (m)-[:DEPLOYED_BY]->(i)
                RETURN count(m) as modules_created, count(i) as relationships_created
                """
                
                module_result = await cls.client.execute_query(module_query, {
                    "instance_name": instance_name,
                    "module_name": module["name"],
                    "module_version": module.get("version", "unknown")
                })
                
                if module_result:
                    modules_created += module_result[0]["modules_created"]
                    instance_module_relationships += module_result[0]["relationships_created"]
            
            # Step 3: Create Module->Module dependency relationships
            dependencies_created = 0
            
            for edge in edges:
                dependency_query = """
                MERGE (m_from:Module { name: $from_name }) 
                ON CREATE SET m_from.created = timestamp(), m_from.version = $from_version
                MERGE (m_to:Module { name: $to_name }) 
                ON CREATE SET m_to.created = timestamp(), m_to.version = $to_version
                MERGE (m_from)-[:DEPENDS_ON { instance: $instance_name, since: timestamp() }]->(m_to)
                MERGE (m_to)-[:DEPENDS_BY { instance: $instance_name, since: timestamp() }]->(m_from)
                RETURN count(*) as dependencies_created
                """
                
                dependency_result = await cls.client.execute_query(dependency_query, {
                    "from_name": edge["from_name"],
                    "to_name": edge["to_name"],
                    "from_version": edge.get("from_version", "unknown"),
                    "to_version": edge.get("to_version", "unknown"),
                    "instance_name": instance_name
                })
                
                if dependency_result:
                    dependencies_created += dependency_result[0]["dependencies_created"]
            
            logger.info(f"Graph ingestion completed for '{instance_name}': {modules_created} modules, {dependencies_created} dependencies")
            return {
                "instances_processed": instances_processed,
                "modules_created": modules_created,
                "dependencies_created": dependencies_created,
                "instance_module_relationships": instance_module_relationships
            }
            
        except Exception as e:
            logger.error(f"Error ingesting graph data: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    @classmethod
    async def execute_query(cls, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query"""
        if not cls.client or not cls.client.is_connected:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        try:
            return await cls.client.execute_query(query, parameters)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")