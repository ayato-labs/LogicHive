from pydantic import BaseModel, Field


class WorldBibleEntrySchema(BaseModel):
    category: str = Field(..., description="ひとつ選択: character, location, item, plot, world")
    content: str = Field(..., description="具体的な事実・設定の内容")


class CharacterProfileSchema(BaseModel):
    character_name: str = Field(..., description="名前")
    aliases: list[str] = Field(default_factory=list, description="別名・二つ名")
    personality_traits: list[str] = Field(default_factory=list, description="性格的特徴")
    speech_style: str = Field(..., description="口調の特徴や決め台詞など")
    relationships: dict[str, str] = Field(default_factory=dict, description="他者との関係性")
    summary: str = Field(..., description="魅力解析・まとめ")


class FullAnalysisExtraction(BaseModel):
    world_entries: list[WorldBibleEntrySchema] = Field(default_factory=list)
    character_profiles: list[CharacterProfileSchema] = Field(default_factory=list)


async def extract_novel_knowledge(client, text: str, model: str = "gemini-2.0-flash"):
    """
    小説本文から設定知識（世界観・キャラ・プロット）を抽出し、構造化データとして返却する。
    物語の整合性を維持するための「World Bible」構築のコアロジック。
    """
    prompt = f"""
以下の小説本文から、物語の世界観や今後の展開に影響を与える重要な「設定・事実」および「キャラクター詳細」を抽出してください。

1. 設定・事実 (World Bible):
   - character: 人物関係の変化。location: 地名・施設。item: 道具・アーティファクト。plot: 事件・謎。world: 規則・魔法・背景。
2. キャラクター像 (Character Profile):
   - 性格、口調、他者との関係性、その人物の魅力を抽出。

本文:
{text}
"""
    response = await client.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": FullAnalysisExtraction,
        },
    )
    return response.parsed
