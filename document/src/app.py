from flask import Flask, request, render_template, render_template_string, send_from_directory
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, os, uuid
from flask import jsonify

app = Flask(__name__)

template = "{{doc.content.content}}"

def parse_content(d):
    if d['content_type'] == 'json':
            d['content'] = json.loads(d['content'])
    return d

@app.route('/')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = "MATCH (o:Document) return o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    documents = [parse_content(d) for d in documents]

    for d in documents:
        d['rendered_content'] = render_template_string(template, doc=d)

    return render_template('documents.html', documents=documents)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(".", "static"), filename)

@app.route('/set_render_template', methods=['POST'])
def set_render_setting():
    print(request.get_json())
    data = request.get_json()
    template = data['template']
    json_data = data['json']
    return jsonify({"json":json_data, "html":render_template_string(template, doc=json_data)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
