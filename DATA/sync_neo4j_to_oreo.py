#!/usr/bin/env python3
"""Attach neo4j_research (PostgreSQL) to OREO.

Reads the research datastore and regenerates OREO's graph data + exports:

  IDE/DATA/<category>.json          - per-category fact graphs (what the editor loads)
  IDE/DATA/index.json               - manifest: category -> fact_count, subcategories, file
  DATA/exports/facts_by_category.csv - every fact rowed with its category
  DATA/exports/sources_categories.csv - sources mapped to categories/subcategories
  DATA/exports/oreo_research_complete.csv - fixed full export (was broken: joined a
                                            nonexistent research_facts.section_id)

Facts are deduped on (key_term, value, source_url) keeping the highest confidence,
because past ingestion wrote some facts twice (verified: e.g. 'approaches' /
https://en.wikipedia.org/wiki/Graph_rewriting has 2 rows in research_facts).

Connects via TCP (peer auth not available to a script running as root):
  DBNAME=neo4j_research USER=postgres HOST=127.0.0.1 PASSWORD=postgres
All overridable via env: NEO4J_RESEARCH_DB, _USER, _HOST, _PASSWORD.

Usage:
  /root/.venv/bin/python DATA/sync_neo4j_to_oreo.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import psycopg2

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS = (REPO_ROOT / "IDE/DATA", REPO_ROOT / "DATA/exports")

DB = dict(
    dbname=os.environ.get("NEO4J_RESEARCH_DB", "neo4j_research"),
    user=os.environ.get("NEO4J_RESEARCH_USER", "postgres"),
    host=os.environ.get("NEO4J_RESEARCH_HOST", "127.0.0.1"),
    password=os.environ.get("NEO4J_RESEARCH_PASSWORD", "postgres"),
)


def fetch(conn):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.id, c.name
          FROM research_categories c
         ORDER BY c.name
        """
    )
    categories = cur.fetchall()

    cur.execute(
        """
        SELECT rsc.category_id, f.id, f.key_term, f.fact_type, f.value, f.confidence,
               s.url, s.title, s.id AS source_id
          FROM research_facts f
          JOIN research_sources s              ON s.id = f.source_id
          JOIN research_source_categories rsc  ON rsc.source_id = s.id
        """
    )
    fact_rows = cur.fetchall()

    cur.execute(
        """
        SELECT sc.category_id, sub.name, count(*)
          FROM research_source_subcategories ssc
          JOIN research_subcategories sub      ON sub.id = ssc.subcategory_id
          JOIN research_source_categories sc   ON sc.source_id = ssc.source_id
         GROUP BY sc.category_id, sub.name
         ORDER BY sc.category_id, sub.name
        """
    )
    subcat_rows = cur.fetchall()

    cur.execute(
        """
        SELECT s.url, s.title,
               string_agg(DISTINCT c.name, ', ' ORDER BY c.name) AS categories,
               string_agg(DISTINCT sub.name, ', ' ORDER BY sub.name) AS subcategories
          FROM research_sources s
          LEFT JOIN research_source_categories sc  ON sc.source_id = s.id
          LEFT JOIN research_categories c          ON c.id = sc.category_id
          LEFT JOIN research_source_subcategories ssc ON ssc.source_id = s.id
          LEFT JOIN research_subcategories sub     ON sub.id = ssc.subcategory_id
         GROUP BY s.url, s.title
         ORDER BY s.url
        """
    )
    source_rows = cur.fetchall()

    cur.execute(
        """
        SELECT s.url, s.title, f.key_term, f.fact_type, f.value, f.confidence
          FROM research_facts f
          JOIN research_sources s ON s.id = f.source_id
        """
    )
    all_fact_rows = cur.fetchall()
    cur.close()
    return categories, fact_rows, subcat_rows, source_rows, all_fact_rows


def dedupe(rows):
    """Collapse exact (key_term, value, source_url) repeats, keep max confidence."""
    best = {}
    for row in rows:
        key = (row["key_term"], row["value"], row["source_url"])
        current = best.get(key)
        if current is None or row["confidence"] > current["confidence"]:
            best[key] = row
    return best


def main():
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    categories, fact_rows, subcat_rows, source_rows, all_fact_rows = fetch(conn)
    conn.close()

    cat_name = dict(categories)
    facts_by_cat = {cid: [] for cid, _ in categories}
    for (cid, fid, key_term, fact_type, value, confidence, url, title, source_id) in fact_rows:
        facts_by_cat[cid].append(
            dict(
                fact_id=str(fid), key_term=key_term, fact_type=fact_type, value=value,
                confidence=float(confidence or 1.0), source_url=url, source_title=title,
                source_id=str(source_id),
            )
        )

    subcats_by_cat = {}
    for (cid, name, count) in subcat_rows:
        subcats_by_cat.setdefault(cid, {})[name] = count

    graphs = []
    manifest = {"total_facts": 0, "total_categories": len(categories), "categories": {}}

    for cid, name in categories:
        unique = dedupe(facts_by_cat[cid])
        fact_list = sorted(unique.values(), key=lambda r: (r["key_term"] or "", r["source_url"] or ""))
        slug = name.lower().replace(" ", "_")
        graphs.append(
            {"path": TARGETS[0] / f"{slug}.json", "category": name, "facts": fact_list}
        )
        manifest["total_facts"] += len(fact_list)
        manifest["categories"][name] = {
            "fact_count": len(fact_list),
            "subcategories": subcats_by_cat.get(cid, {}),
            "file": f"DATA/{slug}.json",
        }

    for target_dir in TARGETS:
        target_dir.mkdir(parents=True, exist_ok=True)

    for g in graphs:
        g["path"].write_text(
            json.dumps({"category": g["category"], "facts": g["facts"]}, indent=2)
            + "\n", encoding="utf-8",
        )
    (TARGETS[0] / "index.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    with (TARGETS[1] / "facts_by_category.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["category", "key_term", "fact_type", "value", "confidence", "source_url", "source_title"])
        for cid, name in categories:
            for r in sorted(dedupe(facts_by_cat[cid]).values(), key=lambda r: r["key_term"] or ""):
                w.writerow([name, r["key_term"], r["fact_type"], r["value"], r["confidence"],
                            r["source_url"], r["source_title"]])

    with (TARGETS[1] / "sources_categories.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["url", "title", "categories", "subcategories"])
        for url, title, cats, subs in source_rows:
            w.writerow([url, title, cats, subs])

    completed = dedupe(
        dict(
            key_term=r[2], fact_type=r[3], value=r[4],
            confidence=float(r[5] or 1.0), source_url=r[0], source_title=r[1],
        )
        for r in all_fact_rows
    )
    with (TARGETS[1] / "oreo_research_complete.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["key_term", "fact_type", "value", "confidence", "source_url", "source_title"])
        for r in sorted(completed.values(), key=lambda r: r["key_term"] or ""):
            w.writerow([r["key_term"], r["fact_type"], r["value"], r["confidence"],
                        r["source_url"], r["source_title"]])

    print(f"attached: {manifest['total_facts']} facts, {manifest['total_categories']} categories")
    print(f"  IDE/DATA: {len(graphs)} category json + index.json")
    print(f"  exports:  facts_by_category.csv, sources_categories.csv, oreo_research_complete.csv")
    for cid, name in categories:
        print(f"    {name:42s} {manifest['categories'][name]['fact_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())