# FastAPI Neo4j Microservice

This is an asynchronous FastAPI microservice for Neo4j graph database operations. It provides endpoints for graph data ingestion and Cypher query execution using the Neo4j async driver.

## Features

- Asynchronous Neo4j driver integration
- Environment-based configuration with Pydantic BaseSettings
- Graph data ingestion with UNWIND + MERGE Cypher operations
- Parameterized Cypher query execution
- Structured logging
- Error handling with proper HTTP exceptions
- Modular code organization following FastAPI best practices

## Project Structure

```
app/
├── __init__.py
├── config.py         # Configuration using Pydantic BaseSettings
├── db.py             # Neo4j database client with async methods
├── main.py           # FastAPI application entry point
├── models.py         # Pydantic models for request/response validation
└── routers/          # API route modules
    ├── __init__.py
    └── graph.py      # Graph operations endpoints
```

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements-neo4j.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:

```
NEO4J_URI=neo4j+s://your-neo4j-instance:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
DEBUG=true  # Set to false in production
```

## Running the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Endpoints

### Health Check

```
GET /health
```

Returns the service health status.

### Ingest Graph Data

```
POST /api/graph/ingest
```

Ingests nodes and edges into the Neo4j database.

Example request body:

```json
{
  "nodes": [
    {
      "id": "node1",
      "properties": {
        "name": "Node 1",
        "type": "Person"
      }
    },
    {
      "id": "node2",
      "properties": {
        "name": "Node 2",
        "type": "Organization"
      }
    }
  ],
  "edges": [
    {
      "id": "edge1",
      "source": "node1",
      "target": "node2",
      "properties": {
        "type": "WORKS_FOR",
        "since": 2020
      }
    }
  ]
}
```

### Execute Cypher Query

```
POST /api/graph/query
```

Executes a Cypher query with parameters.

Example request body:

```json
{
  "query": "MATCH (n:Node) WHERE n.type = $type RETURN n.id, n.name",
  "parameters": {
    "type": "Person"
  }
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages in JSON format:

```json
{
  "detail": "Error message"
}
```

## Logging

The application logs:
- DEBUG level: Cypher queries and parameters
- INFO level: Query execution summaries, node/edge counts
- ERROR level: Exceptions and error details