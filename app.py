import os
import time
import uuid
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for
from neo4j import GraphDatabase

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "graphcart-dev-secret")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "cia3project")
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def query(cypher, **params):
    with driver.session() as session:
        return [record.data() for record in session.run(cypher, **params)]


def execute(cypher, **params):
    with driver.session() as session:
        session.run(cypher, **params).consume()


def positive_int(value, field, minimum=1):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number.")
    if parsed < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    return parsed


def nonnegative_float(value, field):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if parsed < 0:
        raise ValueError(f"{field} cannot be negative.")
    return parsed


def new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def initialise_database():
    constraints = [
        "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT warehouse_id IF NOT EXISTS FOR (w:Warehouse) REQUIRE w.id IS UNIQUE",
        "CREATE CONSTRAINT order_id IF NOT EXISTS FOR (o:Order) REQUIRE o.id IS UNIQUE",
    ]
    for statement in constraints:
        execute(statement)
    if query("MATCH (n) RETURN count(n) AS total")[0]["total"] == 0:
        seed_data()


def seed_data():
    execute("MATCH (n) DETACH DELETE n")
    suppliers = [
        ("s1", "TechSource Distributors", "electronics@techsource.com"),
        ("s2", "Home Essentials Ltd", "sales@homeessentials.com"),
        ("s3", "OfficeWorks Supply", "orders@officeworks.com"),
    ]
    warehouses = [("w1", "Chennai Central", "Chennai"), ("w2", "Bengaluru Hub", "Bengaluru"), ("w3", "Mumbai West", "Mumbai")]
    customers = [("c1", "Aarav Sharma", "aarav@email.com"), ("c2", "Diya Patel", "diya@email.com"), ("c3", "Kabir Singh", "kabir@email.com"), ("c4", "Meera Nair", "meera@email.com"), ("c5", "Rohan Gupta", "rohan@email.com")]
    products = [
        ("p1", "Wireless Headphones", "Electronics", 2499, "s1"),
        ("p2", "Smart Watch", "Electronics", 3999, "s1"),
        ("p3", "Bluetooth Speaker", "Electronics", 1799, "s1"),
        ("p4", "Coffee Maker", "Home Appliances", 3299, "s2"),
        ("p5", "Desk Lamp", "Home Decor", 899, "s2"),
        ("p6", "Mechanical Keyboard", "Electronics", 2799, "s3"),
        ("p7", "Office Chair", "Furniture", 6499, "s3"),
        ("p8", "Laptop Stand", "Office Supplies", 1199, "s3"),
    ]
    for sid, name, email in suppliers:
        execute("CREATE (:Supplier {id:$id, name:$name, email:$email})", id=sid, name=name, email=email)
    for wid, name, city in warehouses:
        execute("CREATE (:Warehouse {id:$id, name:$name, city:$city})", id=wid, name=name, city=city)
    for cid, name, email in customers:
        execute("CREATE (:Customer {id:$id, name:$name, email:$email})", id=cid, name=name, email=email)
    for pid, name, category, price, sid in products:
        execute("MATCH (s:Supplier {id:$sid}) CREATE (p:Product {id:$id, name:$name, category:$category, price:$price})-[:SUPPLIED_BY]->(s)", id=pid, name=name, category=category, price=price, sid=sid)
    stock = [("p1", "w1", 24), ("p1", "w2", 11), ("p2", "w1", 8), ("p2", "w3", 17), ("p3", "w2", 20), ("p4", "w1", 9), ("p4", "w3", 14), ("p5", "w2", 31), ("p6", "w1", 18), ("p6", "w3", 12), ("p7", "w3", 6), ("p8", "w1", 25), ("p8", "w2", 15)]
    for pid, wid, quantity in stock:
        execute("MATCH (p:Product {id:$pid}), (w:Warehouse {id:$wid}) CREATE (p)-[:STOCKED_AT {quantity:$quantity, reorder_level:5}]->(w)", pid=pid, wid=wid, quantity=quantity)
    purchases = [("c1", "p1"), ("c1", "p6"), ("c2", "p1"), ("c2", "p2"), ("c2", "p3"), ("c3", "p1"), ("c3", "p2"), ("c3", "p6"), ("c4", "p4"), ("c4", "p5"), ("c5", "p6"), ("c5", "p8")]
    for cid, pid in purchases:
        execute("MATCH (c:Customer {id:$cid}), (p:Product {id:$pid}) CREATE (c)-[:PURCHASED {date:$date, quantity:1}]->(p)", cid=cid, pid=pid, date="2026-09-01")


