"""
Synthetic Data Generation Pipeline for Progressive Entity Resolution (PRJ-07).
Generates 1,200 base identities across 4 disparate operational silos with
intentional schema divergence and progressive multi-hop discovery chaining.
"""

import os
import random
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from faker import Faker

# Base directories
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR

TOTAL_POPULATION = 1200
SEED = 42


def generate_synthetic_datasets():
    """
    Generate synthetic data for HR, CRM, Platform, and Membership operational silos.
    Guarantees progressive 4-database chaining for entity resolution.
    """
    print(f"[*] Initializing Faker with SEED={SEED} for {TOTAL_POPULATION} unique identities...")
    fake = Faker()
    Faker.seed(SEED)
    random.seed(SEED)

    # 1. Anchor entity: John Doe (Explicitly configured for deterministic evaluation)
    john_doe_identity = {
        "id": 0,
        "full_name": "John Doe",
        "crm_name": "John Doe",
        "hr_email": "john@example.com",
        "crm_email": "john.doe.crm@enterprise.com",
        "platform_phone": "9876543210",
        "hr_mobile": "9876543210",
        "crm_contact": "9876543210",
        "address": "Mumbai",
        "username": "johndoe",
        "company": "ABC Pvt Ltd",
        "registered_ip": "103.21.124.50",
        "member_id": "M1042",
        "loyalty_tier": "Platinum",
        "membership_email": "johndoe.loyalty@club.com",
        "employee_id": "EMP1001",
        "client_id": "CRM1001"
    }

    base_identities: List[Dict[str, Any]] = [john_doe_identity]

    # Pre-generate unique usernames and phone numbers
    used_usernames = {"johndoe"}
    used_phones = {"9876543210"}
    used_emails = {"john@example.com"}

    loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    tier_weights = [0.45, 0.30, 0.15, 0.10]

    # Major metropolitan hubs for realistic address clustering
    locations = [
        "Mumbai", "Bengaluru", "Delhi NCR", "Hyderabad", "Pune",
        "Chennai", "Kolkata", "San Francisco, CA", "New York, NY",
        "London, UK", "Singapore", "Berlin, DE"
    ]

    print(f"[*] Generating {TOTAL_POPULATION - 1} background synthetic identities...")
    for idx in range(1, TOTAL_POPULATION):
        emp_num = 1001 + idx
        full_name = fake.name()

        # Generate unique phone
        while True:
            phone_num = f"9{random.randint(100000000, 999999999)}"
            if phone_num not in used_phones:
                used_phones.add(phone_num)
                break

        # Generate unique clean username
        clean_name = full_name.lower().replace(" ", "").replace(".", "").replace("'", "")[:8]
        username_candidate = f"{clean_name}{random.randint(10, 999)}"
        while username_candidate in used_usernames:
            username_candidate = f"{clean_name}{random.randint(1000, 9999)}"
        used_usernames.add(username_candidate)

        company_name = fake.company().replace("'", "")
        address = f"{random.choice(locations)}, {fake.street_address().replace("'", "")}"
        ip_addr = fake.ipv4()
        tier = random.choices(loyalty_tiers, weights=tier_weights)[0]

        hr_mail = f"{username_candidate}@corporate.net"
        crm_mail = f"{username_candidate}@clientlink.io"
        mem_mail = f"{username_candidate}@rewardsportal.org"

        base_identities.append({
            "id": idx,
            "full_name": full_name,
            "crm_name": full_name,
            "hr_email": hr_mail,
            "crm_email": crm_mail,
            "platform_phone": phone_num,
            "hr_mobile": phone_num,
            "crm_contact": phone_num,
            "address": address,
            "username": username_candidate,
            "company": company_name,
            "registered_ip": ip_addr,
            "member_id": f"M{2000 + idx}",
            "loyalty_tier": tier,
            "membership_email": mem_mail,
            "employee_id": f"EMP{emp_num}",
            "client_id": f"CRM{emp_num}"
        })

    print("[*] Assembling silo tables with disparate operational schemas...")

    # --- Silo 1: HR DB ---
    # columns: [employee_id, full_name, email, mobile_number]
    hr_records = []
    for p in base_identities:
        hr_records.append({
            "employee_id": p["employee_id"],
            "full_name": p["full_name"],
            "email": p["hr_email"],
            "mobile_number": p["hr_mobile"]
        })
    df_hr = pd.DataFrame(hr_records)
    # Shuffle for realistic non-indexed alignment while preserving deterministic seed
    df_hr = df_hr.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    # --- Silo 2: CRM DB ---
    # columns: [client_id, name, email_id, contact_no, address]
    crm_records = []
    for p in base_identities:
        crm_records.append({
            "client_id": p["client_id"],
            "name": p["crm_name"],
            "email_id": p["crm_email"],
            "contact_no": p["crm_contact"],
            "address": p["address"]
        })
    df_crm = pd.DataFrame(crm_records)
    df_crm = df_crm.sample(frac=1.0, random_state=SEED + 1).reset_index(drop=True)

    # --- Silo 3: Platform DB ---
    # columns: [username, phone, company, registered_ip]
    platform_records = []
    for p in base_identities:
        platform_records.append({
            "username": p["username"],
            "phone": p["platform_phone"],
            "company": p["company"],
            "registered_ip": p["registered_ip"]
        })
    df_platform = pd.DataFrame(platform_records)
    df_platform = df_platform.sample(frac=1.0, random_state=SEED + 2).reset_index(drop=True)

    # --- Silo 4: Membership DB ---
    # columns: [member_id, email, username, loyalty_tier]
    membership_records = []
    for p in base_identities:
        membership_records.append({
            "member_id": p["member_id"],
            "email": p["membership_email"],
            "username": p["username"],
            "loyalty_tier": p["loyalty_tier"]
        })
    df_membership = pd.DataFrame(membership_records)
    df_membership = df_membership.sample(frac=1.0, random_state=SEED + 3).reset_index(drop=True)

    # Export to CSV
    hr_csv_path = OUTPUT_DIR / "hr_db.csv"
    crm_csv_path = OUTPUT_DIR / "crm_db.csv"
    platform_csv_path = OUTPUT_DIR / "platform_db.csv"
    membership_csv_path = OUTPUT_DIR / "membership_db.csv"

    df_hr.to_csv(hr_csv_path, index=False)
    df_crm.to_csv(crm_csv_path, index=False)
    df_platform.to_csv(platform_csv_path, index=False)
    df_membership.to_csv(membership_csv_path, index=False)

    print(f"    [+] Saved: {hr_csv_path.name} ({len(df_hr)} records)")
    print(f"    [+] Saved: {crm_csv_path.name} ({len(df_crm)} records)")
    print(f"    [+] Saved: {platform_csv_path.name} ({len(df_platform)} records)")
    print(f"    [+] Saved: {membership_csv_path.name} ({len(df_membership)} records)")

    # 4. Generate SQL Dumps for HR and CRM
    hr_sql_path = OUTPUT_DIR / "hr_db.sql"
    crm_sql_path = OUTPUT_DIR / "crm_db.sql"

    generate_sql_dump(
        table_name="hr_db",
        df=df_hr,
        output_path=hr_sql_path,
        col_defs={
            "employee_id": "VARCHAR(50) PRIMARY KEY",
            "full_name": "VARCHAR(255) NOT NULL",
            "email": "VARCHAR(255)",
            "mobile_number": "VARCHAR(50)"
        }
    )

    generate_sql_dump(
        table_name="crm_db",
        df=df_crm,
        output_path=crm_sql_path,
        col_defs={
            "client_id": "VARCHAR(50) PRIMARY KEY",
            "name": "VARCHAR(255) NOT NULL",
            "email_id": "VARCHAR(255)",
            "contact_no": "VARCHAR(50)",
            "address": "VARCHAR(255)"
        }
    )

    return df_hr, df_crm, df_platform, df_membership


