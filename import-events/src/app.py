from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask import send_from_directory
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, re, requests, uuid

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/tmp/srvc-upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_node_by_hash(tx, hash):
    result = tx.run("MATCH (n {hash: $hash}) RETURN n", hash=hash)
    records = result.data()
    return records[0]['n'] if records else None

def get_or_create_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']
    else:
      return Node('User', id=str(uuid4()), email=email)

def create_document(data, filename):
    document = Node('Document', id=str(uuid4()), content=json.dumps(data), content_type='json', hash=data.get('hash'))
    document_source = Node('DocumentSource', name=filename)
    rel = Relationship(document_source, 'SOURCE_OF', document)
    return document, document_source, rel

def create_label(data, filename):
    ldata = data.get('data')
    return Node('Label', id=str(uuid4()), content=json.dumps(data), content_type='json', hash=data.get('hash'), name=ldata.get('id'), description=ldata.get('question'), type=ldata.get('type'))

def create_answer(tx, data, filename):
    adata = data.get('data')
    answer = Node('Answer', id=str(uuid4()), answer=json.dumps(adata.get('answer')), content=json.dumps(adata), content_type='json', hash=data.get('hash'))
    doc_rel = Relationship(answer, 'HAS_DOCUMENT', get_node_by_hash(tx, adata.get('event', adata.get('document'))))
    lbl_rel = Relationship(answer, 'HAS_LABEL', get_node_by_hash(tx, adata.get('label')))
    match = re.search(r'mailto:(\S+)', adata.get('reviewer'))
    email = match.group(1) if match else None
    user = get_or_create_user(tx, email)
    user_rel = Relationship(answer, 'HAS_USER', user)
    return answer, doc_rel, lbl_rel, user, user_rel

def upload_to_neo4j(file_path, filename, graph):
    with open(file_path, 'r') as f:
        answers = []
        documents = []
        document_sources = []
        labels = []
        rels = []
        for line in f:
            line = line.strip()  # remove leading/trailing whitespace
            if line:  # skip blank lines
                try:
                    data = json.loads(line) # try to parse line as JSON
                    if data['type'] == 'document':
                        document, document_source, rel = create_document(data, filename)
                        documents.append(document)
                        document_sources.append(document_source)
                        rels.append(rel)
                    elif data['type'] == 'label':
                        labels.append(create_label(data, filename))
                    elif data['type'] == 'label-answer':
                        answers.append(data)

                except json.JSONDecodeError:
                    print(f"Skipped invalid JSON line: {line}")
                    continue

        tx = graph.begin()
        for document, document_source, rel in zip(documents, document_sources, rels):
            tx.merge(document_source, "DocumentSource", "name")
            tx.merge(document, "Document", "id")
            tx.create(rel)
        for label in labels:
            tx.merge(label, 'Label', 'id')
        for data in answers:
            answer, doc_rel, lbl_rel, user, user_rel = create_answer(tx, data, filename)
            tx.merge(answer, 'Answer', 'id')
            tx.create(doc_rel)
            tx.create(lbl_rel)
            tx.merge(user, 'User', 'email')
            tx.create(user_rel)
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