@app.route("/")
def dashboard():
    stats = query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total")
    stat_map = {row["label"]: row["total"] for row in stats}
    low_stock = query("MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse) WHERE s.quantity <= s.reorder_level RETURN p.name AS product, w.name AS warehouse, s.quantity AS quantity ORDER BY s.quantity")
    kpis = query("""CALL { MATCH (o:Order) RETURN count(o) AS orders }
        CALL { MATCH ()-[s:STOCKED_AT]->() RETURN coalesce(sum(s.quantity),0) AS units }
        CALL { MATCH (o:Order)-[i:CONTAINS]->(p:Product) RETURN coalesce(sum(i.quantity * coalesce(i.unit_price,p.price)),0) AS revenue }
        RETURN orders, units, revenue""")[0]
    category_sales = query("""MATCH (o:Order)-[i:CONTAINS]->(p:Product)
        RETURN p.category AS category, sum(i.quantity * coalesce(i.unit_price,p.price)) AS revenue
        ORDER BY revenue DESC""")
    warehouse_stock = query("""MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse)
        RETURN w.name AS warehouse, sum(s.quantity) AS units ORDER BY units DESC""")
    top_products = query("""MATCH (c:Customer)-[r:PURCHASED]->(p:Product)
        RETURN p.name AS product, sum(r.quantity) AS units ORDER BY units DESC LIMIT 5""")
    recent_orders = query("""MATCH (o:Order)-[:PLACED_BY]->(c:Customer)
        MATCH (o)-[i:CONTAINS]->(p:Product) MATCH (o)-[:SHIPPED_FROM]->(w:Warehouse)
        RETURN o.id AS id, o.date AS date, c.name AS customer, p.name AS product,
        i.quantity AS quantity, w.name AS warehouse ORDER BY o.date DESC LIMIT 5""")
    relationships = query("MATCH ()-[r]->() RETURN count(r) AS total")[0]["total"]
    return render_template("dashboard.html", stats=stat_map, kpis=kpis, low_stock=low_stock,
                           category_sales=category_sales, warehouse_stock=warehouse_stock,
                           top_products=top_products, recent_orders=recent_orders, relationships=relationships)


@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        product_id = request.form.get("id") or new_id("p")
        try:
            price = nonnegative_float(request.form.get("price"), "Price")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("products"))
        execute("MERGE (p:Product {id:$id}) SET p.name=$name, p.category=$category, p.price=$price WITH p OPTIONAL MATCH (p)-[old:SUPPLIED_BY]->() DELETE old WITH p MATCH (s:Supplier {id:$supplier_id}) MERGE (p)-[:SUPPLIED_BY]->(s)", id=product_id, name=request.form["name"].strip(), category=request.form["category"].strip(), price=price, supplier_id=request.form["supplier_id"])
        flash("Product saved successfully.", "success")
        return redirect(url_for("products"))
    rows = query("MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier) OPTIONAL MATCH (p)-[stock:STOCKED_AT]->() RETURN p.id AS id, p.name AS name, p.category AS category, p.price AS price, s.name AS supplier, coalesce(sum(stock.quantity),0) AS stock ORDER BY p.name")
    suppliers = query("MATCH (s:Supplier) RETURN s.id AS id, s.name AS name ORDER BY s.name")
    edit = query("MATCH (p:Product {id:$id})-[:SUPPLIED_BY]->(s) RETURN p.id AS id,p.name AS name,p.category AS category,p.price AS price,s.id AS supplier_id", id=request.args.get("edit")) if request.args.get("edit") else []
    return render_template("products.html", products=rows, suppliers=suppliers, edit=edit[0] if edit else None)


