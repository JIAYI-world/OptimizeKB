import base64
import httpx
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
# 下载并编码图片
image_url = "https://d1iv7db44yhgxn.cloudfront.net/documentation/images/c39694c9-42bb-4fb4-9f98-848e10da4364/significanceplugin.png" # 替换为实际图片 URL
image_data = base64.b64encode(httpx.get(image_url).read()).decode("utf-8")
load_dotenv()
# openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
# messages_payload = [
#     {
#         "role": "user",
#         "content": [
#             {
#                 "type": "text",
#                 "text": "请用一句话详细描述这张图片的内容，用于图片的alt文本。"
#             },
#             {
#                 "type": "image",
#                 "image_url": {
#                     "url": image_url
#                 }
#             }
#         ]
#     }
# ]
#
# # 使用修复后的请求体进行API调用
# response = openai_client.chat.completions.create(
#     model=os.getenv("LLM_TEXT_MODEL", "deepseek-chat"),
#     messages=messages_payload,
#     max_tokens=100
# )
#
# description = response.choices[0].message.content.strip()
# print(description)
# # 配置 DeepSeek 模型
model = ChatOpenAI(
model_name="deepseek-chat",
openai_api_key=os.getenv("OPENAI_API_KEY"), # 从环境变量获取密钥
openai_api_base="https://api.deepseek.com/v1"
)

# 构建多模态消息
message = HumanMessage(
content=json.dumps([
{"type": "text", "text": "请描述这张图片"},
{"type": "image", "image_url": image_url}
])
)

# 调用 API 并获取响应
response = model.invoke([message])
print(response.content)