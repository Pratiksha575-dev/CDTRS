import requests


BASE_URL = "http://127.0.0.1:8000"


def post(endpoint, data):
    response = requests.post(
        BASE_URL + endpoint,
        json=data,
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def get(endpoint):
    response = requests.get(
        BASE_URL + endpoint,
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def patch(endpoint, data):
    response = requests.patch(
        BASE_URL + endpoint,
        json=data,
        timeout=10
    )

    response.raise_for_status()

    return response.json()