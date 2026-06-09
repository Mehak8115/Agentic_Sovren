# agents/agent_engine.py
"""
Shared ReAct engine used by all three agents.

Pattern per step:
  THOUGHT: <reasoning>
  ACTION:  <tool_name>
  ARGS:    <json>
  ...repeat...
  THOUGHT: <final reasoning>
  FINISH:  <natural language answer>

The engine:
  - Shows LLM only tool descriptions + schemas (not raw data)
  - Stores all live objects in a context dict (no huge JSON in prompts)
  - Limits loop to MAX_STEPS
  - Returns structured output + thought_process log
"""

import os
import json
import re
from dotenv import load_dotenv
from agents.groq_client import groq_chat

load_dotenv()

MAX_STEPS = 20


class AgentEngine:
    """
    Generic ReAct loop engine.

    Usage:
        engine = AgentEngine(tools, system_prompt)
        result = engine.run(user_message, initial_context)
    """

    def __init__(self, tools: dict, system_prompt: str):
        """
        tools: {
          "tool_name": {
            "description": str,
            "args": [{"name": str, "type": str, "required": bool}],
            "fn": callable,
          }
        }
        """
        self.tools         = tools
        self.system_prompt = system_prompt
        self.memory: list[str] = []

    def run(self, user_message: str, context: dict | None = None) -> dict:
        self.memory = []
        ctx = context or {}

        tool_schema = self._format_tool_schema()
        system = self.system_prompt.format(tool_schema=tool_schema)

        messages = [
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_message},
        ]

        finish_text  = None
        final_result = None

        for step in range(MAX_STEPS):
            llm_out = groq_chat(messages=messages, temperature=0)
            messages.append({"role": "assistant", "content": llm_out})

            parsed = self._parse(llm_out)

            thought = parsed.get("thought", "")
            if thought:
                self._log(f"[THINK] {thought[:200]}")

            # FINISH
            if "finish" in parsed:
                finish_text = parsed["finish"]
                self._log(f"[FINISH] {finish_text[:200]}")
                break

            action = parsed.get("action")
            args   = parsed.get("args", {})

            if not action:
                self._log("[WARN] No action found, stopping.")
                break

            self._log(f"[ACT]   {action}({json.dumps(args, default=str)[:120]})")

            # Execute tool
            observation = self._execute(action, args, ctx)

            # Store in context with tool name as key
            ctx[action] = observation

            obs_str = self._summarise(action, observation)
            self._log(f"[OBS]   {obs_str}")

            messages.append({
                "role":    "user",
                "content": f"OBSERVATION from {action}:\n{obs_str}\n\nContinue.",
            })

            # If the tool returned a final usable result, capture it
            if isinstance(observation, dict) and "error" not in observation:
                final_result = observation

        return {
            "finish":        finish_text or "Agent completed.",
            "final_result":  final_result or ctx.get(list(ctx.keys())[-1]) if ctx else {},
            "context":       ctx,
            "thought_process": self.memory,
        }

    # ── Internals ─────────────────────────────────────────────────────────────

    def _format_tool_schema(self) -> str:
        lines = []
        for name, meta in self.tools.items():
            args = ", ".join(
                f"{a['name']}({'required' if a.get('required') else 'optional'})"
                for a in meta.get("args", [])
            ) or "none"
            lines.append(f"- {name}({args}): {meta['description']}")
        return "\n".join(lines)

    def _parse(self, text: str) -> dict:
        thought = action = finish = None
        args = {}

        m = re.search(r"THOUGHT:\s*(.+?)(?=ACTION:|FINISH:|$)", text, re.DOTALL | re.IGNORECASE)
        if m:
            thought = m.group(1).strip()

        m = re.search(r"FINISH:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
        if m:
            finish = m.group(1).strip()
            return {"thought": thought, "finish": finish}

        m = re.search(r"ACTION:\s*(\w+)", text, re.IGNORECASE)
        if m:
            action = m.group(1).strip()

        m = re.search(r"ARGS:\s*(\{.*?\}|\[.*?\])", text, re.DOTALL | re.IGNORECASE)
        if m:
            try:
                args = json.loads(m.group(1))
            except Exception:
                args = {}

        return {"thought": thought, "action": action, "args": args}

    def _execute(self, tool_name: str, args: dict, ctx: dict) -> any:
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        fn = self.tools[tool_name]["fn"]

        # Resolve context references
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str) and v in ctx:
                # Direct context key reference
                resolved[k] = ctx[v]
            elif isinstance(v, str) and "." in v:
                # Nested reference: "extract_requirements.location"
                parts = v.split(".", 1)
                parent = ctx.get(parts[0])
                if isinstance(parent, dict):
                    resolved[k] = parent.get(parts[1], v)
                else:
                    resolved[k] = v
            else:
                resolved[k] = v

        try:
            return fn(**resolved)
        except Exception as e:
            return {"error": str(e)}

    def _summarise(self, tool_name: str, result: any) -> str:
        if isinstance(result, dict) and "error" in result:
            return f"ERROR: {result['error']}"
        if isinstance(result, list):
            n = len(result)
            if n == 0:
                return "Empty list — 0 items found"
            first = result[0]
            if isinstance(first, dict):
                # Show useful preview fields
                useful = ["name", "title", "price_per_day", "location", "rating",
                          "gap_score", "is_eligible", "booking_status", "recommendation_score"]
                preview = {k: first[k] for k in useful if k in first}
                names = [r.get("name") or r.get("title") or r.get("candidate_id","?")
                         for r in result[:5]]
                return f"{n} items found. Names/titles: {names}. First item: {json.dumps(preview, default=str)[:200]}"
            return f"{n} items"
        if isinstance(result, dict):
            important = ["job_id", "title", "name", "candidate_id", "booking_id",
                         "gap_score", "is_eligible", "status", "valid", "error",
                         "recommendation", "count", "eligible_jobs", "budget_max",
                         "budget_min", "travel_month", "location", "user_sentiment"]
            summary = {k: result[k] for k in important if k in result}
            if not summary:
                summary = dict(list(result.items())[:6])
            return json.dumps(summary, default=str)[:300]
        return str(result)[:200]

    def _log(self, msg: str):
        self.memory.append(msg)
