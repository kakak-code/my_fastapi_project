import re
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from app.services.extractor import extract_sections_with_llm, format_output

router = APIRouter()


class ExtractRequest(BaseModel):
    """参数提取请求模型（JSON格式）"""
    text: str = Field(..., description="待提取的文本内容，支持{{#llm.text#}}格式")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "{{#llm.text#}}关于评价的故事\n庄子关于评价的故事讲述了...\n\n关于得失的故事\n庄子关于得失的故事讲述了...{{#llm.text#}}"
            }
        }


class ExtractResponse(BaseModel):
    """参数提取响应模型（JSON格式）"""
    result: str = Field(..., description="提取结果，纯JSON数组字符串")
    
    class Config:
        json_schema_extra = {
            "example": {
                "result": '[{"section":"关于评价的故事","bullets":"庄子关于评价的故事讲述了..."},{"section":"关于得失的故事","bullets":"庄子关于得失的故事讲述了..."}]'
            }
        }


@router.post(
    "/extractor",
    summary="参数提取器",
    description="提取文本中每个章节的标题和对应章节的大纲内容，请求体和响应均为JSON格式",
    tags=["extractor"],
    response_model=ExtractResponse,
    response_class=JSONResponse
)
async def extract_parameters(request: ExtractRequest) -> ExtractResponse:
    """
    提取文本中每个章节的标题和对应章节的大纲内容。
    
    处理规则：
    1. 提取文本中每个章节的标题和对应章节的大纲内容
    2. 输出格式仅为JSON数组，禁止包含任何XML标签、解释性文字、备注或多余符号
    3. JSON数组结构：每个元素包含 "section"（章节标题）和 "bullets"（大纲内容）两个键
    
    请求示例：
    ```json
    {
        "text": "{{#llm.text#}}你的文本内容...{{#llm.text#}}"
    }
    ```
    
    响应示例：
    ```json
    {
        "result": "[{\"section\": \"章节标题\", \"bullets\": \"大纲内容\"}]"
    }
    ```
    """
    try:
        # 处理{{#llm.text#}}格式，提取实际文本内容
        text = request.text
        
        # 移除{{#llm.text#}}标记（如果存在）
        text = re.sub(r'\{\{#llm\.text#\}\}', '', text)
        text = text.strip()
        
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 提取章节信息
        sections = extract_sections_with_llm(text)
        
        # 格式化为纯JSON字符串
        result = format_output(sections)
        
        logger.info(f"成功提取 {len(sections)} 个章节")
        
        return ExtractResponse(result=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提取参数时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")

