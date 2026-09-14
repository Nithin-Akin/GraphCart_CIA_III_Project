// GraphCart database schema. The Flask app creates these constraints at startup.
CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT warehouse_id IF NOT EXISTS FOR (w:Warehouse) REQUIRE w.id IS UNIQUE;
CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE;

// Main graph relationships:
// (Customer)-[:PURCHASED {date, quantity}]->(Product)
// (Product)-[:SUPPLIED_BY]->(Supplier)
// (Product)-[:STOCKED_AT {quantity, reorder_level}]->(Warehouse)
// (Order)-[:PLACED_BY]->(Customer)
// (Order)-[:CONTAINS {quantity}]->(Product)
// (Order)-[:SHIPPED_FROM]->(Warehouse)
