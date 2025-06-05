import logging
import os
from fastapi import FastAPI, HTTPException
from routers.graph import router as graph_router
from db import Neo4jDatabase

# Configure logging with explicit stdout handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Ensure logs go to stdout
    ]
)
logger = logging.getLogger(__name__)

# Add immediate startup logs
print("=== MAIN.PY LOADING ===")
logger.info("main.py module loading started")

# Create FastAPI app first
app = FastAPI()

# Add startup and shutdown event handlers (older pattern for compatibility)
@app.on_event("startup")
async def startup_event():
    print("=== STARTUP EVENT TRIGGERED ===")
    logger.info("Application startup event initiated")
    try:
        await Neo4jDatabase.initialize()
        logger.info("Database initialization completed successfully")
        print("=== DATABASE INITIALIZED SUCCESSFULLY ===")
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {e}")
        print(f"=== DATABASE INITIALIZATION FAILED: {e} ===")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")
    await Neo4jDatabase.close()
    logger.info("Application shutdown completed")

app.include_router(graph_router)

@app.get("/healthcheck")
async def healthcheck():
    """Enhanced health check with Neo4j connectivity test"""
    neo4j_connected = False
    
    if Neo4jDatabase.client:
        neo4j_connected = await Neo4jDatabase.client.health_check()
    
    return {
        "status": "healthy" if neo4j_connected else "unhealthy",
        "database_connected": neo4j_connected
    }

@app.get("/labels")
async def get_labels():
    """Example endpoint to get all node labels"""
    try:
        query = "CALL db.labels()"
        result = await Neo4jDatabase.execute_query(query)
        return {"labels": [record["label"] for record in result]}
    except Exception as e:
        logger.error(f"Error getting labels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_database_stats():
    """Get basic database statistics"""
    try:
        queries = {
            "node_count": "MATCH (n) RETURN count(n) as count",
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) as count",
            "label_count": "CALL db.labels() YIELD label RETURN count(label) as count"
        }
        
        stats = {}
        for stat_name, query in queries.items():
            result = await Neo4jDatabase.execute_query(query)
            stats[stat_name] = result[0]["count"] if result else 0
        
        return stats
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

print("=== MAIN.PY LOADED SUCCESSFULLY ===")
logger.info("main.py module loaded successfully")
