# import for flask app
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, make_response
from jwt import ExpiredSignatureError
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask.json.provider import JSONProvider
import json
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, decode_token, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_access_cookies, unset_jwt_cookies, unset_refresh_cookies

# import for environment variables
from dotenv import load_dotenv
import pytz
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

#jwt config
app.config["JWT_SECRET_KEY"] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
jwt = JWTManager(app)


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
def home():
    return render_template('login.html')

@app.route('/main')
def main():
    return render_template('index.html')


# 로그인
@app.route("/users/login", methods=['POST'])
def login():
    requests = request.get_json()
    input_user_id = requests.get("userId")
    input_password = requests.get("password")

    try:
        user_info = db.User.find_one({ "userId": input_user_id, "status": "active" })
    except:
        return jsonify({"result": "fail", "data": "유저 찾기에 실패했습니다. 다시 시도해주세요."})

    if user_info is None:
        return jsonify({"result": "fail", "data": "아이디가 틀렸거나, 존재하지 않는 유저입니다."})
    
    id = str(user_info['_id'])
    name = user_info['name']
    password = user_info['password']

    # 로그인 확인 
    if password != input_password:
        return jsonify({"result": "fail", "data": "비밀번호가 틀렸습니다."})

    # 로그인 성공, 토큰 발급
    access_token = create_access_token(identity=id, additional_claims={"id": id, "name": name})
    refresh_token = create_refresh_token(identity=id)

    response = jsonify({"result": "success", "data": {
        "access_token": access_token, 
        "refresh_token": refresh_token
    }})
    set_access_cookies(response, access_token) 
    set_refresh_cookies(response, refresh_token)

    response.set_cookie('id', id)
    response.set_cookie('name', name)

    return response


@app.route("/auth/check", methods=['GET'])
def check_login_first():
    access_token = request.cookies.get('access_token_cookie')
    refresh_token = request.cookies.get('refresh_token_cookie')

    if access_token is None or refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})

    return validate_token(access_token, refresh_token)


# access token 재발급
@app.route("/auth/refresh", methods=['GET'])
def refresh_access_token():
    refresh_token = request.cookies.get('refresh_token_cookie')

    if refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})
    
    id = request.cookies.get('id')
    name = request.cookies.get('name')

    access_token = create_access_token(identity=id, additional_claims={"id": id, "name": name})
    response = jsonify({"result": "success", "data": {
        "access_token": access_token
    }})
    set_access_cookies(response, access_token)

    return response


# 로그아웃
@app.route("/users/logout", methods=['GET'])
def logout():

    response = jsonify({"result": "success", "data": "로그아웃 되었습니다."})
    unset_jwt_cookies(response)
    response.delete_cookie('id')
    response.delete_cookie('name')

    return response


# 회원가입
@app.route("/users/register", methods=['POST'])
def register():
    requests = request.get_json()
    input_user_id = requests.get("userId")
    input_password = requests.get("password")
    input_name = requests.get("name")

    kst = pytz.timezone('Asia/Seoul')
    created_at = datetime.now(kst)
    
    try:
        db.User.insert_one({
            "userId": input_user_id,
            "password": input_password,
            "name": input_name,
            "status": "active",
            "createdAt": created_at,
        })
        return jsonify({"result": "success", "data": "회원가입이 완료되었습니다."})
    except:
        return jsonify({"result": "fail", "data": "회원가입 시도에 실패하였습니다. 다시 시도해주세요."})


# 아이디 중복 체크
@app.route("/users/check-id", methods=['POST'])
def check_id():
    
    requests = request.get_json()
    input_user_id = requests.get("userId")

    try: 
        user_info = db.User.find_one({ "userId": input_user_id, "status": "active" })
    except:
        return jsonify({"result": "fail", "data": "아이디 체크에 실패하였습니다. 다시 시도해주세요."})

    if user_info is None:
        return jsonify({"result": "success", "data": "사용 가능한 아이디입니다."})
    else:
        return jsonify({"result": "dsuccess", "data": "이미 존재하는 아이디입니다."})


# 메세지 생성 기능
@app.route('/messages', methods=['POST'])
def post_message():
    access_token = request.cookies.get('access_token_cookie')
    refresh_token = request.cookies.get('refresh_token_cookie')
    
    if access_token is None or refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})

    post_data = request.get_json()
    if not post_data or not post_data.get('recipient') or not post_data.get('content'):
        return make_response(jsonify({
            'result': 'fail'
        }), 400)
    
    generatorId = request.cookies.get('id')

    kst = pytz.timezone('Asia/Seoul')
    created_at = datetime.now(kst)

    try:
        db.Message.insert_one({
            "generatorId": generatorId,
            "recipient": post_data.get('recipient'),
            "content": post_data.get('content'),
            "createdAt": created_at
        })
        inserted_one = db.Message.find_one({"generatorId": generatorId, "createdAt": created_at})
        db.BoardIndex.insert_one({
            "postId": str(inserted_one['_id']),
            "type": "MESSAGE",
            "createdAt": created_at
        })
        return make_response(jsonify({
            'result': 'success'
        }), 200)
    except:
        return make_response(jsonify({
            'result': 'fail'
        }), 400)
    

