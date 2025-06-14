from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import os
import hmac
import hashlib
import time
import urllib.parse
from config import SECRET_KEY

# 使用环境变量或默认值设置密钥和IV
CRYPTO_KEY = os.environ.get('CRYPTO_KEY', SECRET_KEY).encode()[:32]
CRYPTO_IV = os.environ.get('CRYPTO_IV', 'JPY0IbolqwiPFpKC').encode()[:16]

def encrypt_data(data):
    cipher = Cipher(algorithms.AES(CRYPTO_KEY), modes.CBC(CRYPTO_IV), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    if isinstance(data, str):
        data = data.encode()
    padded_data = padder.update(data) + padder.finalize()
    encrypted = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_data(encrypted_data):
    cipher = Cipher(algorithms.AES(CRYPTO_KEY), modes.CBC(CRYPTO_IV), backend=default_backend())
    decryptor = cipher.decryptor()
    encrypted = base64.b64decode(encrypted_data.encode())
    decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode()

# 讯飞星火API HMAC签名相关函数
def generate_xf_signature(api_key, api_secret, host, date, method="POST", path="/v1/chat/completions"):
    """为讯飞星火API生成HMAC签名
    
    参数:
        api_key: API Key
        api_secret: API Secret
        host: 主机名
        date: 请求日期 (RFC1123格式, 如 "Mon, 02 Jan 2006 15:04:05 GMT")
        method: 请求方法, 默认POST
        path: API路径, 默认/v1/chat/completions
    
    返回:
        包含authorization, date和host的请求头字典
    """
    # 1. 构建签名原文
    signature_origin = f"host: {host}\ndate: {date}\n{method} {path} HTTP/1.1"
    
    # 2. 使用HMAC-SHA256计算签名
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    
    # 3. Base64编码签名结果
    signature = base64.b64encode(signature_sha).decode('utf-8')
    
    # 4. 构建authorization_origin
    authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    
    # 5. Base64编码authorization
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    
    # 6. 返回请求头字典
    return {
        "authorization": authorization,
        "date": date,
        "host": host
    }
