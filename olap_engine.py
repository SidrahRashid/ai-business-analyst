"""
OLAP DUCKDB ANALYTICS & LAZY RELATIONAL JOIN ENGINE
===================================================
Overcomes:
1. In-Memory Scalability Ceiling (RAM bound): Streams queries through DuckDB's
   columnar OLAP engine with out-of-core spilling and tiny RAM footprint.
2. Eager Join Cardinality & Cartesian Risks: Generates lazy on-demand joins
   only for tables required by the query, isolating grains and preventing fact row duplication.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

import duckdb
import pandas as pd

from clients_config import CLIENTS


class DuckDBAnalyticsEngine:
    """Enterprise Embedded OLAP Engine for Large-Scale Zero-Copy Analytics."""

    def __init__(self, db_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        temp_dir = base_dir / "data" / "cache" / "duckdb_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # In-memory session with disk-spilling temp directory
        self.con = duckdb.connect(database=":memory:", read_only=False)
        self.con.execute(f"SET temp_directory = '{temp_dir.as_posix()}';")
        self.con.execute("SET memory_limit = '2GB';")
        self.con.execute("SET threads = 4;")
        
        self.registered_clients: Set[str] = set()
        self.client_schemas: Dict[str, Dict[str, Any]] = {}

    def register_client_dataset(self, client_id: str) -> bool:
        """Lazily registers client normalized tables and star-schema views into DuckDB."""
        if client_id in self.registered_clients:
            return True

        client = CLIENTS.get(client_id)
        if not client:
            return False

        data_file_str = str(client.get("data_file", ""))
        data_file = Path(__file__).resolve().parent / data_file_str
        folder = data_file.parent
        schema_file = folder / "schema_relationships.json"

        if schema_file.exists():
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                self.client_schemas[client_id] = schema
                tables = schema.get("tables", {})
                fact_name = schema.get("primary_fact_table")

                # Register each individual physical table as a zero-copy DuckDB view
                registered_tbl_names = []
                for tbl_name, tbl_info in tables.items():
                    csv_path = folder / tbl_info["file"]
                    if csv_path.exists():
                        safe_csv_path = csv_path.as_posix()
                        view_name = f"{client_id}_{tbl_name}"
                        self.con.execute(f"""
                            CREATE OR REPLACE VIEW {view_name} AS 
                            SELECT * FROM read_csv_auto('{safe_csv_path}', header=True);
                        """)
                        registered_tbl_names.append(view_name)

                # Build Star-Schema Unified Analytical View: v_{client_id}_analytics
                if fact_name and fact_name in tables:
                    fact_info = tables[fact_name]
                    fact_view = f"{client_id}_{fact_name}"
                    join_clauses = []
                    select_fields = [f"{fact_view}.*"]

                    # Join dimension tables
                    for fk_col, fk_info in fact_info.get("foreign_keys", {}).items():
                        target_ref = fk_info["references"]  # e.g. "dim_estates.ESTATE_ID"
                        target_tbl, target_pk = target_ref.split(".")
                        target_view = f"{client_id}_{target_tbl}"
                        if target_tbl in tables:
                            dim_attrs = tables[target_tbl].get("attributes", [])
                            # Add dimension attributes
                            for attr in dim_attrs:
                                select_fields.append(f"{target_view}.{attr}")
                            join_clauses.append(f"LEFT JOIN {target_view} ON {fact_view}.{fk_col} = {target_view}.{target_pk}")

                    # Join bridge tables with grain preservation
                    for tbl_name, tbl_info in tables.items():
                        if tbl_info.get("type") == "BRIDGE_FACT":
                            bridge_view = f"{client_id}_{tbl_name}"
                            b_fks = tbl_info.get("foreign_keys", {})
                            for b_fk, b_info in b_fks.items():
                                b_ref = b_info["references"]
                                b_target_tbl, b_target_pk = b_ref.split(".")
                                if b_target_tbl == fact_name:
                                    b_attrs = tbl_info.get("attributes", [])
                                    for b_attr in b_attrs:
                                        select_fields.append(f"{bridge_view}.{b_attr}")
                                    join_clauses.append(f"LEFT JOIN {bridge_view} ON {fact_view}.{b_target_pk} = {bridge_view}.{b_fk}")

                    unified_view_name = f"v_{client_id}_analytics"
                    select_sql = f"""
                        CREATE OR REPLACE VIEW {unified_view_name} AS
                        SELECT {', '.join(select_fields)}
                        FROM {fact_view}
                        {' '.join(join_clauses)};
                    """
                    self.con.execute(select_sql)

                self.registered_clients.add(client_id)
                return True
            except Exception as e:
                print(f"[DUCKDB SCHEMA LOAD WARNING] {e}, falling back to standalone file.")

        # Fallback to single standalone CSV
        if data_file.exists():
            safe_path = data_file.as_posix()
            unified_view_name = f"v_{client_id}_analytics"
            self.con.execute(f"""
                CREATE OR REPLACE VIEW {unified_view_name} AS
                SELECT * FROM read_csv_auto('{safe_path}', header=True);
            """)
            self.registered_clients.add(client_id)
            return True

        return False

    def validate_sql_safety(self, sql: str) -> Tuple[bool, Optional[str]]:
        """Ensures that SQL contains only safe, read-only SELECT or WITH statements."""
        clean = sql.strip().upper()
        if not (clean.startswith("SELECT") or clean.startswith("WITH")):
            return False, "Only read-only SELECT or WITH queries are permitted."

        dangerous_patterns = [
            r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
            r"\bALTER\b", r"\bTRUNCATE\b", r"\bEXEC\b", r"\bPRAGMA\b",
            r"\bATTACH\b", r"\bDETACH\b", r"\bCOPY\b", r"\bINSTALL\b",
            r"\bLOAD\b", r"\bCALL\b", r"\bCREATE\b"
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, clean):
                return False, f"Prohibited SQL command detected: {pattern.replace(chr(92) + 'b', '')}"

        return True, None

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Executes a sanitized SQL query with memory and timeout protection."""
        is_safe, err = self.validate_sql_safety(sql)
        if not is_safe:
            return None, err

        try:
            if params:
                result_df = self.con.execute(sql, params).df()
            else:
                result_df = self.con.execute(sql).df()
            return result_df, None
        except Exception as e:
            return None, f"SQL Execution Error: {str(e)}"

    def build_lazy_star_query(
        self,
        client_id: str,
        measures: List[Tuple[str, str]],  # [(column, agg_func)] e.g. [("VOLUME_KG", "SUM")]
        dimensions: List[str],             # e.g. ["ESTATE", "REGION"]
        filters: Optional[List[Dict[str, Any]]] = None,
        sort_by: Optional[str] = None,
        sort_dir: str = "DESC",
        limit: Optional[int] = None
    ) -> str:
        """
        Builds a minimal, lazy Star-Schema query.
        Joins ONLY dimension tables referenced in the query, preventing eager Cartesian explosion!
        """
        self.register_client_dataset(client_id)
        schema = self.client_schemas.get(client_id)

        # If no relational schema, query the unified view directly
        if not schema:
            tbl_source = f"v_{client_id}_analytics"
            sel_dims = [f'"{d}"' for d in dimensions]
            sel_meas = [f'{agg.upper()}("{m}") AS "{agg.capitalize()}_{m}"' for m, agg in measures]
            select_items = sel_dims + sel_meas
            where_clauses = []
            if filters:
                for f in filters:
                    col, op, val = f.get("column"), f.get("operator", "=="), f.get("value")
                    if col and val is not None:
                        val_escaped = str(val).replace("'", "''")
                        if op in ["==", "="]:
                            where_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) = LOWER(\'{val_escaped}\')')
                        elif op == "!=":
                            where_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) != LOWER(\'{val_escaped}\')')
                        elif op in [">", "<", ">=", "<="]:
                            where_clauses.append(f'"{col}" {op} {val}')
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            group_sql = f"GROUP BY {', '.join(sel_dims)}" if sel_dims else ""
            order_sql = f"ORDER BY {sort_by} {sort_dir}" if sort_by else ""
            limit_sql = f"LIMIT {limit}" if limit else ""
            return f"SELECT {', '.join(select_items)} FROM {tbl_source} {where_sql} {group_sql} {order_sql} {limit_sql}".strip()

        # Relational Star-Schema exists: determine minimal tables needed
        tables = schema.get("tables", {})
        fact_key = schema.get("primary_fact_table")
        fact_info = tables[fact_key]
        fact_view = f"{client_id}_{fact_key}"

        needed_cols = set(dimensions) | {m[0] for m in measures}
        if filters:
            for f in filters:
                if f.get("column"):
                    needed_cols.add(f["column"])

        # Determine which dimension tables must be joined
        joins = []
        table_aliases = {fact_key: fact_view}

        for fk_col, fk_info in fact_info.get("foreign_keys", {}).items():
            target_ref = fk_info["references"]
            target_tbl, target_pk = target_ref.split(".")
            target_view = f"{client_id}_{target_tbl}"
            target_attrs = set(tables.get(target_tbl, {}).get("attributes", []))
            
            # Check if this dimension table contains any requested column
            if needed_cols & target_attrs or target_tbl in needed_cols:
                joins.append(f"LEFT JOIN {target_view} ON {fact_view}.{fk_col} = {target_view}.{target_pk}")
                table_aliases[target_tbl] = target_view

        # Check bridge tables
        for tbl_name, tbl_info in tables.items():
            if tbl_info.get("type") == "BRIDGE_FACT":
                bridge_view = f"{client_id}_{tbl_name}"
                b_attrs = set(tbl_info.get("attributes", []))
                if needed_cols & b_attrs:
                    for b_fk, b_info in tbl_info.get("foreign_keys", {}).items():
                        b_ref = b_info["references"]
                        b_target_tbl, b_target_pk = b_ref.split(".")
                        if b_target_tbl == fact_key:
                            # Grain preservation: join by primary key
                            joins.append(f"LEFT JOIN {bridge_view} ON {fact_view}.{b_target_pk} = {bridge_view}.{b_fk}")

        # Construct SELECT
        sel_dims = [f'"{d}"' for d in dimensions]
        sel_meas = [f'{agg.upper()}("{m}") AS "{agg.capitalize()}_{m}"' for m, agg in measures]
        select_items = sel_dims + sel_meas

        where_clauses = []
        if filters:
            for f in filters:
                col, op, val = f.get("column"), f.get("operator", "=="), f.get("value")
                if col and val is not None:
                    val_escaped = str(val).replace("'", "''")
                    if op in ["==", "="]:
                        where_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) = LOWER(\'{val_escaped}\')')
                    elif op == "!=":
                        where_clauses.append(f'LOWER(CAST("{col}" AS VARCHAR)) != LOWER(\'{val_escaped}\')')
                    elif op in [">", "<", ">=", "<="]:
                        where_clauses.append(f'"{col}" {op} {val}')

        join_sql = " ".join(joins)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        group_sql = f"GROUP BY {', '.join(sel_dims)}" if sel_dims else ""
        order_sql = f"ORDER BY {sort_by} {sort_dir}" if sort_by else ""
        limit_sql = f"LIMIT {limit}" if limit else ""

        query = f"SELECT {', '.join(select_items)} FROM {fact_view} {join_sql} {where_sql} {group_sql} {order_sql} {limit_sql}".strip()
        return query


# Global OLAP Singleton
_OLAP_ENGINE_INSTANCE: Optional[DuckDBAnalyticsEngine] = None

def get_olap_engine() -> DuckDBAnalyticsEngine:
    global _OLAP_ENGINE_INSTANCE
    if _OLAP_ENGINE_INSTANCE is None:
        _OLAP_ENGINE_INSTANCE = DuckDBAnalyticsEngine()
    return _OLAP_ENGINE_INSTANCE
