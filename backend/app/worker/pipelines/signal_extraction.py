# Signal Extraction Pipeline Step
# TODO: Implement in Session 3

"""
LLM을 사용한 시그널 추출:
1. Claude Sonnet 4로 시그널 추출
2. Guardrails 검증 (금지 표현, evidence 필수)
3. 중복 시그널 필터링
4. DB 저장

Fallback: Claude → GPT-4o → Gemini 1.5 Pro
"""
