from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, Response, flash, make_response
from py2neo import Graph, Node, Relationship
from requests.exceptions import RequestException
from threading import Lock
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
import json
import jwt
import os
import shutil
import yaml
import random
import requests
import secrets
import subprocess
import time

load_dotenv()

def copy_base_files(project_path):
    os.makedirs(project_path, exist_ok=True)
    shutil.copy('base-docker-compose.yml', os.path.join(project_path, 'docker-compose.yml'))
    shutil.copy('base-.env', os.path.join(project_path, '.env'))

def update_env_file(project_path, web_port):
    env_path = os.path.join(project_path, '.env')
    secret_key = os.getenv('SECRET_KEY')

    with open(env_path, 'a') as env_file:
        env_file.write(f'SECRET_KEY={secret_key}\n')
        env_file.write(f'WEB_PORT={web_port}\n')

def get_existing_ports(base_path):
    # List all .env files in the base directory
    env_files = [os.path.join(root, file)
                 for root, dirs, files in os.walk(base_path)
                 for file in files if file == '.env']

    # Extract the WEB_PORT from each .env file
    ports = []
    for env_file in env_files:
        with open(env_file, 'r') as file:
            for line in file:
                if line.startswith('WEB_PORT='):
                    port = int(line.replace('WEB_PORT=', '').strip())
                    ports.append(port)

    return ports

def get_unique_port(existing_ports):
    while True:
        port = random.randint(6000, 10000)
        if port not in existing_ports:
            return port

def generate_docker_compose(user_name, project_name):
    base_path = os.path.join('..', 'projects')
    project_path = os.path.join(base_path, user_name, project_name)

    existing_ports = get_existing_ports(base_path)
    web_port = get_unique_port(existing_ports)
    copy_base_files(project_path)
    update_env_file(project_path, web_port)
    run_docker_compose(project_path)

# Work-around for https://github.com/docker/compose/issues/6532
lock_dict = {'__root__': Lock()}

def run_docker_compose(path):
    with lock_dict['__root__']:
      if path not in lock_dict:
          lock_dict[path] = Lock()

    with lock_dict[path]:
        subprocess.run(["docker", "compose", "-f", os.path.join(path, "docker-compose.yml"), "up", "-d"])

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

def get_user(tx, email):
    result = tx.run("MATCH (n:User {email: $email}) RETURN n", email=email)
    records = result.data()
    if records:
      return records[0]['n']

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        graph = Graph("bolt://localhost:5001", auth=("neo4j", "test1234"))
        tx = graph.begin()
        user = get_user(tx, email)
        graph.commit(tx)

        if user and check_password_hash(user['password_hash'], password):
            # User ID is encoded into the token here
            token = jwt.encode({'user_id': user['id']}, app.config['SECRET_KEY'], algorithm='HS256')

            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('token', token)  # Set the JWT as a cookie

            return resp

        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        graph = Graph("bolt://localhost:5001", auth=("neo4j", "test1234"))
        tx = graph.begin()
        user = get_user(tx, email)

        if user:
            flash('User already exists.')
            return redirect(url_for('register'))

        user = Node('User', id=str(uuid4()), email=email, password_hash=generate_password_hash(request.form.get('password')))
        tx.merge(user, 'User', 'email')
        graph.commit(tx)

        flash('Registered successfully.')
        token = jwt.encode({'user_id': user['id']}, app.config['SECRET_KEY'], algorithm='HS256')

        resp = make_response(redirect(url_for('home')))
        resp.set_cookie('token', token)  # Set the JWT as a cookie

        return resp
    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_name = request.form['user_name']
        project_name = request.form['project_name']
        generate_docker_compose(user_name, project_name)
        return redirect(url_for('home'))

    base_path = os.path.join('..', 'projects')
    projects = [os.path.join(root, dir).replace(base_path + os.sep, '')
                for root, dirs, files in os.walk(base_path)
                for dir in dirs if 'docker-compose.yml' in os.listdir(os.path.join(root, dir))]
    projects.sort()

    return render_template('home.html', projects=projects)

def get_project_port(user, project):
    base_path = os.path.join('..', 'projects')
    project_path = os.path.join(base_path, user, project)
    env_path = os.path.join(project_path, '.env')

    with open(env_path, 'r') as file:
        for line in file:
            if line.startswith('WEB_PORT='):
                return int(line.replace('WEB_PORT=', '').strip())

    return None

@app.route('/<string:user>/<string:project>/', defaults={'subpath': None}, methods=['GET', 'POST', 'HEAD'])
@app.route('/<string:user>/<string:project>/<path:subpath>', methods=['GET', 'POST', 'HEAD'])
def project_service(user, project, subpath):
    base_path = os.path.join('..', 'projects')
    project_path = os.path.join(base_path, user, project)

    port = get_project_port(user, project)
    if port is None:
        return "Project not found", 404

    if subpath:
        url = f"http://localhost:{port}/{subpath}"
    else:
        url = f"http://localhost:{port}/"

    max_retries = 5
    for i in range(max_retries):
        try:
            if request.method == 'POST':
                files = {name: (file.filename, file.stream.read(), file.content_type) for name, file in request.files.items()}
                json_data = request.get_json(silent=True)
                if json_data is not None:
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(url, data=json.dumps(json_data).encode(), headers=headers)
                elif files:
                    response = requests.post(url, data=request.form, files=files)
                else:
                    response = requests.post(url, data=request.form)
            elif request.method == 'HEAD':
                response = requests.head(url)
            else:  # GET request
                response = requests.get(url, params=request.args)
            break  # If the request is successful, break out of the loop
        except RequestException:
            if i < max_retries - 1:  # No need to retry for the last time
                run_docker_compose(project_path)
                time.sleep(5 * (i + 1))  # Wait for a longer time after each retry
            else:
                return "Service is not available. Please try again later.", 503

    return Response(response.content, mimetype=response.headers.get('content-type'), headers={'Accept': response.headers.get('Accept')})

run_docker_compose('docker')

if __name__ == '__main__':
    app.run(debug=True)
