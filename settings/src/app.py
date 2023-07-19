from flask import Flask, request, render_template, redirect, url_for, jsonify
from py2neo import Graph, Node, NodeMatcher
from uuid import uuid4
import json, jwt, os

app = Flask(__name__)

settings_group = [
    {'name': 'Project', 'settings': ['visibility']},
    {'name': 'Review', 'settings': ['review_priority', 'unlimited_reviewers']},
    {'name': 'Access', 'settings' : ['invite_link']}
]

default_settings = [
    {'key': 'visibility', 'value': 'public', 'options': ['public', 'private'], 'enabled': False},
    {'key': 'review_priority', 'value': 'public', 'options': ['public', 'private'], 'enabled': False},
    {'key': 'unlimited_reviewers', 'value': 'No', 'options': ['Yes', 'No']},
    {'key': 'invite_link', 'value': None, 'options': None, 'enabled': False}
]

def get_current_email(request):
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

@app.before_first_request
def create_settings():
    try:
        email = get_current_email(request)
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))
    tx = graph.begin()

    user = get_user(tx, email)
    if not (user and user.get('isAdmin') or user.get('isOwner')):
        return 'Forbidden', 403

    matcher = NodeMatcher(graph)
    for group in settings_group:
        for setting_key in group['settings']:
            setting = next((item for item in default_settings if item['key'] == setting_key), None)
            if setting:
                if matcher.match("Setting", key=setting_key).first() is None:
                    setting_node = Node(
                        "Setting",
                        key=setting_key,
                        value=setting.get('value'),
                        options=json.dumps(setting.get('options')),
                        enabled=setting.get('enabled'),
                        group=group.get('name')
                    )
                    tx.create(setting_node)
    tx.commit()

@app.route('/', methods=['GET', 'POST'])
def settings():
    try:
        email = get_current_email(request)
    except:
        return redirect('/login'), 303

    graph = Graph("bolt://neo4j:7687", auth=("neo4j", "test1234"))

    user = get_user(graph, email)
    if not (user and user.get('isAdmin') or user.get('isOwner')):
        return 'Forbidden', 403

    if request.method == 'POST':
        key = request.form.get('key')
        value = request.form.get('value')
        tx = graph.begin()
        tx.run("MERGE (setting:Setting {key: $key, value: $value})", key=key, value=value)
        tx.commit()
        return redirect(url_for('settings'))

    settings = graph.run("MATCH (setting:Setting) RETURN setting.key AS key, setting.value AS value, setting.options AS options, setting.enabled AS enabled, setting.group AS group").data()
    return render_template('settings.html', settings=settings, settings_group=settings_group)

@app.route('/generate_invite_link', methods=['GET'])
def generate_invite_link():
    invite_id = str(uuid4())
    return jsonify({'invite_link': invite_id})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
