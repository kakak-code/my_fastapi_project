import json
import re
from typing import Any

from loguru import logger

from app.core.config import Settings


def extract_sections_with_llm(text: str, settings: Settings | None = None) -> list[dict[str, str]]:
    """
    使用LLM提取文本中的章节标题和大纲内容。
    
    如果未配置LLM API，则使用基于规则的提取方法。
    
    Args:
        text: 待提取的文本内容
        settings: 应用配置（可选）
        
    Returns:
        包含章节信息的JSON数组，每个元素包含 "section" 和 "bullets" 键
    """
    # 如果配置了LLM API，可以使用LLM进行智能提取
    # 这里先实现基于规则的提取方法作为fallback
    
    return extract_sections_with_rules(text)


def extract_sections_with_rules(text: str) -> list[dict[str, str]]:
    """
    使用基于规则的提取方法提取章节标题和大纲内容。
    
    支持多种章节标题格式：
    - 数字编号：1. 标题、1.1 标题
    - 中文编号：第一章、第一节
    - 特殊标记：# 标题、## 标题
    - 纯文本标题（以换行分隔）
    
    Args:
        text: 待提取的文本内容
        
    Returns:
        包含章节信息的JSON数组
    """
    sections = []
    
    # 清理文本
    text = text.strip()
    if not text:
        return sections
    
    # 尝试多种章节标题模式
    patterns = [
        # 中文"关于...的故事"、"关于...的"等格式
        r'^(关于[^。，,]+(?:的故事|的|)?)\s*[:：]?\s*$',
        # 数字编号：1. 标题 或 1.1 标题
        r'^(\d+(?:\.\d+)*\.?\s+)(.+?)$',
        # 中文编号：第一章、第一节、一、等
        r'^(第[一二三四五六七八九十百千万\d]+[章节部分])\s*(.+?)$',
        # Markdown风格：# 标题 或 ## 标题
        r'^(#{1,6})\s+(.+?)$',
        # 带下划线的标题：==== 或 ----
        r'^(.+?)\s*[=_-]{3,}$',
        # 单独的中文标题（短句，通常不超过20字）
        r'^([^。，,]{2,20}?)$',
    ]
    
    lines = text.split('\n')
    current_section: dict[str, str] | None = None
    current_bullets: list[str] = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 检查是否是章节标题
        is_section_title = False
        section_title = None
        
        for pattern in patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                is_section_title = True
                # 提取标题文本
                if pattern.startswith(r'^(关于'):
                    section_title = match.group(1).strip()
                elif pattern.startswith(r'^(\d+'):
                    section_title = match.group(2).strip()
                elif pattern.startswith(r'^(第'):
                    section_title = match.group(1) + ' ' + match.group(2).strip()
                elif pattern.startswith(r'^(#{1,6})'):
                    section_title = match.group(2).strip()
                elif pattern.startswith(r'^(.+?)\s*[=_-]'):
                    section_title = match.group(1).strip()
                elif pattern.startswith(r'^([^。，,]{2,20}?)'):
                    # 检查是否是标题：下一行有内容，且当前行较短
                    if i + 1 < len(lines) and lines[i + 1].strip() and len(line) <= 30:
                        section_title = match.group(1).strip()
                    else:
                        is_section_title = False
                        section_title = None
                break
        
        # 如果没有匹配到标准模式，检查是否是明显的标题行
        # 标题通常较短（2-30字），且后面跟着内容，且不包含句号
        if not is_section_title and 2 <= len(line) <= 30 and '。' not in line:
            # 检查下一行是否有内容
            if i + 1 < len(lines) and lines[i + 1].strip():
                # 检查上一行是否为空或也是标题（连续标题的情况）
                prev_empty = i == 0 or not lines[i - 1].strip()
                if prev_empty:
                    # 可能是标题
                    is_section_title = True
                    section_title = line
        
        if is_section_title and section_title:
            # 保存上一个章节
            if current_section:
                current_section['bullets'] = ' '.join(current_bullets).strip()
                if current_section['bullets']:
                    sections.append(current_section)
            
            # 开始新章节
            current_section = {'section': section_title, 'bullets': ''}
            current_bullets = []
        else:
            # 添加到当前章节的大纲内容
            if current_section:
                current_bullets.append(line)
            else:
                # 如果没有当前章节，创建一个默认章节
                current_section = {'section': '概述', 'bullets': ''}
                current_bullets = [line]
    
    # 保存最后一个章节
    if current_section:
        current_section['bullets'] = ' '.join(current_bullets).strip()
        if current_section['bullets']:
            sections.append(current_section)
    
    # 如果没有提取到任何章节，返回整个文本作为单个章节
    if not sections:
        sections = [{'section': '全文', 'bullets': text[:500]}]
    
    return sections


def format_output(sections: list[dict[str, str]]) -> str:
    """
    将章节信息格式化为纯JSON字符串，不包含任何XML标签或解释性文字。
    
    Args:
        sections: 章节信息列表
        
    Returns:
        纯JSON字符串（紧凑格式，无缩进）
    """
    return json.dumps(sections, ensure_ascii=False, separators=(',', ':'))

