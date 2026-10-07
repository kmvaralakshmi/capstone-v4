"""Run the LLM-driven autonomous seven-agent ESG system."""
from __future__ import annotations
import argparse, json, os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from pathlib import Path
from ai_agents.agents import AGENT_FACTORIES

ROOT=Path(__file__).resolve().parent
TRACE=ROOT/"processed-data"/"ai_agent_traces"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--agents", nargs="*", default=["agent1","agent2","agent3","agent4","agent5","agent6","agent7"])
    p.add_argument("--max-steps", type=int, default=12)
    args=p.parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for autonomous AI mode. See .env.example and AI_AGENT_README.md")
    TRACE.mkdir(parents=True, exist_ok=True)
    results=[]
    context={"project":"Explainable Multi-Agent ESG Risk Analysis System","target_fy":"FY 2024-25","companies":"configured cohort","instruction":"Work autonomously using the tools available to your specialist role. Inspect observations and choose the next action."}
    for key in args.agents:
        if key not in AGENT_FACTORIES: raise SystemExit(f"Unknown agent: {key}")
        agent=AGENT_FACTORIES[key](); agent.max_steps=args.max_steps
        print(f"\n===== {agent.name} =====")
        result=agent.run(context)
        agent.save_trace(TRACE/f"{key}_trace.json")
        print(result.get("final",""))
        results.append(result)
        context["previous_agent"]={"agent":result.get("agent"),"status":result.get("status"),"final":result.get("final","")}
    (TRACE/"run_summary.json").write_text(json.dumps(results,indent=2,default=str),encoding="utf-8")
    print(f"\nAutonomous run traces saved to {TRACE}")

if __name__=="__main__": main()
