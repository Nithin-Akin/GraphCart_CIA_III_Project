# GraphCart: E-Commerce Recommendations and Inventory Management

GraphCart is a CIA III project built from the submitted case study, **Leveraging Graph Databases for Real-Time Product Recommendations and Inventory Management in E-Commerce**. It uses Neo4j to store connected customer, product, purchase, supplier, warehouse, stock, and order data.

## Features

1. Dashboard with live graph counts.
2. Product CRUD and supplier connections.
3. Customer CRUD and purchase history.
4. Warehouse inventory CRUD using `STOCKED_AT` relationships.
5. Order creation, stock-aware fulfillment, and product recommendations.

## Run locally

Install Docker Desktop, open a terminal in this folder, then run:

```bash
docker compose up --build
```

Open the app at `http://localhost:5001` and Neo4j Browser at `http://localhost:7475`.

Neo4j credentials:

```text
Username: neo4j
Password: cia3project
```

To stop it later, press `Ctrl+C`, then run `docker compose down`.

## Evaluation demonstration flow

1. Open **Dashboard** and explain the nodes and relationships.
2. In **Products**, add or edit a product and show that a supplier relationship is created.
3. In **Inventory**, update the quantity in a warehouse.
4. In **Customers**, record a new purchase for a customer.
5. In **Recommendations**, select the customer and run the Cypher recommendation query.
6. Create an order and show that the application selects a warehouse with enough stock and reduces inventory.

## Key Cypher concepts demonstrated

- `MERGE` creates nodes and relationships safely.
- `MATCH` reads connected graph data.
- `SET` updates node fields and relationship properties.
- `DELETE` and `DETACH DELETE` remove records and relationships.
- Multi-hop traversals generate recommendations and locate fulfilment stock.

## Reset demo data

Use the **Reset demo data** button in the navigation bar. It deletes the current graph and loads the prepared sample data again.
