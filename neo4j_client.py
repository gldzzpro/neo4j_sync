import os
import logging
from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError, ConfigurationError

logger = logging.getLogger(__name__)

class AsyncNeo4jClient:
    """Async Neo4j client with proper error handling and connection management"""
    
    def __init__(self):
        self._uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._username = os.getenv("NEO4J_USERNAME", "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None
        self._connected = False
        
        logger.info(f"Initializing Neo4j client with URI: {self._uri}")
        logger.info(f"Username: {self._username}")
        logger.info(f"Password length: {len(self._password)} characters")
    
    async def connect(self):
        """Initialize the Neo4j driver and verify connectivity"""
        try:
            logger.info(f"Attempting to connect to Neo4j at: {self._uri}")
            logger.info(f"Using username: {self._username}")
            
            # MINIMAL configuration for Neo4j Aura - just URI and auth, nothing else!
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password)
            )
            
            logger.info("Neo4j driver created successfully")
            
            # Test the connection
            logger.info("Testing Neo4j connection...")
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                test_value = record["test"]
                logger.info(f"Connection test successful! Result: {test_value}")
                
            # Test database info
            async with self._driver.session() as session:
                result = await session.run("CALL dbms.components() YIELD name, versions, edition")
                async for record in result:
                    logger.info(f"Connected to {record['name']} {record['versions'][0]} {record['edition']}")
                    break
            
            self._connected = True
            logger.info("Neo4j connection established successfully")
            
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            logger.error(f"Check if Neo4j Aura instance is running and accessible")
            self._driver = None
            self._connected = False
            raise
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            logger.error(f"Check username/password credentials")
            self._driver = None
            self._connected = False
            raise
        except ConfigurationError as e:
            logger.error(f"Neo4j configuration error: {e}")
            logger.error(f"Check URI format and connection parameters")
            self._driver = None
            self._connected = False
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {type(e).__name__}: {e}")
            logger.error(f"Connection details - URI: {self._uri}, Username: {self._username}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self._driver = None
            self._connected = False
            raise

    async def close(self):
        """Close the Neo4j driver connection"""
        if self._driver:
            try:
                logger.info("Closing Neo4j connection...")
                await self._driver.close()
                logger.info("Neo4j connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Neo4j connection: {e}")
            finally:
                self._driver = None
                self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected"""
        return self._connected and self._driver is not None

    @property
    def driver(self):
        """Get the Neo4j driver instance"""
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized. Call connect() first.")
        return self._driver

    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        if not self.is_connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")
        
        try:
            logger.debug(f"Executing query: {query}")
            async with self._driver.session() as session:
                result = await session.run(query, parameters or {})
                data = await result.data()
                records = [record for record in data]
                logger.debug(f"Query returned {len(records)} records")
                return records
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise

    async def health_check(self) -> bool:
        """Check if the Neo4j connection is healthy"""
        try:
            if not self._driver or not self._connected:
                logger.warning("Health check failed: driver not connected")
                return False
            
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                health_status = record and record["health"] == 1
                logger.debug(f"Health check result: {health_status}")
                return health_status
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False