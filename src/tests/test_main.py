from src.tests.utils import client


def test_read_main():
    response = client.get("/test")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["result"] == "success"


def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert b"awesome" in response.content
