"""Seven LLM-driven autonomous ESG agents.

Each agent has a goal, a tool set, and an autonomous tool-selection loop. The
existing deterministic modules remain the trusted computation layer underneath.
"""
from .core import AutonomousAgent, Tool
from . import tools as t


def agent1():
    return AutonomousAgent("Agent 1 - Autonomous BRSR Extraction Agent",
        "Extract and validate the required BRSR ESG metrics from company reports.",
        "Inspect the PDF and search evidence. Select table, keyword-context, or text-window extraction based on observations. Validate extracted values and retry with another strategy when evidence is weak. Complete the cohort only when outputs are sufficiently covered.",
        [
            Tool("inspect_pdf","Inspect PDF pages and availability.",{"type":"object","properties":{"company_code":{"type":"string"}},"required":["company_code"]},t.inspect_pdf),
            Tool("search_document","Search a company PDF for a metric phrase.",{"type":"object","properties":{"company_code":{"type":"string"},"query":{"type":"string"}},"required":["company_code","query"]},t.search_document),
            Tool("extract_table","Inspect tables on candidate PDF pages.",{"type":"object","properties":{"company_code":{"type":"string"},"page_numbers":{"type":"array","items":{"type":"integer"}}},"required":["company_code","page_numbers"]},t.extract_table),
            Tool("extract_metric_with_strategy","Extract one metric using a selected strategy.",{"type":"object","properties":{"company_code":{"type":"string"},"metric_name":{"type":"string"},"strategy":{"type":"string","enum":["table","keyword_context","text_window"]}},"required":["company_code","metric_name","strategy"]},t.extract_metric_with_strategy),
            Tool("validate_metric","Validate an extracted metric value.",{"type":"object","properties":{"metric_name":{"type":"string"},"value":{"type":"number"}},"required":["metric_name","value"]},t.validate_metric),
            Tool("run_agent1_for_all","Run the trusted extraction engine across the cohort after planning/inspection.",{"type":"object","properties":{},"required":[]},t.run_agent1_for_all),
        ])

def agent2():
    return AutonomousAgent("Agent 2 - Autonomous Environmental Risk Agent","Assess environmental risk for company locations using available AQI evidence.","Inspect data first, choose relevant location analyses, and run the full cohort when the evidence is adequate.",[Tool("inspect_environmental_data","Inspect available AQI datasets.",{"type":"object","properties":{},"required":[]},t.inspect_environmental_data),Tool("analyze_location","Analyze AQI for a company city.",{"type":"object","properties":{"company_code":{"type":"string"},"city":{"type":"string"}},"required":["company_code","city"]},t.analyze_location),Tool("run_agent2_all","Run the environmental analysis for all configured companies.",{"type":"object","properties":{},"required":[]},t.run_agent2_all)])

def agent3():
    return AutonomousAgent("Agent 3 - Autonomous ESG News Agent","Determine ESG relevance and sentiment of company news.","Inspect the news schema, test relevance/sentiment tools when useful, and run the cohort analysis once the data is understood. You may choose VADER or TextBlob for an inspection.",[Tool("inspect_news_data","Inspect the news dataset.",{"type":"object","properties":{},"required":[]},t.inspect_news_data),Tool("assess_esg_relevance","Assess ESG relevance of a news text.",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]},t.assess_esg_relevance),Tool("analyze_news_text","Analyze sentiment using VADER or TextBlob.",{"type":"object","properties":{"text":{"type":"string"},"method":{"type":"string","enum":["vader","textblob"]}},"required":["text","method"]},t.analyze_news_text),Tool("run_agent3_all","Run the full news sentiment agent.",{"type":"object","properties":{},"required":[]},t.run_agent3_all)])

def agent4():
    return AutonomousAgent("Agent 4 - Autonomous Financial Correlation Agent","Analyze stock performance and its relationship to ESG outputs.","Inspect available market data, choose useful company analyses, and run the cohort correlation stage when inputs are ready.",[Tool("inspect_stock_data","Inspect stock dataset coverage.",{"type":"object","properties":{},"required":[]},t.inspect_stock_data),Tool("analyze_company_stock","Inspect stock data for one company.",{"type":"object","properties":{"company_code":{"type":"string"}},"required":["company_code"]},t.analyze_company_stock),Tool("run_agent4_all","Run the full stock/ESG correlation agent.",{"type":"object","properties":{},"required":[]},t.run_agent4_all)])

def agent5():
    return AutonomousAgent("Agent 5 - Autonomous Greenwashing Detection Agent","Cross-check BRSR claims against environmental and news evidence and identify potential contradictions.","Inspect the available cross-source datasets before choosing company-level or cohort-level detection. Do not invent evidence.",[Tool("inspect_cross_source_data","Inspect the input datasets and samples.",{"type":"object","properties":{"company_code":{"type":"string"}},"required":["company_code"]},t.inspect_cross_source_data),Tool("run_agent5_company","Run cross-source detection for one company.",{"type":"object","properties":{"company_code":{"type":"string"}},"required":["company_code"]},t.run_agent5_company),Tool("run_agent5_all","Run greenwashing detection for the full cohort.",{"type":"object","properties":{},"required":[]},t.run_agent5_all)])

def agent6():
    return AutonomousAgent("Agent 6 - Autonomous Master ESG Scoring Agent","Combine validated upstream evidence into ESG pillar and master scores with quality gates.","Inspect inputs, assess whether the upstream evidence is present, then execute scoring. If inputs are missing, report the dependency instead of fabricating values.",[Tool("inspect_scoring_inputs","Inspect upstream agent outputs.",{"type":"object","properties":{},"required":[]},t.inspect_scoring_inputs),Tool("run_agent6_all","Run quality gates, cross-validation and master scoring for the cohort.",{"type":"object","properties":{},"required":[]},t.run_agent6_all)])

def agent7():
    return AutonomousAgent("Agent 7 - Autonomous Explainability Agent","Generate evidence-based human-readable explanations of the final ESG analysis.","Inspect final scores, optionally inspect an individual company, and generate the final explanation output. Do not invent facts beyond the available score data.",[Tool("inspect_score_output","Inspect master score output.",{"type":"object","properties":{},"required":[]},t.inspect_score_output),Tool("explain_company","Generate an explanation for one company from the computed scores.",{"type":"object","properties":{"company_code":{"type":"string"}},"required":["company_code"]},t.explain_company),Tool("run_agent7_all","Generate explainable outputs for the cohort.",{"type":"object","properties":{},"required":[]},t.run_agent7_all)])

AGENT_FACTORIES={"agent1":agent1,"agent2":agent2,"agent3":agent3,"agent4":agent4,"agent5":agent5,"agent6":agent6,"agent7":agent7}
