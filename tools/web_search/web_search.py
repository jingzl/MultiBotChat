from duckduckgo_search import DDGS
import json
from utils.base_llm import base_llm_completion
from config import LOGGER
import os
import streamlit as st
import html


def format_to_markdown(query, results):
    try:
        markdown_outputs = [f'搜索主题：{query}']
        for i, item in enumerate(results):
            # 使用Streamlit的按钮组件来打开链接
            # 为每个链接创建一个唯一的键，以避免在同一个会话中的冲突
            key = f"link_{i}_{hash(item['href'])}"
            title = html.escape(item['title'])
            body = html.escape(item['body'])
            href = html.escape(item['href'])
            
            # 使用st的特性，让链接在新标签页中打开
            markdown_outputs.append(f"""# {title}

摘要：{body}

<a href="{href}" target="_blank" rel="noopener noreferrer">在新窗口中阅读原文</a>

或点击此处复制链接：`{href}`
""")
        return '\n\n'.join(markdown_outputs)
    except json.JSONDecodeError:
        return "Error: Invalid JSON string"
    except KeyError as e:
        return f"Error: Missing key {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def run(parameter, content, group_prompt, group_history):
    try:
        completion = base_llm_completion(
            '请结合上下文深入理解我当前的关注点，将我当下最可能检索的1~5个关键问题短语用空格分开，输出成一行',
            system_prompt="你是一个搜索高手，擅长解读用户的真实意图，并拟定最适合搜索的关键短语，你永远只提炼关键短语，不要做其他的事情，你的输出不超过50个字",
            history=group_history[-10:],
        )
        query = completion.choices[0].message.content
    except Exception as e:
        return f'[ERROR] 调用本地模型时发生错误: {str(e)}'
        
    try:
        if os.getenv('HTTPS_PROXY','tb'):
            ddgs = DDGS(proxy=os.getenv('HTTPS_PROXY'))
        else:
            ddgs = DDGS()
        
        with ddgs:
            results = ddgs.text(query[0:100], region='cn-zh', max_results=3)
    
        if not results:
            LOGGER.error("No results found")
            return '没有找到结果'
        markdown_results = format_to_markdown(query,results)
        return markdown_results
    
    except Exception as e:
        return f'[ERROR] 通过DuckDuckGo搜索时发生错误: {str(e)}'