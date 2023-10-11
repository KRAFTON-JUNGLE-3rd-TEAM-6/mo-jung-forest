from flask import Flask
from pymongo import MongoClient
import json
from flask.json.provider import JSONProvider

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.dbjungle    # DB 이름 변경

###
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)


app.json = CustomJSONProvider(app)
###

@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
