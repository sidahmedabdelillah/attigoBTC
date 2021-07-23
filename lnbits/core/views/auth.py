import random
import string
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4
import bcrypt
from quart import (
    jsonify,
    request,
)
from sqlite3 import Binary
from datetime import datetime, timedelta
import jwt
import json
from .send_email import send_mail
from ..crud import get_account
from .. import (
    core_app,
    db,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXP_DELTA_SECONDS,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_ADRESS,
    MAIL_PASSWORD,
    MAIL_USE_TLS,
    MAIL_USE_SSL,
)


API_URI = "/api/v1"


class EasySQL:
    def  __init__(self, conditions: Dict={}, tables: list=[], columns: list=["*"], columns_values: Dict={}, operator: str="AND", clause: str="WHERE") -> None:
        self.conditions = conditions
        self.tables = tables
        self.columns = columns
        self.columns_values = columns_values
        self.operator = operator.upper()
        self.clause = clause.upper()

    def string_formater(self, string):
        if type(string) == str:
            return f"'{str(string)}'"
        else:
            return Binary(string)

    def update(self):
        operator_conditions = f" {self.operator} ".join([f'"{column}"="{value}"' for column, value in self.conditions.items()])
        if_clause = "" if len(self.conditions) < 1 else self.clause
        dynamic_conditions = [if_clause, operator_conditions]
        columns_values = [f"{col} = '{val}'"for col, val in self.columns_values.items()]
        sql_statement = f"""UPDATE {", ".join(self.tables)} SET {", ".join(columns_values)} {" ".join(dynamic_conditions)};"""
        return sql_statement

    def find(self):
        operator_conditions = f" {self.operator} ".join([f'"{column}"="{value}"' for column, value in self.conditions.items()])
        if_clause = "" if len(self.conditions) < 1 else self.clause
        dynamic_conditions = [if_clause, operator_conditions]
        sql_statement = f"""SELECT {", ".join(self.columns)} FROM {", ".join(self.tables)} {" ".join(dynamic_conditions)};"""
        return sql_statement

    def insert(self):
        sql_statement = f"""INSERT INTO {self.tables[0]} ({", ".join([str(col) for col in self.columns_values.keys()])}) VALUES ({", ".join(["?" for val in self.columns_values.values()])});"""

        return sql_statement

class DbUtil:
    def __init__(self, db, tables=None):
        self.db = db
        self.tables = tables
        
    async def update_all(self, columns_values):
        sql = EasySQL(tables=self.tables, columns_values=columns_values)
        sql_statement = sql.update()
        return await self.db.execute(sql_statement)

    async def find_all(self):
        sql = EasySQL(tables=self.tables)
        sql_statement = sql.find()
        return await self.db.fetchall()

    async def update(self, columns_values, conditions={}, operator=""):
        sql = EasySQL(tables=self.tables, columns_values=columns_values, conditions=conditions, operator=operator)
        sql_statement = sql.update()
        return await self.db.execute(sql_statement)

    async def update_blob(self, columns_values, values=(), conditions={}, operator=""):
        sql = EasySQL(tables=self.tables, columns_values=columns_values, conditions=conditions, operator=operator)
        sql_statement = sql.update()
        return await self.db.execute(sql_statement.replace("'", ""), values)
    
    async def find(self, conditions, columns=["*"], operator=""):
        sql = EasySQL(tables=self.tables, conditions=conditions, columns=columns, operator=operator)
        sql_statement = sql.find()
        return await self.db.fetchall(sql_statement)

    async def insert(self, columns_values):
        sql = EasySQL(tables=self.tables, columns_values=columns_values)
        sql_statement = sql.insert()
        values = tuple(columns_values.values())
        return await self.db.execute(sql_statement, values)

    async def find_one(self, conditions={}, columns=["*"], operator=""):
        result = (await self.find(conditions, columns=columns, operator=""))
        if (type(result) == list and len(result) > 0):
            return result[0]
        return None

    async def find_last(self, conditions={}, columns=["*"], operator=""):
        return (await self.find(conditions, columns=columns, operator=""))[-1]

    async def update_one(self, columns_values, conditions={}, operator=""):
        _id = await self.find_one(["id"], conditions)
        return await self.update(columns_values, {"id": _id})
    
    async def find_all_and_count(self):
        result = await self.find_all()
        return len(result)

    async def find_and_count(self, conditions={}, columns=["*"], operator=""):
        result = await self.find(conditions, columns=columns, operator="")
        return len(result)

    def get_db(self):
        return self.db

users = DbUtil(db, ["accounts"])
wallets = DbUtil(db, ["wallets"])

