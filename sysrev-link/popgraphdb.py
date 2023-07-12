import json
import sqlite3
import psycopg2, psycopg2.extras
import datetime
from psycopg2 import sql
from neo4j import GraphDatabase, basic_auth
from tqdm import tqdm

# Connect to Neo4j
neo4j_host = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_password = "test1234"
neo4j_driver = GraphDatabase.driver(neo4j_host, auth=basic_auth(neo4j_user, neo4j_password))

# Connect to PostgreSQL
pg_conn = psycopg2.connect(dbname="sysrev", user="postgres", host="localhost", port="5470")
pg_cursor = pg_conn.cursor()

def convert_val(val):
    # if isinstance(val, datetime.datetime):
    #     return val.isoformat()
    if isinstance(val, dict):
        return json.dumps(val)
    return val


project_id=1 

# ARTICLE CONVERSION
pg_query = "SELECT * FROM article WHERE project_id = %s"
pg_cursor.execute(pg_query, (project_id,))
rows = pg_cursor.fetchall()
columns = [desc[0] for desc in pg_cursor.description]

with neo4j_driver.session() as session:
    for row in rows:
        node_properties = {column: convert_val(value) for column, value in zip(columns, row)}
        session.run("CREATE (a:Document $props)", props=node_properties)

# PROJECT_SOURCE
pg_query = "SELECT * FROM project_source WHERE project_id = %s"
pg_cursor.execute(pg_query, (project_id,))
rows = pg_cursor.fetchall()
columns = [desc[0] for desc in pg_cursor.description]

with neo4j_driver.session() as session:
    for row in rows:
        node_properties = {column: convert_val(value) for column, value in zip(columns, row)}
        session.run("CREATE (a:DocumentSource $props)", props=node_properties)

# ARTICLE SOURCE

with neo4j_driver.session() as session:
    _ = session.run("CREATE INDEX source_idx FOR (n:DocumentSource) ON (n.source_id)")    
    _ = session.run("CREATE INDEX article_idx FOR (n:Document) ON (n.article_id)")
    
pg_query = """SELECT source_id, art.article_id FROM article_source as asrc
    JOIN article art ON asrc.article_id = art.article_id WHERE art.project_id = %s"""

pg_cursor.execute(pg_query, (project_id,))
rows = pg_cursor.fetchall()
columns = [desc[0] for desc in pg_cursor.description]

with neo4j_driver.session() as session:
    batch_size = 100
    for i in tqdm(range(0, len(rows), batch_size)):
        batch = rows[i:i + batch_size]
        params = [{'sid': sid, 'aid': aid} for sid, aid in batch]
        _ = session.run("""
        UNWIND $params AS param
        MATCH (s:DocumentSource {source_id: param.sid}), (a:Document {article_id: param.aid})
        CREATE (s)-[:SOURCE_OF]->(a)
        """, params=params)

# ARTICLE_DATA

# LABEL CONVERSION
pg_query = "SELECT * FROM label WHERE project_id = %s"
pg_cursor.execute(pg_query, (project_id,))
rows = pg_cursor.fetchall()
columns = [desc[0] for desc in pg_cursor.description]

with neo4j_driver.session() as session:
    for row in rows:
        node_properties = {column: convert_val(value) for column, value in zip(columns, row)}
        session.run("CREATE (a:Label $props)", props=node_properties)

with neo4j_driver.session() as session:
    _ = session.run("CREATE INDEX label_idx FOR (n:Label) ON (n.label_id)")

# ARTICLE_LABEL
pg_query = "SELECT * FROM article_label al JOIN article ar on al.article_id=ar.article_id WHERE project_id = %s"
pg_cursor.execute(pg_query, (project_id,))
rows = pg_cursor.fetchall()
columns = [desc[0] for desc in pg_cursor.description]