def generate_sql_dump(table_name: str, df: pd.DataFrame, output_path: Path, col_defs: Dict[str, str]):
    """
    Generate clean ANSI SQL DDL and INSERT statements compatible with SQLite, PostgreSQL, and MySQL.
    """
    lines = [
        f"-- SQL Dump for {table_name}",
        f"-- Generated for Unified Progressive Entity Resolution (PRJ-07)",
        f"-- Total Records: {len(df)}",
        "",
        f"DROP TABLE IF EXISTS {table_name};",
        f"CREATE TABLE {table_name} ("
    ]

    col_lines = [f"    {col} {datatype}" for col, datatype in col_defs.items()]
    lines.append(",\n".join(col_lines))
    lines.append(");\n")

    cols = list(col_defs.keys())
    cols_joined = ", ".join(cols)

    # Batch INSERT statements in groups of 50 for optimal execution
    batch_size = 50
    for i in range(0, len(df), batch_size):
        chunk = df.iloc[i:i + batch_size]
        value_tuples = []
        for _, row in chunk.iterrows():
            formatted_vals = []
            for col in cols:
                val = str(row[col]) if pd.notna(row[col]) else ""
                val_escaped = val.replace("'", "''")
                formatted_vals.append(f"'{val_escaped}'")
            value_tuples.append(f"({', '.join(formatted_vals)})")
        
        insert_stmt = f"INSERT INTO {table_name} ({cols_joined}) VALUES\n" + ",\n".join(value_tuples) + ";"
        lines.append(insert_stmt)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"    [+] Saved SQL Dump: {output_path.name} ({len(df)} rows)")


