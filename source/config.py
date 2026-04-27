"""
环境变量配置模块 (Configuration Module)

这是一个简单的辅助模块。
当我们启动应用时，这个模块会通过 python-dotenv 库，
自动去读取项目根目录下的 `.env` 文件，把里面的 API Keys 加载进系统的环境变量中。
"""
import os
from dotenv import load_dotenv

# 自动寻找并读取 .env 文件
load_dotenv()

# 从环境变量中获取模型所需要的 Key
# 如果你发现程序报错说没权限，第一件事就是去检查 .env 文件配好了没！
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
KIMI_API_KEY = os.getenv("KIMI_API_KEY")
