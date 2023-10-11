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

# 메세지 생성 기능
@app.route('/messages', methods=['POST'])
def post_message():
    post_data = request.get_json()
    if not post_data:
        return jsonify({
            'result': 'fail'
        })
    
    generatorId = request.cookies.get('userId')     # 구현 예정
    if not generatorId:
        return jsonify({
            'result': 'fail',
            'message': '로그인이 필요합니다.'
        })
    
    try:
        db.Message.insert_one({
            "generatorId": generatorId,
            "recipient": post_data.get('recipient'),
            "content": post_data.get('content'),
            "createdAt": post_data.get('createdAt')
        })
        return jsonify({
            'result': 'success'
        })
    except:
        return jsonify({
            'result': 'fail'
        })
    
# 투표 생성 기능
@app.route('/votes', methods=['POST'])
def post_vote():
    post_data = request.get_json()
    if not post_data:
        return jsonify({
            'result': 'fail'
        })
    
    generatorId = request.cookies.get('userId')     # 구현 예정
    if not generatorId:
        return jsonify({
            'result': 'fail',
            'message': '로그인이 필요합니다.'
        })

    try:
        db.Vote.insert_one({
            "generatorId": generatorId,
            "title": post_data.get('title'),
            "option1": post_data.get('option1'),
            "option2": post_data.get('option2'),
            "option3": post_data.get('option3'),
            "option4": post_data.get('option4'),
            "option5": post_data.get('option5'),
            "createdAt": post_data.get('createdAt')
        })
        return jsonify({
            'result': 'success'
        })
    except:
        return jsonify({
            'result': 'fail'
        })

# 유저별 투표 기능
@app.route('/votes/<voteId>/options/<optionId>', methods=['POST'])
def do_vote(voteId, optionId):
    voterId = request.cookies.get('userId')     # 구현 예정
    if not voterId:
        return jsonify({
            'result': 'fail',
            'message': '로그인이 필요합니다.'
        })

    existingVote = db.UserVote.find_one({
        "voterId": voterId,
        "voteId": voteId
    })
    if existingVote:
        # 투표 결과를 바꾸고 싶을 경우 구현
        return jsonify({
            'result': 'success',
            'message': '이미 투표하셨습니다.'
        })

    try:
        db.UserVote.insert_one({
            "voterId": voterId,
            "voteId": voteId,
            "optionId": optionId,
        })
        return jsonify({
            'result': 'success'
        })
    except:
        return jsonify({
            'result': 'fail'
        })


if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
