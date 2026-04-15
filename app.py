from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_PATH = r"C:\Users\raperez\Documents\kiosk\qc_kiosk.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Business Units ──────────────────────────────
@app.route("/api/business_units")
def business_units():
    conn = get_db()
    rows = conn.execute("SELECT * FROM business_units WHERE active=1").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Products ─────────────────────────────────────
@app.route("/api/products")
def products():
    bu = request.args.get("bu")
    conn = get_db()
    if bu:
        rows = conn.execute("""
            SELECT p.*, b.code AS bu_code
            FROM products p
            JOIN business_units b ON b.id = p.business_unit_id
            WHERE b.code = ? AND p.active = 1
            ORDER BY p.name
        """, (bu,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.*, b.code AS bu_code
            FROM products p
            JOIN business_units b ON b.id = p.business_unit_id
            WHERE p.active = 1
            ORDER BY p.name
        """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Controls por producto ─────────────────────────
@app.route("/api/products/<int:product_id>/controls")
def controls(product_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM controls
        WHERE product_id = ?
        ORDER BY sort_order
    """, (product_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Guardar inspección ────────────────────────────
@app.route("/api/inspections", methods=["POST"])
def save_inspection():
    data = request.get_json()
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO inspections
            (product_id, business_unit_id, operator_number, operator_name,
             shift, lot_number, result, folio, containment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["product_id"], data["business_unit_id"],
        data["operator_number"], data["operator_name"],
        data["shift"], data.get("lot_number"),
        data["result"], data["folio"], data.get("containment")
    ))
    inspection_id = cur.lastrowid
    for r in data["results"]:
        conn.execute("""
            INSERT INTO inspection_results
                (inspection_id, control_id, value_text, value_numeric, result)
            VALUES (?, ?, ?, ?, ?)
        """, (
            inspection_id, r["control_id"],
            r.get("value_text"), r.get("value_numeric"), r["result"]
        ))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "inspection_id": inspection_id}), 201


# ── Listar inspecciones ───────────────────────────
@app.route("/api/inspections")
def list_inspections():
    conn = get_db()
    rows = conn.execute("""
        SELECT i.*, p.name AS product_name, p.part_number, b.code AS bu_code
        FROM inspections i
        JOIN products p ON p.id = i.product_id
        JOIN business_units b ON b.id = i.business_unit_id
        ORDER BY i.created_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
