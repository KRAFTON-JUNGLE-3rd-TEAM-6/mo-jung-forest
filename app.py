# import for flask app
from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask.json.provider import JSONProvider
import json

# import for environment variables
from dotenv import load_dotenv
load_dotenv()
import os

# start app and connect to db
app = Flask(__name__)
client = MongoClient('3.34.130.34',     # 배포 시 localhost로 변경
                    27017,
                    username = os.getenv('MONGO_ID'),
                    password = os.getenv('MONGO_PW'),
                    authSource = os.getenv('MONGO_AUTH'))
db = client.mojungforest

# custom (de)serializer for ObjectId
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



@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
