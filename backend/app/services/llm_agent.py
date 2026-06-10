import json
from groq import Groq
from sqlalchemy.orm import Session
from app.models.sar import SARDraft
from app.models.alert import Alert
from app.models.llm_config import LLMConfig
from app.models.pii_map import PIIMap
from app.config import settings
import time

def generate_sar(alert_id: str, db: Session) -> SARDraft:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    llm_config = db.query(LLMConfig).filter(LLMConfig.tenant_id == alert.tenant_id).first()
    pii_map = db.query(PIIMap).filter(PIIMap.alert_id == alert_id).first()
    
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    # 1. Format the evidence payload
    payload = alert.masked_payload
    compliance_rules = []
    # If there were compliance matches, we would fetch them. For brevity:
    prompt = f"""
    You are an expert Anti-Money Laundering (AML) Compliance Officer.
    Review the following transaction details and generate a Suspicious Activity Report (SAR) narrative.
    
    TRANSACTION DATA (PII Masked):
    {json.dumps(payload, indent=2)}
    
    RISK SCORE: {alert.risk_score}
    
    Please provide:
    1. A clear, professional narrative explaining why this transaction is suspicious.
    2. A structured JSON assessment with 'key_indicators' and 'recommended_action'.
    
    Format your response EXACTLY as follows:
    ---NARRATIVE---
    [Your narrative here]
    ---JSON---
    [Your JSON here]
    """
    
    start_time = time.time()
    
    completion = client.chat.completions.create(
        model=llm_config.model_name,
        messages=[
            {"role": "system", "content": "You are a precise, objective compliance expert. Only output the requested sections."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=2048,
        top_p=1,
        stream=False
    )
    
    latency = int((time.time() - start_time) * 1000)
    response_text = completion.choices[0].message.content
    
    try:
        parts = response_text.split('---JSON---')
        narrative_part = parts[0].replace('---NARRATIVE---', '').strip()
        json_part = parts[1].strip() if len(parts) > 1 else "{}"
        structured_data = json.loads(json_part)
    except Exception as e:
        narrative_part = response_text
        structured_data = {"error": "Failed to parse structured output"}
        
    # Rehydrate
    rehydrated_text = narrative_part
    if pii_map:
        for token, original in pii_map.token_map.items():
            rehydrated_text = rehydrated_text.replace(token, str(original))
            
    # Save Draft
    draft = SARDraft(
        alert_id=alert.id,
        tenant_id=alert.tenant_id,
        draft_text=narrative_part,
        draft_structured=structured_data,
        rehydrated_text=rehydrated_text,
        llm_provider=llm_config.provider,
        llm_model=llm_config.model_name,
        prompt_used=prompt,
        generation_latency_ms=latency,
        prompt_tokens=completion.usage.prompt_tokens,
        completion_tokens=completion.usage.completion_tokens
    )
    db.add(draft)
    
    llm_config.total_requests += 1
    llm_config.total_tokens_used += completion.usage.total_tokens
    
    db.commit()
    db.refresh(draft)
    
    return draft