@app.post("/products/<product_id>/delete")
def delete_product(product_id):
    execute("MATCH (p:Product {id:$id}) DETACH DELETE p", id=product_id)
    flash("Product deleted.", "warning")
    return redirect(url_for("products"))


@app.route("/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        customer_id = request.form.get("id") or new_id("c")
        execute("MERGE (c:Customer {id:$id}) SET c.name=$name, c.email=$email", id=customer_id, name=request.form["name"], email=request.form["email"])
        flash("Customer saved successfully.", "success")
        return redirect(url_for("customers"))
    rows = query("MATCH (c:Customer) OPTIONAL MATCH (c)-[r:PURCHASED]->() RETURN c.id AS id,c.name AS name,c.email AS email,count(r) AS purchases ORDER BY c.name")
    products_list = query("MATCH (p:Product) RETURN p.id AS id,p.name AS name ORDER BY p.name")
    edit = query("MATCH (c:Customer {id:$id}) RETURN c.id AS id,c.name AS name,c.email AS email", id=request.args.get("edit")) if request.args.get("edit") else []
    return render_template("customers.html", customers=rows, products=products_list, edit=edit[0] if edit else None)


@app.post("/customers/<customer_id>/purchase")
def add_purchase(customer_id):
    try:
        quantity = positive_int(request.form.get("quantity", 1), "Quantity")
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("customers"))
    execute("MATCH (c:Customer {id:$cid}), (p:Product {id:$pid}) CREATE (c)-[:PURCHASED {date:$date, quantity:$quantity}]->(p)", cid=customer_id, pid=request.form["product_id"], date=str(date.today()), quantity=quantity)
    flash("Purchase relationship added to Neo4j.", "success")
    return redirect(url_for("customers"))


@app.post("/customers/<customer_id>/delete")
def delete_customer(customer_id):
    execute("MATCH (c:Customer {id:$id}) DETACH DELETE c", id=customer_id)
    flash("Customer deleted.", "warning")
    return redirect(url_for("customers"))


@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    if request.method == "POST":
        try:
            quantity = positive_int(request.form.get("quantity"), "Quantity", 0)
            reorder = positive_int(request.form.get("reorder_level"), "Reorder level", 0)
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("inventory"))
        execute("MATCH (p:Product {id:$pid}), (w:Warehouse {id:$wid}) MERGE (p)-[s:STOCKED_AT]->(w) SET s.quantity=$quantity, s.reorder_level=$reorder", pid=request.form["product_id"], wid=request.form["warehouse_id"], quantity=quantity, reorder=reorder)
        flash("Inventory record saved successfully.", "success")
        return redirect(url_for("inventory"))
    records = query("MATCH (p:Product)-[s:STOCKED_AT]->(w:Warehouse) RETURN p.id AS product_id,p.name AS product,w.id AS warehouse_id,w.name AS warehouse,w.city AS city,s.quantity AS quantity,s.reorder_level AS reorder_level ORDER BY p.name,w.name")
    products_list = query("MATCH (p:Product) RETURN p.id AS id,p.name AS name ORDER BY p.name")
    warehouses = query("MATCH (w:Warehouse) RETURN w.id AS id,w.name AS name,w.city AS city ORDER BY w.name")
    return render_template("inventory.html", inventory=records, products=products_list, warehouses=warehouses)


@app.post("/inventory/<product_id>/<warehouse_id>/delete")
def delete_stock(product_id, warehouse_id):
    execute("MATCH (:Product {id:$pid})-[s:STOCKED_AT]->(:Warehouse {id:$wid}) DELETE s", pid=product_id, wid=warehouse_id)
    flash("Inventory relationship deleted.", "warning")
    return redirect(url_for("inventory"))


