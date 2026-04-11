from typing import Any, Dict, List, Optional, Tuple, Callable, Awaitable
from pydantic import BaseModel, Field

class ScenePlanSchema(BaseModel):
    location: str = Field(..., description="場所名")
    characters: List[str] = Field(..., description="登場キャラクター")
    description: str = Field(..., description="シーンの内容")

class PlannerOutputSchema(BaseModel):
    scene_plan: List[ScenePlanSchema] = Field(..., description="シーンごとの詳細計画")
    key_events: List[str] = Field(..., description="発生すべき重要な出来事")
    cliffhanger: str = Field(..., description="今回の引き（クリフハンガー）")
    emotional_arc: str = Field(..., description="感情の起伏")

class TextValidationSchema(BaseModel):
    is_consistent: bool = Field(..., description="整合性あり")
    contradiction_found: str = Field("", description="矛盾点")

async def run_novel_generation_cycle(
    client, 
    context: str, 
    style_dna: Optional[dict] = None, 
    relevant_knowledge: List[str] = None,
    max_retries: int = 2
):
    """
    3ステップ小説生成パイプライン (System C): 
    プロット立案 -> 詳細設定の反映 -> 執筆 & 整合性検証ループ
    """
    # 1. Planning Step
    prompt_plan = f"一流作家として次話のプロットを立案せよ。\n文脈: {context}\n知識: {relevant_knowledge}\nDNA: {style_dna}"
    plan_resp = await client.generate_content(
        model="gemini-2.0-flash", contents=prompt_plan,
        config={"response_mime_type": "application/json", "response_schema": PlannerOutputSchema}
    )
    plan = plan_resp.parsed

    # 2. Writing (Initially)
    prompt_write = f"プロットに基づき執筆せよ。\n計画: {plan.model_dump_json()}\n文脈: {context}"
    content = (await client.generate_content(model="gemini-2.0-flash", contents=prompt_write)).text

    # 3. Validation Loop
    for _ in range(max_retries):
        prompt_val = f"設定矛盾をチェックせよ。\n本文: {content[:2000]}\n知識: {relevant_knowledge}"
        val_resp = await client.generate_content(
            model="gemini-2.0-flash", contents=prompt_val,
            config={"response_mime_type": "application/json", "response_schema": TextValidationSchema}
        )
        val = val_resp.parsed
        if val.is_consistent:
            return content, True
        
        # Re-write if inconsistent
        prompt_fix = f"矛盾点: {val.contradiction_found} を修正して再執筆せよ。"
        content = (await client.generate_content(model="gemini-2.0-flash", contents=prompt_fix)).text

    return content, False
