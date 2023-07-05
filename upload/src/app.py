from flask import Flask, request, render_template
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/srvc-upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def create_object(data):
    node = Node('Object', id=str(uuid4()), json_data=json.dumps(data), type=data.get('type'), uri=data.get('uri'))
    return node

def upload_to_neo4j(file_path, graph):
    with open(file_path, 'r') as f:
        nodes = []
        for line in f:
            line = line.strip()  # remove leading/trailing whitespace
            if line:  # skip blank lines
                try:
                    data = json.loads(line) # try to parse line as JSON
                    node = create_object(data)
                    nodes.append(node)

                except json.JSONDecodeError:
                    print(f"Skipped invalid JSON line: {line}")
                    continue

        tx = graph.begin()
        merge_nodes(tx, nodes, merge_key='id')
        # merge_nodes docs are wrong. we still have to call create
        for node in nodes:
          tx.create(node)
        graph.commit(tx)

@app.route('/upload')
def upload_form():
    return render_template('upload.html')

@app.route('/uploader', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        filename = secure_filename(f.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(file_path)

        graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
        upload_to_neo4j(file_path, graph)

        return 'file uploaded successfully'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
