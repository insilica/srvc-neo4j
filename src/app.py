from flask import Flask, request, render_template
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
import json, jsonlines, os, uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/app/upload'  # Set to a valid path

def create_node(graph, data, parent=None, relationship_name=None):
    if isinstance(data, dict):
        node = Node('Object', id=str(uuid.uuid4()), json_data=json.dumps(data), type=data.get('type'), uri=data.get('uri'))
        graph.create(node)

        if parent is not None:
            relationship = Relationship(parent, relationship_name, node)
            graph.create(relationship)

        for k, v in data.items():
            if isinstance(v, (dict, list)):
                create_node(graph, v, parent=node, relationship_name=k)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            create_node(graph, item, parent=parent, relationship_name=f"{relationship_name}_{i}")

def upload_to_neo4j(file_path, graph):
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()  # remove leading/trailing whitespace
            if line:  # skip blank lines
                try:
                    data = json.loads(line)  # try to parse line as JSON
                    create_node(graph, data)
                except json.JSONDecodeError:
                    print(f"Skipped invalid JSON line: {line}")
                    continue

@app.route('/upload')
def upload_form():
    return render_template('upload.html')

# Excruciatingly slow
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

@app.route('/documents')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    documents = graph.run("""
    MATCH (o:Object {type: "document"})
    RETURN o.uri AS uri, o.json_data AS json_data
    """).data()

    for document in documents:
        document['json_data'] = json.loads(document['json_data'])

    return render_template('documents.html', documents=documents)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
