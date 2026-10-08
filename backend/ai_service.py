import re
from typing import Dict, Any, List
from .config import get_gemini_api_key

def local_fallback_summary(segments: List[Dict[str, Any]], video_title: str) -> Dict[str, Any]:
    """Smart heuristic summarizer when Gemini API Key is not yet configured."""
    if not segments:
        return {
            "summary_3lines": [
                "영상의 자막 데이터가 비어 있어 자동 요약을 생성할 수 없습니다.",
                "영상 링크와 자막 지원 여부를 확인해 주세요.",
                "Gemini API 키를 등록하시면 정밀 AI 분석이 가능합니다."
            ],
            "timeline": [],
            "keywords": ["유튜브", "영상요약", "Gemini AI"],
            "is_ai_generated": False
        }

    total_segs = len(segments)
    # Pick 3 key representative sections (beginning, middle, conclusion)
    line1 = segments[min(2, total_segs - 1)]['text'] if total_segs > 2 else segments[0]['text']
    line2 = segments[total_segs // 2]['text'] if total_segs > 3 else "영상 본론의 핵심 내용이 논의됩니다."
    line3 = segments[max(0, total_segs - 2)]['text'] if total_segs > 4 else "영상의 마무리 및 결론이 요약됩니다."

    # Group into timeline intervals
    step = max(1, total_segs // 5)
    timeline = []
    for i in range(0, total_segs, step):
        seg = segments[i]
        timeline.append({
            "timestamp": seg['timestamp'],
            "topic": seg['text'][:80] + ("..." if len(seg['text']) > 80 else "")
        })

    # Simple keyword extraction
    all_words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', " ".join([s['text'] for s in segments]))
    stopwords = {"이것", "저것", "그것", "있는", "하는", "그리고", "하지만", "진짜", "너무", "이런", "그런", "저런", "그냥", "오늘", "제가"}
    freq = {}
    for w in all_words:
        if w not in stopwords and len(w) >= 2:
            freq[w] = freq.get(w, 0) + 1
    top_keywords = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:6]

    return {
        "summary_3lines": [
            f"1️⃣ {line1}",
            f"2️⃣ {line2}",
            f"3️⃣ {line3}"
        ],
        "timeline": timeline[:6],
        "keywords": top_keywords or ["유튜브", "동영상", "핵심요약"],
        "is_ai_generated": False,
        "note": "⚙️ Gemini API 키를 입력하시면 공식 Gemini 3.8 Flash 모델이 정밀 문맥 이해를 바탕으로 압도적인 고품질 3줄 요약과 챕터를 생성합니다."
    }

def summarize_with_gemini(transcript_text: str, video_title: str) -> Dict[str, Any]:
    api_key = get_gemini_api_key()
    if not api_key:
        return {"success": False, "error": "GEMINI_API_KEY_MISSING"}

    prompt = f"""당신은 전문 유튜브 영상 분석가이자 속독 요약 전문가입니다.
아래는 유튜브 영상 "{video_title}"의 타임스탬프가 포함된 전체 자막 스크립트입니다.
이 내용을 바탕으로 시청자가 단 30초 만에 영상의 핵심을 완벽히 이해할 수 있도록 명확하고 매력적인 요약 보고서를 작성해 주세요.

[요구사항]
1. 📌 **핵심 3줄 요약**: 영상의 핵심 내용을 임팩트 있게 3개의 번호 목록(1, 2, 3)으로 요약 (한 줄당 1~2문장)
2. ⏱️ **타임라인별 핵심 내용 정리**: 중요한 주제가 바뀌는 타임스탬프와 해당 구간의 핵심 주제 요약 (4~6개 항목)
3. 💡 **핵심 키워드 & 인사이트**: 영상에서 가장 중요한 핵심 키워드 5개 및 시청자를 위한 핵심 시사점 1줄

[자막 스크립트]
{transcript_text[:12000]}
"""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        # Try gemini-3.8-flash, fallback to gemini-2.5-flash or gemini-1.5-flash
        models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
        response_text = ""
        
        for m in models_to_try:
            try:
                # First attempt with client.interactions.create
                interaction = client.interactions.create(
                    model=m,
                    input=prompt
                )
                response_text = interaction.output_text or ""
                if response_text:
                    break
            except Exception:
                try:
                    # Fallback to generate_content
                    resp = client.models.generate_content(
                        model=m,
                        contents=prompt
                    )
                    response_text = resp.text or ""
                    if response_text:
                        break
                except Exception:
                    continue

        if not response_text:
            return {"success": False, "error": "Gemini API 응답 생성 실패"}

        return {
            "success": True,
            "markdown": response_text,
            "is_ai_generated": True
        }

    except Exception as e:
        return {"success": False, "error": f"Gemini API 호출 에러: {str(e)}"}
