import pytest, os
from src.app import app as flask_app

# Test client fixture
@pytest.fixture
def app():
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

# Tests
def test_upload_file(client):
    data = {
        'file': (open('test/test.jsonl', 'rb'), 'test.jsonl')
    }
    response = client.post('/uploader', data=data, content_type='multipart/form-data')
    assert response.status_code == 200

def test_get_sources(client):
    response = client.get('/sources')
    assert response.status_code == 200
