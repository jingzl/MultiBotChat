from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
import hashlib
from pydantic import BaseModel
import os
import sys

# 添加项目根目录到Python路径
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
print(f"添加到路径: {root_dir}")
print(f"当前Python路径: {sys.path}")

try:
    from config import SECRET_KEY, TOKEN_EXPIRATION
    print("成功导入config")
except ImportError as e:
    print(f"导入config失败: {e}")
    raise

app = FastAPI(title="MultiBot Chat API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 数据模型
class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# API路由
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # TODO: 实现数据库验证
        # 临时使用JSON文件验证
        from utils.user_manager import user_manager
        print(f"获取到user_manager: {user_manager}")
        if not user_manager.login(form_data.username, form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(seconds=TOKEN_EXPIRATION)
        access_token = create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"登录时发生错误: {e}")
        raise

@app.post("/register")
async def register(user: User):
    try:
        # TODO: 实现数据库注册
        # 临时使用JSON文件注册
        from utils.user_manager import user_manager
        if not user_manager.register(user.username, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists or invalid format"
            )
        return {"message": "User registered successfully"}
    except Exception as e:
        print(f"注册时发生错误: {e}")
        raise

@app.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    token: str = Depends(oauth2_scheme)
):
    try:
        # TODO: 实现数据库密码修改
        # 临时使用JSON文件修改
        from utils.user_manager import user_manager
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if not user_manager.change_password(username, old_password, new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid old password"
            )
        return {"message": "Password changed successfully"}
    except Exception as e:
        print(f"修改密码时发生错误: {e}")
        raise

@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    username = payload.get("sub")
    return {"username": username}

@app.get("/")
async def root():
    return {"message": "MultiBot Chat API is running! 访问 /docs 获取API文档"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 