# 투표 생성 기능
@app.route('/votes', methods=['POST'])
def post_vote():
    access_token = request.cookies.get('access_token_cookie')
    refresh_token = request.cookies.get('refresh_token_cookie')
    
    if access_token is None or refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})

    post_data = request.get_json()
    if not post_data or not post_data.get('title') or not post_data.get('option'):
        return make_response(jsonify({
            'result': 'fail'
        }), 400)
    
    generatorId = request.cookies.get('id')

    kst = pytz.timezone('Asia/Seoul')
    created_at = datetime.now(kst)

    try:
        db.Vote.insert_one({
            "generatorId": generatorId,
            "title": post_data.get('title'),
            "option": post_data.get('option'),
            "createdAt": created_at
        })
        inserted_one = db.Vote.find_one({"generatorId": generatorId, "createdAt": created_at})
        db.BoardIndex.insert_one({
            "postId": str(inserted_one['_id']),
            "type": "VOTE",
            "createdAt": created_at
        })
        return make_response(jsonify({
            'result': 'success'
        }), 200)
    except:
        return make_response(jsonify({
            'result': 'fail'
        }), 400)

# 유저별 투표 기능
@app.route('/votes/<voteId>/options/<optionId>', methods=['POST'])
def do_vote(voteId, optionId):
    access_token = request.cookies.get('access_token_cookie')
    refresh_token = request.cookies.get('refresh_token_cookie')
    
    if access_token is None or refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})

    voterId = request.cookies.get('id')

    existingVote = db.UserVote.find_one({
        "voterId": voterId,
        "voteId": voteId
    })
    if existingVote:
        # 투표 결과를 바꾸고 싶을 경우 구현
        return jsonify({
            'result': 'fail',
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

# 메인 게시판 GET
@app.route('/mainBoard', methods=['GET'])
def show_main():
    # 변수 할당
    from typing import Final
    POST_PER_PAGE: Final = 4
    requestedPage = int(request.args.get('page'))

    # 전체 게시글 수 조회
    totalPostNum = db.BoardIndex.count_documents(filter={})
    if not totalPostNum:
        return make_response(jsonify({
            'result': 'fail',
            'message': 'No post in the database.'
        }), 204)
    
    # 최신 게시글 조회
    pagedPosts = list(db.BoardIndex.find().sort([('createdAt', -1)]).skip((requestedPage - 1) * POST_PER_PAGE).limit(POST_PER_PAGE))
    if not pagedPosts:
        return make_response(jsonify({
            'result': 'fail',
            'message': 'No posts found for the page.'
        }), 404)
    
    objList = []
    for board in pagedPosts:
        print(board)
        # 게시글이 메세지인 경우
        if board['type'] == 'MESSAGE':
            message = db.Message.find_one({"_id" : ObjectId(board['postId'])})
            messageObj = {
                "mode" : "MESSAGE",
                "recipient": message['recipient'],
			    "content": message['content'],
            }
            objList.append(messageObj)
        # 게시글이 투표인 경우
        elif board['type'] == 'VOTE':
            vote = db.Vote.find_one({"_id" : ObjectId(board['postId'])})
            currentUserVote = db.UserVote.find_one({
                "voterId": request.cookies.get('id'),
                "voteId": str(vote['_id'])
            })
            from collections import defaultdict
            key_counts = defaultdict(int)
            polls = db.UserVote.find({"voteId": str(vote['_id'])})
            for poll in polls:
                key_counts[poll['optionId']] += 1
            voteObj = {
                "mode": "VOTE",
                "title": vote['title'],
                "options": vote['option'],
                "optionProportions": [{key: value} for key, value in key_counts.items()]
            }
            if currentUserVote:
                voteObj['selectedOptionId'] = currentUserVote['optionId']

            objList.append(voteObj)

    return make_response(jsonify({
        'result': 'success',
        'data': objList
    }), 200)


#############################################################################
############################### util 함수 ###################################
#############################################################################


# 로그인이 필요한 api에서 사용하여 토큰이 유효한지 확인하는 함수
def validate_token(access_token, refresh_token):
    if access_token is None or refresh_token is None:
        return jsonify({"result": "fail", "data": "로그인이 필요합니다."})
    
    try:
        decode_token(access_token).get(app.config["JWT_SECRET_KEY"], None)
        
        # print("access token is valid")
    except ExpiredSignatureError: 
        return jsonify({"result": "afail", "data": "로그인 유지 시간이 만료되었습니다. 연장하시겠습니까?"})
    try:
        decode_token(refresh_token).get(app.config["JWT_SECRET_KEY"], None)
    except ExpiredSignatureError: 
        return jsonify({"result": "rfail", "data": "마지막 로그인으로부터 30일이 지났습니다. 다시 로그인해주세요."})


    return jsonify({"result": "success", "data": "로그인이 유효합니다."})


if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
