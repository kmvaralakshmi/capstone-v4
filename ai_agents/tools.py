"""Tool functions exposed to the autonomous ESG agents.

The existing deterministic implementations remain the computation tools. The
LLM decides which tool to call, when to call it, and whether another observation
or tool is needed before finishing.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import PROCESSED_DATA_DIR, OUTPUT_FILES, COMPANIES, ESG_METRICS, DATA_PATHS
from utils.pdf_extractor import extract_text_from_pdf, extract_tables_from_pdf
from utils.data_validator import validate_numeric_value, validate_percentage
from agents.agent1_brsr_extractor import BRSRExtractionAgent
from agents.agent2_environmental_risk import EnvironmentalRiskValidator
from agents.agent3_news_sentiment import NewsSentimentAnalyzer
from agents.agent4_stock_correlation import StockCorrelationAnalyzer
from agents.agent5_greenwashing_detector import GreenwashingDetector
from agents.agent6_master_scorer import MasterESGScorer
from agents.agent7_explainable_ai import ExplainableAIAgent


def _df_info(path):
    p = Path(path)
    if not p.exists(): return {"exists": False, "path": str(p)}
    try:
        df = pd.read_csv(p)
        return {"exists": True, "path": str(p), "rows": len(df), "columns": list(df.columns), "sample": df.head(3).to_dict("records")}
    except Exception as e:
        return {"exists": True, "path": str(p), "error": str(e)}

# ---------------- Agent 1 ----------------
def inspect_pdf(company_code: str) -> dict:
    info = COMPANIES[company_code]
    path = ROOT / "brsr-pdfs" / info["brsr_file"]
    if not path.exists(): return {"company": company_code, "exists": False, "path": str(path)}
    text = extract_text_from_pdf(path)
    return {"company": company_code, "path": str(path), "pages": len(text), "page_lengths": {str(k): len(v or '') for k,v in list(text.items())[:10]}}

def search_document(company_code: str, query: str) -> dict:
    info = COMPANIES[company_code]; path = ROOT / "brsr-pdfs" / info["brsr_file"]
    text = extract_text_from_pdf(path)
    hits=[]
    q=query.lower()
    for page, body in text.items():
        if q in (body or '').lower():
            idx=(body or '').lower().find(q); hits.append({"page":page,"context":(body or '')[max(0,idx-180):idx+len(q)+300]})
    return {"query":query,"hits":hits[:12],"hit_count":len(hits)}

def extract_table(company_code: str, page_numbers: list[int]) -> dict:
    info=COMPANIES[company_code]; path=ROOT / "brsr-pdfs" / info["brsr_file"]
    tables=extract_tables_from_pdf(path, page_numbers=page_numbers)
    serial={str(p): t[:10] for p,t in tables.items()}
    return {"company":company_code,"pages":page_numbers,"tables":serial}

def extract_metric_with_strategy(company_code: str, metric_name: str, strategy: str) -> dict:
    agent=BRSRExtractionAgent(); info=COMPANIES[company_code]; path=ROOT/"brsr-pdfs"/info["brsr_file"]
    text=extract_text_from_pdf(path); metric_info=None
    for category, metrics in agent.metrics.items():
        for m in metrics:
            if m['name'].lower()==metric_name.lower(): metric_info=m
    if metric_info is None: return {"error":"Unknown metric"}
    keywords=agent._get_search_keywords(metric_name)
    if strategy=="table":
        # Find candidate pages using keywords, then extract tables only there.
        pages=[]
        for p,b in text.items():
            if any(k.lower() in (b or '').lower() for k in keywords): pages.append(p)
        value,page,keyword=agent._extract_from_tables(path, keywords, metric_info, page_numbers=pages[:12])
    elif strategy=="keyword_context":
        sr=agent._search_terms_in_cached_text(text, keywords); value,page,keyword=agent._extract_from_context_search(sr,metric_info)
    else:
        value,page,keyword=agent._extract_from_text_window(text,keywords,metric_info)
    return {"company":company_code,"metric":metric_name,"strategy":strategy,"value":value,"page":page,"keyword":keyword}

def validate_metric(metric_name: str, value: float) -> dict:
    agent=BRSRExtractionAgent();
    info=None
    for ms in agent.metrics.values():
        for m in ms:
            if m['name'].lower()==metric_name.lower(): info=m
    if info is None: return {"error":"Unknown metric"}
    status, review, note=agent._validate_metric_value(metric_name,info,value)
    return {"metric":metric_name,"value":value,"status":status,"needs_review":review,"note":note}

def run_agent1_for_all() -> dict:
    agent=BRSRExtractionAgent(); df=agent.process_all_companies(mode='auto'); path=agent.save_to_csv(df); agent.save_timing_csv()
    return {"status":"completed","rows":len(df),"output":str(path)}

# ---------------- Agent 2 ----------------
def inspect_environmental_data() -> dict:
    agent=EnvironmentalRiskValidator(); h,r=agent.load_air_quality_data(); return {"historical_rows":len(h),"historical_columns":list(h.columns),"realtime_rows":len(r),"realtime_columns":list(r.columns)}

def analyze_location(company_code: str, city: str) -> dict:
    agent=EnvironmentalRiskValidator(); h,r=agent.load_air_quality_data(); return agent.calculate_city_aqi_score(h,r,city)

def run_agent2_all() -> dict:
    agent=EnvironmentalRiskValidator(); h,r=agent.load_air_quality_data(); df=agent.process_all_companies(h,r); p=agent.save_to_csv(df); return {"status":"completed","rows":len(df),"output":str(p)}

# ---------------- Agent 3 ----------------
def inspect_news_data() -> dict:
    a=NewsSentimentAnalyzer(); df=a.load_news_data(); return {"rows":len(df),"columns":list(df.columns),"sample":df.head(3).to_dict('records')}

def analyze_news_text(text: str, method: str) -> dict:
    a=NewsSentimentAnalyzer(); return a.analyze_sentiment_vader(text) if method.lower()=="vader" else a.analyze_sentiment_textblob(text)

def assess_esg_relevance(text: str) -> dict:
    a=NewsSentimentAnalyzer(); score,rel,inc,exc=a.compute_esg_relevance(text); return {"score":score,"is_relevant":rel,"include_matches":inc,"exclude_matches":exc}

def run_agent3_all() -> dict:
    a=NewsSentimentAnalyzer(); df=a.load_news_data(); out=a.process_all_companies(df); p=a.save_to_csv(out); rp=a.save_rejected_to_csv(); return {"status":"completed","rows":len(out),"output":str(p),"rejected":str(rp)}

# ---------------- Agent 4 ----------------
def inspect_stock_data() -> dict:
    a=StockCorrelationAnalyzer(); df=a.load_stock_data(); return {"rows":len(df),"columns":list(df.columns),"date_min":str(df['Date'].min()) if not df.empty else None,"date_max":str(df['Date'].max()) if not df.empty else None}

def analyze_company_stock(company_code: str) -> dict:
    a=StockCorrelationAnalyzer(); df=a.load_stock_data(); ticker=a.match_company_ticker(company_code); rows=df[df.get('Ticker',df.get('Symbol',''))==ticker] if not df.empty else pd.DataFrame();
    if rows.empty and not df.empty:
        cols=[c for c in df.columns if c.lower() in ('ticker','symbol','company_code')]; rows=df[df[cols[0]].astype(str).str.contains(ticker.replace('.NS',''),case=False,na=False)] if cols else df.iloc[0:0]
    return {"company":company_code,"ticker":ticker,"rows":len(rows),"sample":rows.tail(5).to_dict('records')}

def run_agent4_all() -> dict:
    a=StockCorrelationAnalyzer(); df=a.load_stock_data(); out=a.process_all_companies(df); p=a.save_to_csv(out); return {"status":"completed","rows":len(out),"output":str(p)}

# ---------------- Agent 5 ----------------
def inspect_cross_source_data(company_code: str) -> dict:
    paths={k: PROCESSED_DATA_DIR/OUTPUT_FILES[k] for k in ['brsr_metrics','environmental_risk','news_sentiment']}
    return {k:_df_info(v) for k,v in paths.items()}

def run_agent5_company(company_code: str) -> dict:
    a=GreenwashingDetector(); b=a.load_brsr_metrics(); e=a.load_environmental_risk(); n=a.load_news_sentiment();
    b=b[b['Company_Code']==company_code] if not b.empty else b
    out=a.process_all_companies(b,e,n); p=a.save_to_csv(out); return {"status":"completed","company":company_code,"rows":len(out),"output":str(p)}

def run_agent5_all() -> dict:
    a=GreenwashingDetector(); b=a.load_brsr_metrics(); e=a.load_environmental_risk(); n=a.load_news_sentiment(); out=a.process_all_companies(b,e,n); p=a.save_to_csv(out); return {"status":"completed","rows":len(out),"output":str(p)}

# ---------------- Agent 6 ----------------
def inspect_scoring_inputs() -> dict:
    return {k:_df_info(PROCESSED_DATA_DIR/OUTPUT_FILES[k]) for k in ['brsr_metrics','environmental_risk','news_sentiment','stock_correlation','greenwashing']}

def run_agent6_all() -> dict:
    a=MasterESGScorer(); d=a.load_all_agent_outputs(); d=a.apply_quality_gate(d); out=a.process_all_companies(d); p=a.save_to_csv(out); a.save_cross_validation_report(); a.save_quality_report(); b=a.build_external_benchmark_report(out,d); a.save_benchmark_report(b); return {"status":"completed","rows":len(out),"output":str(p)}

# ---------------- Agent 7 ----------------
def inspect_score_output() -> dict:
    return _df_info(PROCESSED_DATA_DIR/OUTPUT_FILES['master_scores'])

def explain_company(company_code: str) -> dict:
    a=ExplainableAIAgent(); df=a.load_master_scores(); row=df[df['Company_Code']==company_code]
    if row.empty: return {"error":"Company not found"}
    r=row.iloc[0]; return {"company":company_code,"explanation":a.generate_score_explanation(company_code,r),"strengths":a.identify_strengths(company_code,r),"weaknesses":a.identify_weaknesses(company_code,r),"recommendations":a.generate_recommendations(company_code,r,a.identify_weaknesses(company_code,r))}

def run_agent7_all() -> dict:
    a=ExplainableAIAgent(); df=a.load_master_scores(); out=a.process_all_companies(df); p=a.save_to_csv(out); return {"status":"completed","rows":len(out),"output":str(p)}
