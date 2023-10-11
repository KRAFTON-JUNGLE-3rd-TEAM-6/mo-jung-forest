# import for flask app
from datetime import timedelta
from flask import Flask, render_template, jsonify, request
from jwt import ExpiredSignatureError
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask.json.provider import JSONProvider
import json
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, decode_token, get_jwt_identity, set_access_cookies, set_refresh_cookies

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
def hello_world():
    return 'Hello World!'

@app.route("/users/login", methods=['POST'])
def login():
    requests = request.get_json()
    input_user_id = requests.get("userId")
    input_password = requests.get("password")

    user_info = db.User.find_one({ "userId": input_user_id })

    if user_info is None:
        return jsonify({"result": "fail", "data": "존재하지 않는 유저입니다."})
    
    id = str(user_info['_id'])
    name = user_info['name']
    password = user_info['password']

    # 로그인 확인 
    if password != input_password:
        return jsonify({"result": "fail", "data": "비밀번호가 틀렸습니다."})

    # 로그인 성공, 토큰 발급
    access_token = create_access_token(identity=id, additional_claims={"id": id, "name": name})
    refresh_token = create_refresh_token(identity=id)

    validate_token(access_token)

    response = jsonify({"access_token": access_token, "refresh_token": refresh_token})
    set_access_cookies(response, access_token) 
    set_refresh_cookies(response, refresh_token)

    response.set_cookie('id', id)
    response.set_cookie('name', name)

    return response


#############################################################################
############################### util 함수 ###################################
#############################################################################


def validate_token(access_token):
    try:
        decode_token(access_token).get(app.config["JWT_SECRET_KEY"], None)
    except ExpiredSignatureError: 
        return render_template('login.html')


if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
