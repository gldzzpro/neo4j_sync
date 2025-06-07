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
            
            # Step 3: Create Module->Module dependency relationships with uniqueness
            dependencies_created = 0
            
            for edge in edges:
                # Modified query to ensure unique relationships and track instances
                dependency_query = """
                MERGE (m_from:Module { name: $from_name }) 
                ON CREATE SET m_from.created = timestamp(), m_from.version = $from_version
                MERGE (m_to:Module { name: $to_name }) 
                ON CREATE SET m_to.created = timestamp(), m_to.version = $to_version
                
                // Create unique DEPENDS_ON relationship
                MERGE (m_from)-[dep_on:DEPENDS_ON]->(m_to)
                ON CREATE SET dep_on.created = timestamp(), dep_on.instances = [$instance_name]
                ON MATCH SET dep_on.instances = 
                    CASE 
                        WHEN $instance_name IN dep_on.instances THEN dep_on.instances
                        ELSE dep_on.instances + $instance_name
                    END
                
                // Create unique DEPENDS_BY relationship
                MERGE (m_to)-[dep_by:DEPENDS_BY]->(m_from)
                ON CREATE SET dep_by.created = timestamp(), dep_by.instances = [$instance_name]
                ON MATCH SET dep_by.instances = 
                    CASE 
                        WHEN $instance_name IN dep_by.instances THEN dep_by.instances
                        ELSE dep_by.instances + $instance_name
                    END
                
                RETURN count(dep_on) as dependencies_created
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
    async def analyze_cycles(cls) -> Dict[str, Any]:
        """Analyze the graph for cyclic dependencies using APOC procedures"""
        if not cls.client or not cls.client.is_connected:
            raise HTTPException(status_code=500, detail="Database not connected")
        
        logger.info("Starting cycle analysis...")
        
        try:
            # First, check if APOC is available
            apoc_check_query = "RETURN apoc.version() as version"
            try:
                await cls.client.execute_query(apoc_check_query)
                logger.info("APOC procedures are available")
            except Exception as apoc_error:
                logger.warning(f"APOC procedures not available: {apoc_error}")
                return {
                    "cycles_detected": False,
                    "cycles": [],
                    "responsible_instances": [],
                    "error": "APOC procedures not available"
                }
            
            # Execute the cycle detection query
            cycle_query = """
            MATCH (m:Module)
            WITH collect(m) AS modules
            CALL apoc.nodes.cycles(modules, {relTypes: ['DEPENDS_ON']})
            YIELD path
            WITH path, [n IN nodes(path) WHERE 'Module' IN labels(n) | n.name] AS moduleNames
            MATCH (i:Instance)-[:DEPLOYS]->(m:Module)
            WHERE m.name IN moduleNames
            RETURN path, collect(DISTINCT i.name) AS deployingInstances
            """
            
            cycle_results = await cls.client.execute_query(cycle_query)
            
            cycles = []
            all_responsible_instances = set()
            
            for result in cycle_results:
                # Extract module names from the path
                path = result.get("path")
                deploying_instances = result.get("deployingInstances", [])
                
                if path:
                    # Convert path to list of module names
                    # The path contains nodes and relationships, we need to extract module names
                    module_names = []
                    # This is a simplified extraction - in practice, you might need to parse the path object
                    # For now, we'll use the moduleNames that should be in the result
                    # Since the query already extracts moduleNames, we can use that
                    
                    # Alternative approach: extract from deployingInstances context
                    # We'll need to re-query to get the actual cycle path
                    pass
                
                # Add deploying instances to the set
                all_responsible_instances.update(deploying_instances)
            
            # Alternative simpler approach for cycle detection without complex path parsing
            simple_cycle_query = """
            MATCH (m:Module)
            WITH collect(m) AS modules
            CALL apoc.nodes.cycles(modules, {relTypes: ['DEPENDS_ON']})
            YIELD path
            WITH [n IN nodes(path) WHERE 'Module' IN labels(n) | n.name] AS moduleNames
            WHERE size(moduleNames) > 0
            MATCH (i:Instance)-[:DEPLOYS]->(m:Module)
            WHERE m.name IN moduleNames
            RETURN moduleNames, collect(DISTINCT i.name) AS deployingInstances
            """
            
            simple_results = await cls.client.execute_query(simple_cycle_query)
            
            cycles = []
            all_responsible_instances = set()
            
            for result in simple_results:
                module_names = result.get("moduleNames", [])
                deploying_instances = result.get("deployingInstances", [])
                
                if module_names:
                    # Add the first module at the end to show the cycle
                    cycle_path = module_names + [module_names[0]] if module_names else []
                    cycles.append(cycle_path)
                    all_responsible_instances.update(deploying_instances)
            
            cycles_detected = len(cycles) > 0
            responsible_instances = sorted(list(all_responsible_instances))
            
            logger.info(f"Cycle analysis completed: {len(cycles)} cycles detected, {len(responsible_instances)} responsible instances")
            
            return {
                "cycles_detected": cycles_detected,
                "cycles": cycles,
                "responsible_instances": responsible_instances
            }
            
        except Exception as e:
            logger.error(f"Error during cycle analysis: {e}")
            # Return safe defaults instead of raising exception
            return {
                "cycles_detected": False,
                "cycles": [],
                "responsible_instances": [],
                "error": f"Cycle analysis failed: {str(e)}"
            }
    
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