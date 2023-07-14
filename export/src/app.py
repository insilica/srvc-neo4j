from flask import Flask, request, render_template, render_template_string, redirect, Response
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
from io import StringIO
import csv, json, jsonlines, os, uuid

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('export.html', export_path=os.getenv('EXPORT_PATH'))

@app.route('/articles')
def export_articles():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document) return o"
    documents = [dict(x['o']) for x in graph.run(q).data()]

    # Create an in-memory text stream
    si = StringIO()
    writer = csv.writer(si)

    content_keys = set(key for doc in documents for key in json.loads(doc['content']).keys())
    column_names = ['id'] + list(content_keys)
    writer.writerow(column_names)

    for doc in documents:
        row = [doc['id']] + [json.loads(doc['content']).get(key, '') for key in content_keys]
        writer.writerow(row)

    response = Response(si.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=articles.csv'
    return response

@app.route('/article-answers')
def export_article_answers():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = """
    MATCH (a:Answer)-[:HAS_DOCUMENT]->(d:Document),
          (a)-[:HAS_LABEL]->(l:Label),
          (a)-[:HAS_USER]->(u:User)
    RETURN a, d.id AS doc_id, l.name AS label_name, u.email as email
    """
    results = [dict(x) for x in graph.run(q).data()]

    # Group answers by document ID
    grouped = {}
    for result in results:
        doc_id = result['doc_id']
        if doc_id not in grouped:
            grouped[doc_id] = {}
        email = result['email']
        if email not in grouped[doc_id]:
            grouped[doc_id][email] = {}
        grouped[doc_id][email][result['label_name']] = json.loads(result['a']['answer'])

    # Create an in-memory text stream
    si = StringIO()
    writer = csv.writer(si)

    column_names = ['Document ID', 'User'] + sorted(set(result['label_name'] for result in results))
    writer.writerow(column_names)

    for doc_id, email_answers in grouped.items():
        for email, answers in email_answers.items():
            row = [doc_id, email] + [answers.get(label_name, '') for label_name in column_names[1:]]
            writer.writerow(row)

    response = Response(si.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=article-answers.csv'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