@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    customers_list = query("MATCH (c:Customer) RETURN c.id AS id,c.name AS name ORDER BY c.name")
    result, selected, cypher = [], request.values.get("customer_id"), ""
    if selected:
        cypher = "MATCH (c:Customer {id:$customer_id})-[:PURCHASED]->(:Product)<-[:PURCHASED]-(similar:Customer)-[:PURCHASED]->(rec:Product) WHERE NOT (c)-[:PURCHASED]->(rec) RETURN rec.name AS product, rec.category AS category, count(DISTINCT similar) AS score ORDER BY score DESC LIMIT 5"
        result = query(cypher, customer_id=selected)
    return render_template("recommendations.html", customers=customers_list, recommendations=result, selected=selected, cypher=cypher)


@app.route("/orders", methods=["GET", "POST"])
def orders():
    if request.method == "POST":
        cid, pid = request.form["customer_id"], request.form["product_id"]
        try:
            qty = positive_int(request.form.get("quantity"), "Quantity")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("orders"))
        oid = new_id("o")
        with driver.session() as session:
            result = session.run("""MATCH (c:Customer {id:$cid}), (p:Product {id:$pid})
                MATCH (p)-[s:STOCKED_AT]->(w:Warehouse) WHERE s.quantity >= $qty
                WITH c,p,s,w ORDER BY s.quantity DESC LIMIT 1
                CREATE (o:Order {id:$oid, date:$date, status:'Shipped'})-[:PLACED_BY]->(c)
                CREATE (o)-[:CONTAINS {quantity:$qty, unit_price:p.price}]->(p)
                CREATE (o)-[:SHIPPED_FROM]->(w)
                CREATE (c)-[:PURCHASED {date:$date, quantity:$qty, order_id:$oid}]->(p)
                SET s.quantity=s.quantity-$qty
                RETURN w.name AS warehouse""", cid=cid, pid=pid, oid=oid, date=str(date.today()), qty=qty)
            order_result = result.single()
        if not order_result:
            flash("No warehouse has enough stock for this order.", "danger")
            return redirect(url_for("orders"))
        flash(f"Order created and shipped from {order_result['warehouse']}.", "success")
        return redirect(url_for("orders"))
    rows = query("MATCH (o:Order)-[:PLACED_BY]->(c:Customer) MATCH (o)-[i:CONTAINS]->(p:Product) MATCH (o)-[:SHIPPED_FROM]->(w:Warehouse) RETURN o.id AS id,o.date AS date,o.status AS status,c.name AS customer,p.name AS product,i.quantity AS quantity,w.name AS warehouse ORDER BY o.date DESC")
    customers_list = query("MATCH (c:Customer) RETURN c.id AS id,c.name AS name ORDER BY c.name")
    products_list = query("MATCH (p:Product) RETURN p.id AS id,p.name AS name ORDER BY p.name")
    return render_template("orders.html", orders=rows, customers=customers_list, products=products_list)


@app.post("/orders/<order_id>/delete")
def delete_order(order_id):
    execute("MATCH (o:Order {id:$id}) OPTIONAL MATCH (o)-[i:CONTAINS]->(p:Product) OPTIONAL MATCH (o)-[:SHIPPED_FROM]->(w:Warehouse) OPTIONAL MATCH (p)-[s:STOCKED_AT]->(w) FOREACH (rel IN CASE WHEN s IS NULL THEN [] ELSE [s] END | SET rel.quantity=rel.quantity+i.quantity) WITH o DETACH DELETE o", id=order_id)
    flash("Order deleted and inventory restored.", "warning")
    return redirect(url_for("orders"))


@app.post("/reset")
def reset():
    seed_data()
    flash("Demo graph reset successfully.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    for attempt in range(20):
        try:
            initialise_database()
            break
        except Exception as exc:
            if attempt == 19:
                raise exc
            time.sleep(3)
    app.run(host="0.0.0.0", port=5000, debug=False)
