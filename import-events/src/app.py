from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask import send_from_directory

from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, requests, uuid

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/tmp/srvc-upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def create_nodes(data, filename):
    document = Node('Document', id=str(uuid4()), content=json.dumps(data), content_type='json')
    document_source = Node('DocumentSource', name=filename)
    rel = Relationship(document_source, 'SOURCE_OF', document)
    return document, document_source, rel

def upload_to_neo4j(file_path, filename, graph):
    with open(file_path, 'r') as f:
        documents = []
        document_sources = []
        rels = []
        for line in f:
            line = line.strip()  # remove leading/trailing whitespace
            if line:  # skip blank lines
                try:
                    data = json.loads(line) # try to parse line as JSON
                    document, document_source, rel = create_nodes(data, filename)
                    documents.append(document)
                    document_sources.append(document_source)
                    rels.append(rel)

                except json.JSONDecodeError:
                    print(f"Skipped invalid JSON line: {line}")
                    continue

        tx = graph.begin()
        for document, document_source, rel in zip(documents, document_sources, rels):
            tx.merge(document_source, "DocumentSource", "name")
            tx.merge(document, "Document", "id")
            tx.create(rel)
        graph.commit(tx)

def delete_from_neo4j(source_name, graph):
    # delete source and connected docs
    graph.run("MATCH (s:DocumentSource)-[r:SOURCE_OF]->(d:Document) WHERE s.name = $name DETACH DELETE r, s, d", name=source_name)

    # delete all remaining documents with no relationship to any source
    graph.run("MATCH (d:Document) WHERE NOT (d)<-[:SOURCE_OF]-(:DocumentSource) DETACH DELETE d")

@app.route('/', methods=['GET'])
def home():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    result = graph.run("MATCH (s:DocumentSource)-[:SOURCE_OF]->(d:Document) RETURN s.name as source, count(d) as documents").data()
    return render_template('import-events.html', sources=result, import_events_path=os.getenv("IMPORT_EVENTS_PATH"))

@app.route('/import', methods=['POST'])
def import_events():
    if request.method == 'POST':
        json = request.get_json()
        if json.get('sysrev_id'):
          url = 'https://sysrev.com/web-api/srvc-events?project-id=' + json.get('sysrev_id')
        else:
          url = request.get_json().get('url')
        if url:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                filename = str(uuid.uuid4())
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # Save the file locally
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                # Now process the file
                graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
                upload_to_neo4j(file_path, filename, graph)

                return redirect(url_for('home'))
            else:
                return "Unable to download file from URL", 400
        else:
            return "No URL provided", 400

@app.route('/delete/<source_name>', methods=['POST'])
def delete_source(source_name):
    if request.method == 'POST':
        graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
        delete_from_neo4j(source_name, graph)

        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
