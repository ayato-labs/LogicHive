import json


def log_json(data):
    print(json.dumps({"log": data}))
