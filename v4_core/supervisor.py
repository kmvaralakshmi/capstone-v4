"""LLM supervisor for V4.

The supervisor dynamically routes work to specialist agents. The actual ESG calculations
remain deterministic and auditable. This avoids claiming that the LLM itself calculated
numerical ESG scores.
"""
from __future__ import annotations
import json, os, time
from pathlib import Path
from openai import OpenAI

SPECIALISTS = {
    "brsr_extraction": "Extract and validate BRSR metrics and preserve page/evidence metadata.",
    "esg_research": "Analyze ESG-relevant text/news and retrieve supporting information.",
    "market_risk": "Analyze market/risk information where available.",
    "validation": "Check completeness, consistency, extraction confidence and evidence quality.",
    "scoring": "Run the deterministic V4 ESG scoring engine after validated inputs exist.",
    "greenwashing": "Identify potential disclosure-performance inconsistencies; never assert greenwashing as fact.",
    "explainability": "Produce evidence-grounded explanations using metric contributions and source pages."
}

class Supervisor:
    def __init__(self, model=None, max_steps=12):
        self.model=model or os.getenv("OPENAI_MODEL","gpt-5.6-luna")
        self.max_steps=max_steps
        self.client=OpenAI()
        self.trace=[]

    def run(self, goal, state_summary):
        tools=[{"type":"function","name":"delegate","description":"Select the next specialist agent to execute.",
                 "parameters":{"type":"object","properties":{"agent":{"type":"string","enum":list(SPECIALISTS)},"reason":{"type":"string"}},"required":["agent","reason"],"additionalProperties":False}}]
        instructions=("You are the ESG project supervisor. Coordinate specialist agents toward the goal. "
                      "Select only the next specialist needed based on current state. Do not invent numerical data. "
                      "Numerical scoring is deterministic. Potential greenwashing must remain a signal requiring review.")
        inp=f"Goal: {goal}\nCurrent state: {state_summary}\nAvailable specialists: {json.dumps(SPECIALISTS)}"
        for step in range(self.max_steps):
            r=self.client.responses.create(model=self.model,instructions=instructions,input=inp,tools=tools,tool_choice="auto")
            calls=[x for x in r.output if getattr(x,"type",None)=="function_call"]
            if not calls:
                self.trace.append({"step":step+1,"final":r.output_text}); break
            call=calls[0]; args=json.loads(call.arguments)
            self.trace.append({"step":step+1,"selected_agent":args["agent"],"reason":args["reason"]})
            # The application runner executes the selected specialist and feeds the result back.
            inp += f"\nSupervisor selected {args['agent']}. Execute it now and return its output summary."
        return self.trace
