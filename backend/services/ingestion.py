"""
Batch Ingestion Pipeline Service (PRJ-07).
Streams CSV and SQL files in chunks, applies canonical mapping, normalizes values,
and bulk-inserts records into the AttributeIndex EAV repository.
"""

import csv
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Generator, Optional
import pandas as pd
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Source, SourceColumn, AttributeIndex
from backend.services.normalizer import normalize_field
from backend.services.field_mapper import suggest_mappings


def extract_column_samples(file_path: str, columns: List[str], source_type: str = "CSV", max_samples: int = 3) -> Dict[str, List[str]]:
    """
    Extracts up to max_samples real non-null sample values for each column.
    """
    col_samples: Dict[str, List[str]] = {c: [] for c in columns}
    try:
        if source_type.upper() == "CSV":
            df = pd.read_csv(file_path, nrows=25, dtype=str, keep_default_na=False)
            for c in columns:
                if c in df.columns:
                    for val in df[c]:
                        v_str = str(val).strip()
                        if v_str and v_str.lower() != "nan" and v_str not in col_samples[c]:
                            col_samples[c].append(v_str)
                        if len(col_samples[c]) >= max_samples:
                            break
        elif source_type.upper() == "SQL":
            for chunk in stream_sql_records(file_path, columns, chunksize=25):
                for row in chunk:
                    for c in columns:
                        v = row.get(c)
                        if v is not None:
                            v_str = str(v).strip()
                            if v_str and v_str.lower() != "nan" and v_str not in col_samples[c]:
                                col_samples[c].append(v_str)
                break
    except Exception:
        pass
    return col_samples


def inspect_file_schema(file_path: str, source_type: str = "CSV") -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    Inspects a file to detect table/source name, column headers, and top sample rows.
    """
    path = Path(file_path)
    source_name = path.name

    if source_type.upper() == "CSV":
        df_sample = pd.read_csv(file_path, nrows=5, dtype=str, keep_default_na=False)
        columns = [str(c).strip() for c in df_sample.columns]
        sample_rows = df_sample.to_dict(orient="records")
        return source_name, columns, sample_rows

    elif source_type.upper() == "SQL":
        table_name, columns = parse_sql_metadata(file_path)
        sample_rows = []
        for chunk in stream_sql_records(file_path, columns, chunksize=5):
            sample_rows.extend(chunk[:5])
            break
        return table_name or source_name, columns, sample_rows

    else:
        raise ValueError(f"Unsupported source type: {source_type}")


def parse_sql_metadata(file_path: str) -> Tuple[str, List[str]]:
    """
    Parses table name and column list from DDL or INSERT headers in a .sql file.
    """
    table_name = Path(file_path).stem
    columns: List[str] = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read(15000)

    # 1. Check for CREATE TABLE statement
    create_match = re.search(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)\s*\((.*?)\);",
        content,
        re.DOTALL | re.IGNORECASE
    )
    if create_match:
        table_name = create_match.group(1).strip("`\"' ")
        body = create_match.group(2)
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if line and not line.upper().startswith(("PRIMARY", "FOREIGN", "KEY", "CONSTRAINT", "INDEX", "--")):
                parts = line.split()
                if parts:
                    col_name = parts[0].strip("`\"' ")
                    columns.append(col_name)

    # 2. Fallback to INSERT INTO statement columns
    if not columns:
        insert_match = re.search(
            r"INSERT\s+INTO\s+([^\s(]+)\s*\((.*?)\)\s*VALUES",
            content,
            re.DOTALL | re.IGNORECASE
        )
        if insert_match:
            table_name = insert_match.group(1).strip("`\"' ")
            cols_str = insert_match.group(2)
            columns = [c.strip("`\"' ") for c in cols_str.split(",") if c.strip()]

    return table_name, columns


def stream_csv_records(file_path: str, chunksize: int = 5000) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Reads CSV in chunks using pandas to prevent high memory consumption.
    """
    for df_chunk in pd.read_csv(file_path, chunksize=chunksize, dtype=str, keep_default_na=False):
        yield df_chunk.to_dict(orient="records")


