import os
import re
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from openai import OpenAI
import json
from tqdm import tqdm
from langchain_core.messages import HumanMessage
# --- 配置与初始化 ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MOCK_API_CALLS = False

# 初始化两个独立的客户端
text_client: Optional[ChatOpenAI] = None
vision_client: Optional[ChatOpenAI] = None

try:
    # 用于处理表格和文本的客户端
    text_client = ChatOpenAI(
        model_name=os.getenv("LLM_TEXT_MODEL", "deepseek-chat"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base="https://api.deepseek.com/v1"
    )
    # 专门用于处理图片的客户端
    vision_client = ChatOpenAI(
        model_name=os.getenv("LLM_TEXT_MODEL", "deepseek-chat"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base="https://api.deepseek.com/v1"
    )
    if not MOCK_API_CALLS and not (text_client.api_key and vision_client.api_key):
        raise ValueError("OpenAI API Key未配置，请检查.env文件")
except Exception as e:
    logging.error(f"初始化LangChain客户端失败: {e}")


# --- 异步API调用函数 ---
async def describe_image_with_llm_async(image_url: str) -> str:
    """调用【视觉模型】对网络图片进行总结"""
    if MOCK_API_CALLS: return "这是一张由AI生成的关于云端图片的总结"
    if not vision_client: return "视觉模型客户端未初始化"

    # ★★★ 核心修复点 1: 使用正确的LangChain多模态消息格式 ★★★
    message = HumanMessage(
        content=json.dumps([
            {"type": "text", "text": "请用一句话详细描述这张图片的内容，用于图片的alt文本。"},
            {"type": "image", "image_url": {"url": image_url}}
        ])
    )

    try:
        logging.info(f"正在为云端图片生成描述: {image_url[:50]}...")
        # ★★★ 核心修复点 2: 使用专门的vision_client ★★★
        response = await vision_client.ainvoke([message])
        description = response.content
        logging.info(f"描述生成成功: {description[:30]}...")
        return description
    except Exception as e:
        logging.error(f"为云端图片生成描述时出错: {e}", exc_info=True)
        return "图片内容描述生成失败"


async def summarize_table_with_llm_async(table_md: str) -> str:
    """调用【文本模型】对表格进行概括"""
    if MOCK_API_CALLS: return "\n[表格内容摘要：...]\n"
    if not text_client: return "[表格总结失败：文本模型未初始化]"
    prompt = f"以下是一个Markdown表格，请对其核心信息进行总结,且字数控制在100内...\n\n表格内容:\n{table_md}"
    try:
        # ★★★ 核心修复点 3: 使用专门的text_client ★★★
        response = await text_client.ainvoke(prompt)
        description = response.content
        logging.info(f"描述生成成功: {description}...")
        return f"\n[表格内容摘要：{response.content}]\n"
    except Exception as e:
        logging.error(f"总结表格时出错: {e}", exc_info=True)
        return "[表格内容总结失败]"


# --- 核心处理逻辑 ---
class MarkdownProcessor:
    def __init__(self):
        self.pattern = re.compile(
            r'(!\[\[([^\]]+)\]\])|'  # 1, 2: Typora-style image
            r'(!\[(.*?)\]\((.*?)\s*(?:"(.*?)")?\))|'  # 3, 4, 5, 6: Standard image
            r'((\n\s*\|.*\|[ \t]*\n)+(?:\|.*-.*\|[ \t]*\n)(?:\|.*\|[ \t]*\n)*)',  # 7: Table
            re.MULTILINE
        )

    async def process_file_async(self, file_path: Path) -> Dict[str, Any]:
        logging.info(f"--- 开始处理: {file_path} ---")
        doc_id = str(uuid.uuid4())

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logging.error(f"读取文件失败 {file_path}: {e}"); return {}

        tasks = []
        matches = list(self.pattern.finditer(content))

        for match in matches:
            start_index = match.start()
            if match.group(1):  # Typora图片 (一定是本地图片)
                tasks.append(self.process_local_image(match.group(1), start_index=start_index))
            elif match.group(3):  # 标准图片
                image_path_str = match.group(5)
                if image_path_str.strip().startswith("http"):
                    # 这是网络图片
                    tasks.append(self.process_remote_image(match.group(3), image_path_str, match.group(6) or "",
                                                           start_index=start_index))
                else:
                    # 这是本地图片
                    tasks.append(self.process_local_image(match.group(3), start_index=start_index))
            elif match.group(7):  # 表格
                tasks.append(self.process_table_match(match.group(7), start_index=start_index))

        replacements = await asyncio.gather(*tasks)

        processed_content = content
        for old, new, _ in sorted(replacements, key=lambda x: x[2], reverse=True):
            if new and old in processed_content:
                processed_content = processed_content.replace(old, new, 1)

        return {"doc_id": doc_id, "original_path": str(file_path), "processed_content": processed_content}

    async def process_remote_image(self, original_markup: str, image_url: str, title: str, start_index: int) -> Tuple[
        str, Optional[str], int]:
        """处理网络图片：只调用AI进行描述"""
        description = await describe_image_with_llm_async(image_url)
        new_markup = f'![{description}]({image_url} "{title}")'
        return original_markup, new_markup, start_index

    async def process_local_image(self, original_markup: str, start_index: int) -> Tuple[str, Optional[str], int]:
        """处理本地图片：只修改alt文本为'[本地图片]'"""
        # 使用正则表达式来安全地替换alt文本，同时保留其他部分
        # 匹配 ![任意内容](任意内容 "任意内容") 或 ![[任意内容]]

        if original_markup.startswith("![["):
            # Typora格式: ![[path]]
            path = original_markup[3:-2]
            new_markup = f'![本地图片]({path})'  # 将其转换为标准格式，方便统一处理
        else:
            # 标准格式: ![alt](src "title")
            match = re.match(r'!\[(.*?)\]\((.*?)\s*(?:"(.*?)")?\)', original_markup)
            if match:
                _alt, src, title = match.groups()
                title_part = f' "{title}"' if title else ""
                new_markup = f'![本地图片]({src}{title_part})'
            else:
                new_markup = original_markup  # 无法解析则不修改

        logging.info(f"标记本地图片: {original_markup} -> {new_markup}")
        # 注意：这里我们返回一个立即完成的awaitable对象
        return original_markup, new_markup, start_index

    async def process_table_match(self, original_markup: str, start_index: int = 0) -> Tuple[str, Optional[str], int]:
        """处理表格：调用AI进行总结"""
        summary = await summarize_table_with_llm_async(original_markup)
        return original_markup, summary, start_index


# --- Main函数 ---
async def main_async(input_dir: str, output_dir: str):
    # (此部分代码与上一版完全相同，无需修改)
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not input_path.is_dir():
        logging.error(f"输入路径不是一个有效的目录: {input_dir}");
        return
    md_files = list(input_path.rglob("*.md"))
    if not md_files:
        logging.warning("在指定目录中未找到任何.md文件。");
        return

    processor = MarkdownProcessor()

    tasks = [processor.process_file_async(f) for f in md_files]
    results = []
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="处理MD文件"):
        results.append(await f)

    logging.info("开始保存处理后的文件...")
    for result in results:
        if not result: continue
        try:
            original_file_path = Path(result['original_path'])
            relative_path = original_file_path.relative_to(input_path)
            output_md_path = output_path / relative_path
            output_md_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write(result['processed_content'])

            import json
            output_json_path = output_md_path.with_suffix('.json')
            with open(output_json_path, 'w', encoding='utf-8') as f:
                metadata_to_save = {"doc_id": result['doc_id'], "original_path": result['original_path'],
                                    "processed_at": datetime.now().isoformat()}
                json.dump(metadata_to_save, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存文件 {result.get('original_path')} 的结果时出错: {e}")
    logging.info(f"处理完成！所有结果已保存到目录: {output_dir}")


if __name__ == "__main__":
    base_project_path = Path(r"C:\Users\36265\Desktop\个人-汇报")
    INPUT_KNOWLEDGE_BASE_DIR = base_project_path / "OptimizeKB"
    OUTPUT_PROCESSED_DIR = base_project_path / "ProcessedKB"

    print(f"自动化处理脚本启动...")
    print(f"输入知识库目录 (Input): {INPUT_KNOWLEDGE_BASE_DIR}")
    print(f"处理后输出目录 (Output): {OUTPUT_PROCESSED_DIR}")

    if not INPUT_KNOWLEDGE_BASE_DIR.exists():
        print(f"\n错误: 输入目录不存在! 请确认路径是否正确: {INPUT_KNOWLEDGE_BASE_DIR}")
        exit()

    asyncio.run(main_async(INPUT_KNOWLEDGE_BASE_DIR, OUTPUT_PROCESSED_DIR))