def get_hashed_pw(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

async def register_user(email: str, password: str, api: bool=False) -> bool:
    hashed_pw = get_hashed_pw(password)
    user_id = uuid4().hex
    if await email_exists(email):
        ret_json = {"status": 301, "msg": "User already exists"}
        return jsonify(ret_json)
    
    await users.insert({
            "id": user_id,
            "email": email,
            "password":  hashed_pw,
            "role": "admin"
            })
    new_account = await get_account(user_id=user_id, conn=db)
    assert new_account, "Newly created account couldn't be retrieved"
    if api:
        return user_id
    return new_account


@core_app.route("/api/v1/logout", methods=["GET"])
async def logout() -> Dict[str, Any]:
    data = request.headers['Authorization']
    token = str.replace(str(data), 'Bearer ','')
    await users.update({"token": token}, {"token": ""})
    return jsonify(generate_return_dict(200, "User logged out"))


@core_app.route("/api/v1/change-password", methods=["POST"])
async def change_password() -> Dict[str, Any]:
    data = request.headers['Authorization']
    token = str.replace(str(data), 'Bearer ','')
    new_password = posted_data["password"]
    hashed_pw = get_hashed_pw(new_password)
    await users.update({"password": hashed_pw}, {"token": token})
    return jsonify(generate_return_dict(200, "Updated password successfully!"))


@core_app.route("/api/v1/get-user", methods=["GET"])
async def get_user() -> Dict[str, Any]:
    data = request.headers['Authorization']
    token = str.replace(str(data), 'Bearer ','')
    user = (await users.find_one({"token": token}, ["id"]))
    if not user:
        ret_json = {"status": 301, "msg": "User not found"}
        return jsonify(ret_json)
    wallet = (await wallets.find_one({"user": user.id}, ["name"]))
    if not wallet:
        ret_json = {"status": 301, "msg": "Wallet not found"}
        return jsonify(ret_json)
    ret_json = {"status": 200, "msg": "Successfully retrieved user id and wallet name", "data": {"id": user.id, "walletName": wallet.name}}
    return jsonify(ret_json)


@core_app.route("/api/v1/sign-up", methods=["POST"])
async def sign_up() -> Dict[str, Any]:
    posted_data = await request.get_json()
    try:
        email = posted_data["email"]
        password = posted_data["password"]
    except KeyError:
        ret_json = {"status": 301, "msg": "Data incomplete"}
        return jsonify(ret_json)
    if not await email_exists(email):
        return jsonify(generate_return_dict(301, "Email doesn't exist"))

    hashed_pw = get_hashed_pw(password)

    user_id = await register_user(email, password, api=True)
    if user_id:
        ret_json = {"status": 200, "msg": "You've successfully signed up!", "data": user_id}
    else:
        ret_json = {"status": 301, "msg": "Error while signing up"}
    return jsonify(ret_json)


@core_app.route("/api/v1/sign-in", methods=["POST"])
async def sign_in() -> Dict[str, Any]:
    posted_data = await request.get_json()

    email = posted_data["email"]
    password = posted_data["password"]

    ret_json, error = await verify_credentials(email, password)
    if error:
        return jsonify(ret_json)
    user_id = (await users.find_one(conditions={"email": email})).id
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    await users.update({"token": jwt_token}, {"email": email})
    ret_json = {
        "status": 200,
        "msg": "You've successfully logged in",
        "token": jwt_token,
        "id": user_id
    }

    return jsonify(ret_json)


@core_app.route("/api/v1/reset-password", methods=["POST"])
async def reset_password() -> Dict[str, Any]:
    posted_data = await request.get_json()
    email = posted_data["email"]
    if not await email_exists(email):
        return jsonify(generate_return_dict(301, "Email doesn't exist"))
    new_password = await get_random_string(12)
    message = (
        "You've reset your password.\n"
        "This is your new password, please sign in to your account and change it.\n"
        f"Password: {new_password}"
    )

    await send_mail(
        send_from=MAIL_ADRESS,
        send_to=email,
        subject="New password",
        message=message,
        server=MAIL_SERVER,
        port=MAIL_PORT,
        username=MAIL_ADRESS,
        password=MAIL_PASSWORD,
        use_tls=MAIL_USE_TLS
        )

    hashed_pw = get_hashed_pw(new_password).decode("utf-8")
    await users.update({"password": hashed_pw}, {"email": email})

    return jsonify(generate_return_dict(200, "Password successfully changed"))

async def authenticate(data: str) -> bool:
    if data.startswith("Bearer"):
        token = str.replace(str(data), 'Bearer ','')
    else:
        user_id = data
        token = (await users.find_one({"id": user_id}, ["token"])).token
    user_id = (await users.find_one({"token": token}, ["id"])).id
    decoded = json.loads(json.dumps(jwt.decode(token, JWT_SECRET, JWT_ALGORITHM)))
    user_id_token = decoded['user_id']
    expiry_time = decoded['exp']
    if user_id == user_id_token:
        return True
    else:
        return False


async def verify_pw(email: str, password: str) -> bool:
    if not await email_exists(email):
        return False

    hashed_pw = (await users.find_one({"email": email}))["password"]
    if type(hashed_pw) == str:
        hashed_pw = hashed_pw.encode("utf-8")

    if bcrypt.hashpw(password.encode("utf-8"), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def generate_return_dict(status: int, message: str) -> Dict[str, Any]:
    ret_json = {"status": status, "message": message}
    return ret_json


async def verify_credentials(
    email: str, password: str
) -> Tuple[Optional[Dict[str, Any]], bool]:
    if not await email_exists(email):
        return generate_return_dict(301, "Invalid email"), True

    correct_pw = await verify_pw(email, password)

    if not correct_pw:
        return generate_return_dict(302, "Invalid Password"), True

    return None, False


async def email_exists(email: str) -> bool:
    if await users.find_and_count({"email": email}) > 0:
        return True
    else:
        return False


async def get_random_string(length: int) -> str:
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str