def stream_sql_records(file_path: str, columns: List[str], chunksize: int = 5000) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Streamingly extracts row tuples from SQL INSERT clauses in batches.
    """
    chunk: List[Dict[str, Any]] = []
    in_values_block = False

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("--"):
                continue

            if "INSERT INTO" in line_str.upper() and "VALUES" in line_str.upper():
                in_values_block = True
                idx = line_str.upper().index("VALUES")
                val_part = line_str[idx + 6:].strip()
                if not val_part:
                    continue
                line_str = val_part

            if in_values_block:
                if line_str.startswith("(") and (line_str.endswith("),") or line_str.endswith(");") or line_str.endswith(")")):
                    trimmed = line_str.rstrip(",;").strip()
                    if trimmed.startswith("(") and trimmed.endswith(")"):
                        raw_tuple_str = trimmed[1:-1]
                        try:
                            parsed_vals = list(csv.reader([raw_tuple_str], quotechar="'", skipinitialspace=True))[0]
                            cleaned_vals = [v.replace("''", "'") for v in parsed_vals]
                            row_dict = {
                                col: cleaned_vals[i] if i < len(cleaned_vals) else ""
                                for i, col in enumerate(columns)
                            }
                            chunk.append(row_dict)
                            if len(chunk) >= chunksize:
                                yield chunk
                                chunk = []
                        except Exception:
                            continue
                if line_str.endswith(";"):
                    in_values_block = False

    if chunk:
        yield chunk


def ingest_source(source_id: int, db: Optional[Session] = None, chunksize: int = 5000) -> Dict[str, Any]:
    """
    Executes the ingestion workflow for a confirmed Source:
      1. Loads confirmed SourceColumn mappings.
      2. Streams records in chunks.
      3. Normalizes each mapped attribute.
      4. Bulk-inserts into AttributeIndex with raw and normalized forms.
      5. Updates Source.record_count and Source.status = 'INDEXED'.
    """
    close_db_on_exit = False
    if db is None:
        db = SessionLocal()
        close_db_on_exit = True

    try:
        source = db.query(Source).filter_by(id=source_id).first()
        if not source:
            raise ValueError(f"Source with id={source_id} not found.")

        # Load confirmed column mappings
        columns_meta = db.query(SourceColumn).filter_by(source_id=source.id).all()
        confirmed_map = {col.original_name: col for col in columns_meta}

        if not confirmed_map:
            raise ValueError(f"No confirmed column mappings found for Source id={source_id}.")

        file_path = source.file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found at: {file_path}")

        source_type = source.source_type.upper()
        if source_type == "CSV":
            streamer = stream_csv_records(file_path, chunksize=chunksize)
        elif source_type == "SQL":
            cols_list = list(confirmed_map.keys())
            streamer = stream_sql_records(file_path, columns=cols_list, chunksize=chunksize)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        # Ensure idempotency: clear prior indexed records for this source if any exist
        db.query(AttributeIndex).filter_by(source_id=source.id).delete()
        db.commit()

        total_records = 0
        attribute_entries: List[Dict[str, Any]] = []

        for chunk in streamer:
            for row in chunk:
                rec_idx = total_records
                total_records += 1

                for col_name, raw_val in row.items():
                    if col_name in confirmed_map:
                        col_def = confirmed_map[col_name]
                        canonical_field = col_def.canonical_field
                        if canonical_field == "custom":
                            # Still record custom fields for completeness or skip
                            pass

                        val_str = str(raw_val).strip() if raw_val is not None else ""
                        if val_str and val_str.lower() != "nan":
                            norm_val = normalize_field(canonical_field, val_str)
                            attribute_entries.append({
                                "workspace_id": source.workspace_id,
                                "source_id": source.id,
                                "record_index": rec_idx,
                                "canonical_field": canonical_field,
                                "original_value": val_str,
                                "normalized_value": norm_val,
                                "is_identifier": col_def.is_identifier
                            })


            # Bulk insert chunk of attribute indices
            if attribute_entries:
                db.bulk_insert_mappings(AttributeIndex, attribute_entries)
                db.commit()
                attribute_entries.clear()

        # Update source metadata upon completion
        source.record_count = total_records
        source.status = "INDEXED"
        db.commit()

        return {
            "source_id": source.id,
            "status": "INDEXED",
            "record_count": total_records
        }

    except Exception as e:
        db.rollback()
        # Mark source as FAILED
        try:
            source = db.query(Source).filter_by(id=source_id).first()
            if source:
                source.status = "FAILED"
                db.commit()
        except Exception:
            pass
        raise e
    finally:
        if close_db_on_exit:
            db.close()
