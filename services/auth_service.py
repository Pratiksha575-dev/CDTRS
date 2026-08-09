USERS = {
    "master": {
        "password": "1234",
        "role": "Master"
    },

    "director": {
        "password": "1234",
        "role": "Director"
    },

    "hod": {
        "password": "1234",
        "role": "HOD"
    },

    "hodpa": {
        "password": "1234",
        "role": "HOD PA"
    },

    "employee": {
        "password": "1234",
        "role": "Employee"
    },

    "admin": {
        "password": "1234",
        "role": "Administrator"
    },

    "viewer": {
        "password": "1234",
        "role": "Read-only User"
    }
}


def authenticate(username, password):

    user = USERS.get(username)

    if user and user["password"] == password:
        return {
            "username": username,
            "role": user["role"]
        }

    return None