@echo off
echo 正在启动MultiBot Chat应用...

rem 启动后端
echo 正在启动后端服务...
start cmd /k "cd %~dp0backend && start_server.bat"

rem 等待几秒钟让后端先启动
timeout /t 5

rem 启动前端
echo 正在启动前端应用...
start cmd /k "cd %~dp0 && start_server.bat"

echo 服务启动中，请稍候...
echo 前端地址: http://127.0.0.1:8501
echo 后端API地址: http://127.0.0.1:8080/docs

echo 如果上述方式启动失败，请尝试在命令行中直接运行:
echo cd %~dp0
echo streamlit run app.py

timeout /t 3 