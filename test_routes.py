"""Lightweight template smoke test. It deliberately replaces Neo4j calls."""
import app as project

project.query = lambda cypher, **params: []
project.execute = lambda cypher, **params: None

client = project.app.test_client()
for path in ["/", "/products", "/customers", "/inventory", "/recommendations", "/orders"]:
    response = client.get(path)
    assert response.status_code == 200, f"{path}: {response.status_code}"
print("All six page routes rendered successfully.")
