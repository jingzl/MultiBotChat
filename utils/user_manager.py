import json
import hashlib
import os
import streamlit as st
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from utils.crypto_utils import encrypt_data, decrypt_data
import logging
import time
import re
import requests
from config import (
    TOKEN_EXPIRATION, USER_DATA_FILE, LOG_LEVEL, TOKEN_DIR, SECRET_KEY, ENABLED_REGISTER,
    API_BASE_URL  # 新增API基础URL配置
)

logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger(__name__)

# 全局变量，用于控制是否使用本地模式（不连接后端）
USE_LOCAL_MODE = os.getenv('MULTIBOT_USE_LOCAL_MODE', 'False').lower() == 'true'

class UserManager:
    def __init__(self):
        self._token = None
        self._username = None
        self.api_base_url = API_BASE_URL
        self._backend_available = True
        
        # 尝试连接后端，检查是否可用
        try:
            # 增加超时时间并添加重试机制
            for attempt in range(3):  # 尝试3次
                try:
                    LOGGER.info(f"尝试连接后端API: {self.api_base_url} (尝试 {attempt+1}/3)")
                    response = requests.get(f"{self.api_base_url}/", timeout=10)  # 将超时增加到10秒
                    if response.status_code == 200:
                        LOGGER.info("成功连接到后端API")
                        self._backend_available = True
                        break
                    else:
                        LOGGER.warning(f"后端API返回非200状态码: {response.status_code}")
                except Exception as e:
                    LOGGER.warning(f"尝试 {attempt+1}/3 连接后端API失败: {e}")
                    if attempt == 2:  # 最后一次尝试
                        self._backend_available = False
                        LOGGER.warning(f"无法连接到后端API，将使用本地模式: {e}")
            
        except Exception as e:
            LOGGER.warning(f"无法连接到后端API，将使用本地模式: {e}")
            self._backend_available = False
            
        if USE_LOCAL_MODE:
            LOGGER.info("已强制使用本地模式")
            self._backend_available = False
            
        if not self._backend_available:
            LOGGER.warning("后端API不可用，将使用本地模式进行用户认证")
            st.warning("⚠️ 后端服务未启动，使用本地模式（仅用于开发测试）")

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def load_users(self):
        if not os.path.exists(USER_DATA_FILE):
            return {}
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_users(self, users):
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(users, file, ensure_ascii=False, indent=4)

    def register(self, username, password):
        if not ENABLED_REGISTER:
            st.warning("暂未开放注册")
            return False

        if not re.match(r'^[a-zA-Z0-9@\._]{1,32}$', username):
            return False

        # 使用后端API
        if self._backend_available:
            try:
                response = requests.post(
                    f"{self.api_base_url}/register",
                    json={"username": username, "password": password}
                )
                return response.status_code == 200
            except Exception as e:
                LOGGER.error(f"注册请求失败: {str(e)}")
                return False
        
        # 本地模式
        else:
            users = self.load_users()
            if username in users:
                st.warning("已存在此账号")
                return False
            users[username] = self.hash_password(password)
            self.save_users(users)
            return True

    def login(self, username, password):
        # 使用后端API
        if self._backend_available:
            try:
                response = requests.post(
                    f"{self.api_base_url}/token",
                    data={"username": username, "password": password}
                )
                if response.status_code == 200:
                    token_data = response.json()
                    self._token = token_data["access_token"]
                    self._username = username
                    return True
                return False
            except Exception as e:
                LOGGER.error(f"登录请求失败: {str(e)}")
                return False
        
        # 本地模式
        else:
            users = self.load_users()
            if username not in users or users[username] != self.hash_password(password):
                return False
            self._username = username
            self._token = self.generate_token(username)
            return True

    def change_password(self, username, old_password, new_password):
        # 使用后端API
        if self._backend_available:
            try:
                response = requests.post(
                    f"{self.api_base_url}/change-password",
                    json={
                        "old_password": old_password,
                        "new_password": new_password
                    },
                    headers={"Authorization": f"Bearer {self._token}"}
                )
                return response.status_code == 200
            except Exception as e:
                LOGGER.error(f"修改密码请求失败: {str(e)}")
                return False
        
        # 本地模式
        else:
            users = self.load_users()
            if username not in users or users[username] != self.hash_password(old_password):
                return False
            users[username] = self.hash_password(new_password)
            self.save_users(users)
            return True

    def get_logged_in_username(self):
        return self._username

    def save_token_to_file(self, data):
        if not os.path.exists(TOKEN_DIR):
            os.makedirs(TOKEN_DIR)
        token_file = os.path.join(TOKEN_DIR, f"{self._token}.token")
        encrypted_data = encrypt_data(data)
        with open(token_file, 'w') as f:
            f.write(encrypted_data)

    def load_token_from_file(self):
        token_file = os.path.join(TOKEN_DIR, f"{self._token}.token")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                encrypted_data = f.read()
            return decrypt_data(encrypted_data)
        return None

    def destroy_token(self):
        if self._token:
            token_file = os.path.join(TOKEN_DIR, f"{self._token}.token")
            if os.path.exists(token_file):
                os.remove(token_file)
        self._token = None
        self._username = None

    def generate_token(self, username):
        serializer = URLSafeTimedSerializer(SECRET_KEY)
        token = serializer.dumps({'username': username, 'created_at': time.time()}, salt=SECRET_KEY)
        self._token = token
        self._username = username
        self.save_session_state_to_file()
        return token

    def verify_token(self, token=None):
        if token is not None:
            self._token = token
        if not self._token:
            return False
        try:
            serializer = URLSafeTimedSerializer(SECRET_KEY)
            data = serializer.loads(self._token, salt=SECRET_KEY, max_age=TOKEN_EXPIRATION)
            username = data['username']
            created_at = data['created_at']

            if time.time() - created_at > TOKEN_EXPIRATION:
                LOGGER.warning(f"Token expired for user: {username}")
                self.destroy_token()
                return False
            
            session_data = self.load_token_from_file()
            if session_data:
                session_data = json.loads(session_data)
                for key, value in session_data.items():
                    if not hasattr(st.session_state, key):
                        setattr(st.session_state, key, value)
                self._username = username
                return True
        except (SignatureExpired, BadSignature):
            LOGGER.warning("Invalid or expired token")
        except Exception as e:
            LOGGER.error(f"Error verifying token: {str(e)}")
        return False

    def save_session_state_to_file(self):
        if not self._token:
            return
        
        session_data = dict(st.session_state)

        # 只保留特定属性
        for key in list(session_data.keys()):
            if key not in ['logged_in', 'username', 'bots', 'default_bot', 'chat_config']:
                del session_data[key]
        
        LOGGER.info(f"Saving session state. Username: {session_data.get('username')}")
        data = json.dumps(session_data)
        self.save_token_to_file(data)

    def get_username_from_token(self):
        if not self._token:
            return None
        data = self.load_token_from_file()
        if data:
            session_data = json.loads(data)
            return session_data.get('username')
        return None

    def is_backend_available(self):
        return self._backend_available

# 创建全局 UserManager 实例
user_manager = UserManager()