def demonstrate_link_chain(target_name: str = "John Doe"):
    """
    Demonstrate the progressive 4-database discovery path starting from a single target entity.
    """
    print("\n" + "=" * 78)
    print(f" PROGRESSIVE ENRICHMENT DISCOVERY PATHWAY: Target = '{target_name}'")
    print("=" * 78)

    df_hr = pd.read_csv(OUTPUT_DIR / "hr_db.csv")
    df_crm = pd.read_csv(OUTPUT_DIR / "crm_db.csv")
    df_platform = pd.read_csv(OUTPUT_DIR / "platform_db.csv")
    df_membership = pd.read_csv(OUTPUT_DIR / "membership_db.csv")

    # Step 1: Initial Discovery in HR DB
    print("\n[HOP 1] Initial Seeding / Query in `hr_db`:")
    hr_match = df_hr[df_hr["full_name"] == target_name]
    if hr_match.empty:
        print(f"    [-] Target '{target_name}' not found in HR DB.")
        return
    hr_row = hr_match.iloc[0]
    print(f"    Found in hr_db.csv:")
    print(f"      employee_id   : {hr_row['employee_id']}")
    print(f"      full_name     : {hr_row['full_name']}")
    print(f"      email         : {hr_row['email']}")
    print(f"      mobile_number : {hr_row['mobile_number']}")

    # Step 2: Progressive Hop to CRM DB via mobile_number and name
    mobile_key = str(hr_row["mobile_number"]).strip()
    print(f"\n    --> PROGRESSIVE HOP: Linking to `crm_db` using contact_no='{mobile_key}'...")
    crm_match = df_crm[df_crm["contact_no"].astype(str).str.strip() == mobile_key]
    if crm_match.empty:
        print(f"    [-] Entity link failed at CRM DB.")
        return
    crm_row = crm_match.iloc[0]
    print(f"[HOP 2] Discovered in `crm_db.csv` (Attributes Enriched: address):")
    print(f"      client_id     : {crm_row['client_id']}")
    print(f"      name          : {crm_row['name']}")
    print(f"      email_id      : {crm_row['email_id']}")
    print(f"      contact_no    : {crm_row['contact_no']}")
    print(f"      address       : {crm_row['address']}")

    # Step 3: Progressive Hop to Platform DB via phone
    print(f"\n    --> PROGRESSIVE HOP: Linking to `platform_db` using phone='{mobile_key}'...")
    plat_match = df_platform[df_platform["phone"].astype(str).str.strip() == mobile_key]
    if plat_match.empty:
        print(f"    [-] Entity link failed at Platform DB.")
        return
    plat_row = plat_match.iloc[0]
    discovered_username = plat_row["username"]
    print(f"[HOP 3] Discovered in `platform_db.csv` (Attributes Enriched: username, company, IP):")
    print(f"      phone         : {plat_row['phone']}")
    print(f"      username      : {plat_row['username']}")
    print(f"      company       : {plat_row['company']}")
    print(f"      registered_ip : {plat_row['registered_ip']}")

    # Step 4: Progressive Hop to Membership DB via username
    print(f"\n    --> PROGRESSIVE HOP: Linking to `membership_db` using username='{discovered_username}'...")
    mem_match = df_membership[df_membership["username"] == discovered_username]
    if mem_match.empty:
        print(f"    [-] Entity link failed at Membership DB.")
        return
    mem_row = mem_match.iloc[0]
    print(f"[HOP 4] Discovered in `membership_db.csv` (Attributes Enriched: member_id, loyalty_tier):")
    print(f"      username      : {mem_row['username']}")
    print(f"      member_id     : {mem_row['member_id']}")
    print(f"      loyalty_tier  : {mem_row['loyalty_tier']}")
    print(f"      email         : {mem_row['email']}")

    # Unified 360 Golden Entity Synthesis
    print("\n" + "-" * 78)
    print(" [SYNTHESIZED 360-DEGREE GOLDEN RECORD]")
    print(f"   Name          : {hr_row['full_name']}")
    print(f"   Mobile / Phone: {hr_row['mobile_number']}")
    print(f"   Address       : {crm_row['address']}")
    print(f"   Employer      : {plat_row['company']}")
    print(f"   Platform User : {plat_row['username']} (IP: {plat_row['registered_ip']})")
    print(f"   Member ID     : {mem_row['member_id']}")
    print(f"   Loyalty Status: {mem_row['loyalty_tier']}")
    print(f"   Known Emails  : {hr_row['email']} (HR) | {crm_row['email_id']} (CRM) | {mem_row['email']} (Membership)")
    print("-" * 78)


if __name__ == "__main__":
    generate_synthetic_datasets()
    demonstrate_link_chain("John Doe")
