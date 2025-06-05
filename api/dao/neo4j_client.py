from neo4j import GraphDatabase
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def run(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results"""
        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    
    def execute_transaction(self, cypher: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query within a transaction"""
        def _run_query(tx, cypher, params):
            result = tx.run(cypher, params or {})
            return [record.data() for record in result]
        
        with self.driver.session() as session:
            return session.execute_write(_run_query, cypher, params)
    
    def health_check(self) -> bool:
        """Check if Neo4j connection is healthy"""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False