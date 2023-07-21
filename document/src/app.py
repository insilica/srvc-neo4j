from collections import defaultdict
from flask import Flask, request, render_template, render_template_string, redirect, url_for, send_file
from jsonlines.jsonlines import InvalidLineError
from werkzeug.utils import secure_filename
from py2neo import Graph, Node, Relationship
from json2html import json2html
from py2neo.bulk import merge_nodes
from uuid import uuid4
import json, jsonlines, jwt, os, uuid

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = '/app/data/pdf-upload'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_current_email():
    auth_token = request.cookies.get('token')
    if not auth_token:
      raise Exception('Invalid token. Please log in again.')

    try:
        payload = jwt.decode(auth_token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        user_email = payload.get('email')
        if not user_email:
            raise Exception('No email in the token')
        return user_email

    except jwt.ExpiredSignatureError:
        raise Exception('Signature expired. Please log in again.')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token. Please log in again.')

def get_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']

def get_project_visibility(tx):
    result = tx.run("MATCH (n:Setting {group: $group, key: $k}) RETURN n", group='Project', k='visibility')
    records = result.data()
    if records:
      return records[0]['n']

template = "{{doc.content}}"

def parse_content(d):
    if d['content_type'] == 'json':
            d['content'] = json.loads(d['content'])
    return d

@app.route('/')
def list_documents():
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    visibility = get_project_visibility(graph)

    if not visibility or visibility['value'] != 'public':
        try:
            email = get_current_email()
        except:
            return redirect('/login'), 303
        user = get_user(graph, email)
        if not (user and user.get('isMember')):
            return 'Forbidden', 403

    q = "MATCH (o:Document) return o"
    documents = [dict(x['o']) for x in graph.run(q).data()]
    documents = [parse_content(d) for d in documents]

    for d in documents:
        d['html'] = json2html.convert(d['content'])
        d['rendered_content'] = render_template_string(template, doc=d)

    return render_template('documents.html', documents=documents)

@app.template_filter('split')
def split_filter(s, delimiter=None):
    return s.split(delimiter)

@app.route('/<string:doc_id>')
def view_document(doc_id):
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    visibility = get_project_visibility(graph)

    if not visibility or visibility['value'] != 'public':
        try:
            email = get_current_email()
        except:
            return redirect('/login'), 303
        user = get_user(graph, email)
        if not (user and user.get('isMember')):
            return 'Forbidden', 403

    q = """
    MATCH (o:Document {id: $id})
    OPTIONAL MATCH (a:Attachment)-[r:HAS_DOCUMENT]->(o)
    RETURN o, collect(a) as attachments
    """
    result = graph.run(q, id=doc_id).data()
    if not result:
      return 'Not Found', 404
    d = dict(result[0]['o'])
    attachments = [dict(a) for a in result[0]['attachments']]
    pdfs = [item for item in attachments if item.get('media_type') == 'application/pdf']

    d['html'] = json2html.convert(d['content'])
    d['rendered_content'] = render_template_string(template, doc=d)

    q = "MATCH (n:Label) RETURN n"
    labels = [dict(x)['n'] for x in graph.run(q).data()]

    q = """
    MATCH (d:Document {id: $id})<-[:HAS_DOCUMENT]-(a:Answer)-[:HAS_USER]->(u:User),
          (a)-[:HAS_LABEL]->(l:Label)
    RETURN u.email AS user_email, l.id AS label_id, a AS answer
    """
    results = graph.run(q, id=doc_id).data()
    data = defaultdict(lambda: defaultdict(dict))
    for result in results:
        user_email = result["user_email"]
        answer = result["answer"]
        label_id = result['label_id']
        data[user_email][label_id] = json2html.convert(answer['answer'])

    return render_template('document.html', document=d, labels=labels, data=data, document_path=os.getenv('DOCUMENT_PATH'), pdfs=pdfs)

def add_attachment(graph, doc_id, file_path, media_type):
    tx = graph.begin()
    attachment_node = Node("Attachment", id=str(uuid4()), file_path=file_path, media_type=media_type)
    tx.create(attachment_node)
    document_node = graph.nodes.match("Document", id=doc_id).first()

    if document_node is None:
        raise f"No Document found with id {doc_id}"

    rel = Relationship(attachment_node, "HAS_DOCUMENT", document_node)
    tx.create(rel)
    graph.commit(tx)

@app.route('/pdf-upload', methods=['POST'])
def pdf_upload():
    try:
        email = get_current_email()
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isMember')):
        return 'Forbidden', 403

    if request.files.get('pdfUpload'):
        doc_id = request.form['docId']
        f = request.files['pdfUpload']
        filename = str(uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(file_path)

        add_attachment(graph, doc_id, file_path, 'application/pdf')

        return redirect(doc_id)

@app.route('/file/<file_id>', methods=['GET'])
def serve_file(file_id):
    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    q = """
    MATCH (a:Attachment {id: $id})
    RETURN a.file_path as file_path, a.media_type as media_type
    """
    result = graph.run(q, id=file_id).data()

    if not result:
        return 'File not found', 404

    file_path = result[0]['file_path']
    media_type = result[0]['media_type']

    # Use the send_file function to send the file
    return send_file(file_path, mimetype=media_type)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Ensure the server is accessible externally