with neo4j_driver.session() as session:
    for row in tqdm(rows):
        node_properties = {column: convert_val(value) for column, value in zip(columns, row)}
        _ = session.run("CREATE (a:Answer $props)", props=node_properties)

with neo4j_driver.session() as session:
    _ = session.run("CREATE INDEX answer_idx FOR (n:Answer) ON (n.article_label_id)")

with neo4j_driver.session() as session:
    batch_size = 100
    for i in tqdm(range(0, len(rows), batch_size)):
        batch = rows[i:i + batch_size]
        dicts = [{column: convert_val(value) for column, value in zip(columns, row)} for row in batch]
        params = [{'lid': x['label_id'], 'aid': x['article_id'], 'alid': x["article_label_id"]} for x in dicts]
        _ = session.run("""
        UNWIND $params AS param
        MATCH (a:Document {article_id: param.aid}), (l:Label {label_id: param.lid})
        CREATE (s)-[:SOURCE_OF]->(a)
        """, params=params)
        
# direct_exports = {
#     "article": "SELECT * FROM article WHERE project_id = %s",
#     "filestore": "SELECT * FROM filestore WHERE project_id = %s",
#     "label": "SELECT * FROM label WHERE project_id = %s",
#     "project_document": "SELECT * FROM project_document WHERE project_id = %s",
#     "project_description": "SELECT * FROM project_description WHERE project_id = %s",
#     "project_member": "SELECT * FROM project_member WHERE project_id = %s",
#     "project_source": "SELECT * FROM project_source WHERE project_id = %s",
# }

# indirect_exports = {
#     "annotation": """
#         SELECT annotation.* 
#         FROM annotation
#         JOIN article ON annotation.article_id = article.article_id
#         WHERE article.project_id = %s
#     """,
#     "article_label": """
#         SELECT article_label.* 
#         FROM article_label
#         JOIN article ON article_label.article_id = article.article_id
#         WHERE article.project_id = %s
#     """,
#     "article_note": """
#         SELECT article_note.* 
#         FROM article_note
#         JOIN article ON article_note.article_id = article.article_id
#         WHERE article.project_id = %s
#     """,
#     "article_pdf": """
#         SELECT article_pdf.* 
#         FROM article_pdf
#         JOIN article ON article_pdf.article_id = article.article_id
#         WHERE article.project_id = %s
#     """,
#     "article_data": """
#         SELECT article_data.* 
#         FROM article_data
#         JOIN article ON article_data.article_data_id = article.article_data_id
#         WHERE article.project_id = %s
#     """,
#     "article_source": """
#         SELECT article_source.* 
#         FROM article_source
#         JOIN article ON article_source.article_id = article.article_id
#         WHERE article.project_id = %s
#     """,
#     "s3store": """
#         SELECT s3store.* 
#         FROM s3store
#         JOIN article_pdf ON s3store.s3_id = article_pdf.s3_id
#         JOIN article ON article_pdf.article_id = article.article_id
#         WHERE article.project_id = %s
#     """
# }

# def convert_datetime(val):
#     if isinstance(val, datetime.datetime):
#         return val.isoformat()
#     return val

# def convert_jsonb(data):
#     if isinstance(data, dict):
#         return json.dumps(data)
#     return data

# exports = list({**direct_exports, **indirect_exports}.items())


# # Fetch and insert data for indirect tables
# for table, pg_query in exports:
#     print(table)
#     pg_cursor.execute(pg_query, (project_id,))
#     columns = [desc[0] for desc in pg_cursor.description]
#     rows = pg_cursor.fetchall()
    
#     if len(rows) == 0:
#         continue
    
#     rows = [
#         tuple(convert_datetime(convert_jsonb(val)) for val in row)
#         for row in rows
#     ]
    
#     placeholders = ", ".join(["?" for _ in columns])
#     sqlite_cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})")
#     sqlite_cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
#     sqlite_conn.commit()


# # Commit the transaction and close connections
# pg_conn.close()
# sqlite_conn.close()
