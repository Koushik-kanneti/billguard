import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "billguard.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name       TEXT    NOT NULL,
            address             TEXT,
            lat                 REAL,
            lng                 REAL,
            bill_type           TEXT,
            risk_level          TEXT,
            estimated_overcharge REAL   DEFAULT 0,
            issues              TEXT,
            timestamp           TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_report(business_name, address, lat, lng,
                  bill_type, risk_level, estimated_overcharge, issues: list):
    conn = get_conn()
    conn.execute("""
        INSERT INTO reports
            (business_name, address, lat, lng, bill_type, risk_level,
             estimated_overcharge, issues, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        business_name, address, lat, lng, bill_type, risk_level,
        estimated_overcharge, json.dumps(issues),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def _risk_color(report_count, avg_overcharge, high_count):
    """Simple scoring → red / orange / green marker color."""
    score = 0
    score += min(report_count * 15, 40)          # frequency  (max 40)
    score += min((avg_overcharge or 0) / 200, 30) # severity   (max 30)
    score += min(high_count * 10, 30)              # % high-risk (max 30)
    if score >= 55:
        return "red"
    if score >= 25:
        return "orange"
    return "green"


def get_map_markers():
    """Return one aggregated marker per unique business name."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            business_name,
            MAX(address)        AS address,
            AVG(lat)            AS lat,
            AVG(lng)            AS lng,
            MAX(bill_type)      AS bill_type,
            COUNT(*)            AS report_count,
            AVG(estimated_overcharge)  AS avg_overcharge,
            MAX(estimated_overcharge)  AS max_overcharge,
            SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_count,
            GROUP_CONCAT(issues, '|||') AS all_issues,
            MAX(timestamp)      AS last_seen
        FROM reports
        WHERE lat IS NOT NULL AND lng IS NOT NULL
        GROUP BY LOWER(TRIM(business_name))
        ORDER BY report_count DESC
    """).fetchall()
    conn.close()

    result = []
    for row in rows:
        # Flatten all issue arrays into one list
        all_issues = []
        if row["all_issues"]:
            for chunk in row["all_issues"].split("|||"):
                try:
                    all_issues.extend(json.loads(chunk))
                except Exception:
                    pass
        common = [item for item, _ in Counter(all_issues).most_common(3)]

        result.append({
            "business_name": row["business_name"],
            "address":       row["address"],
            "lat":           row["lat"],
            "lng":           row["lng"],
            "bill_type":     row["bill_type"],
            "report_count":  row["report_count"],
            "avg_overcharge": round(row["avg_overcharge"] or 0, 2),
            "max_overcharge": round(row["max_overcharge"] or 0, 2),
            "risk_color":    _risk_color(row["report_count"],
                                         row["avg_overcharge"],
                                         row["high_count"]),
            "common_issues": common,
            "last_seen":     (row["last_seen"] or "")[:10],
        })
    return result


def search_businesses(query: str):
    if not query.strip():
        return []
    conn = get_conn()
    like = f"%{query.strip()}%"
    rows = conn.execute("""
        SELECT
            business_name,
            MAX(address)        AS address,
            MAX(bill_type)      AS bill_type,
            COUNT(*)            AS report_count,
            AVG(estimated_overcharge) AS avg_overcharge,
            SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_count
        FROM reports
        WHERE business_name LIKE ? OR address LIKE ?
        GROUP BY LOWER(TRIM(business_name))
        ORDER BY report_count DESC
        LIMIT 10
    """, (like, like)).fetchall()
    conn.close()
    out = []
    for row in rows:
        out.append({
            "business_name":  row["business_name"],
            "address":        row["address"],
            "bill_type":      row["bill_type"],
            "report_count":   row["report_count"],
            "avg_overcharge": round(row["avg_overcharge"] or 0, 2),
            "risk_color":     _risk_color(row["report_count"],
                                          row["avg_overcharge"],
                                          row["high_count"]),
        })
    return out


def get_business_reports(business_name: str, limit: int = 6):
    """Individual report history for a specific business (for side panel)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT risk_level, estimated_overcharge, issues, timestamp, bill_type, address
        FROM reports
        WHERE LOWER(TRIM(business_name)) = LOWER(TRIM(?))
        ORDER BY timestamp DESC
        LIMIT ?
    """, (business_name, limit)).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        try:
            d["issues"] = json.loads(d["issues"] or "[]")
        except Exception:
            d["issues"] = []
        d["timestamp"] = (d["timestamp"] or "")[:10]
        result.append(d)
    return result


def get_stats():
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(*) AS total_reports,
               COUNT(DISTINCT LOWER(TRIM(business_name))) AS total_businesses,
               SUM(estimated_overcharge) AS total_overcharge
        FROM reports
    """).fetchone()
    conn.close()
    return {
        "total_reports":     row["total_reports"] or 0,
        "total_businesses":  row["total_businesses"] or 0,
        "total_overcharge":  round(row["total_overcharge"] or 0, 2),
    }
