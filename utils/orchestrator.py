"""Dependency-aware orchestration for dynamic ESG data acquisition."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from utils.provenance import StageTimer, new_run_id


Fetcher = Callable[[Dict[str, Any]], Any]


@dataclass(frozen=True)
class StageSpec:
    """One source stage and its optional fallback."""

    name: str
    source: str
    fetch: Fetcher
    fallback: Optional[Fetcher] = None
    depends_on_filing: bool = False


class DynamicOrchestrator:
    """Run filing, market, news, and environmental stages with dependencies."""

    def __init__(
        self,
        *,
        cache_dir: Path,
        run_id: Optional[str] = None,
        max_workers: int = 3,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or new_run_id()
        self.max_workers = max(1, max_workers)
        self.timing: list[Dict[str, Any]] = []

    def _cache_path(self, stage: StageSpec, context: Dict[str, Any]) -> Path:
        company = str(context.get("company_code", "unknown")).lower()
        safe_stage = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in stage.name.lower()
        )
        return self.cache_dir / f"{company}_{safe_stage}.json"

    def _read_cache(
        self,
        stage: StageSpec,
        context: Dict[str, Any],
    ) -> Optional[Any]:
        path = self._cache_path(stage, context)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(
        self,
        stage: StageSpec,
        context: Dict[str, Any],
        value: Any,
    ) -> None:
        path = self._cache_path(stage, context)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(value, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _run_stage(
        self,
        stage: StageSpec,
        context: Dict[str, Any],
        *,
        allow_cache: bool,
    ) -> Dict[str, Any]:
        timer = StageTimer(
            run_id=self.run_id,
            stage=stage.name,
            source=stage.source,
        )
        if allow_cache:
            cached = self._read_cache(stage, context)
            if cached is not None:
                timing = timer.finish(status="cached")
                timing["Fallback_Used"] = False
                self.timing.append(timing)
                return {
                    "status": "cached",
                    "source": stage.source,
                    "data": cached,
                    "timing": timing,
                }

        try:
            value = stage.fetch(context)
            self._write_cache(stage, context, value)
            timing = timer.finish()
            self.timing.append(timing)
            return {
                "status": "success",
                "source": stage.source,
                "data": value,
                "timing": timing,
            }
        except Exception as exc:
            if stage.fallback is None:
                timing = timer.finish(status="failed", error=str(exc))
                self.timing.append(timing)
                return {
                    "status": "failed",
                    "source": stage.source,
                    "error": str(exc),
                    "timing": timing,
                }

            try:
                value = stage.fallback(context)
                self._write_cache(stage, context, value)
                timer.fallback_used = True
                timing = timer.finish(status="fallback", error=str(exc))
                self.timing.append(timing)
                return {
                    "status": "fallback",
                    "source": stage.source,
                    "data": value,
                    "error": str(exc),
                    "timing": timing,
                }
            except Exception as fallback_exc:
                error = f"primary: {exc}; fallback: {fallback_exc}"
                timer.fallback_used = True
                timing = timer.finish(status="failed", error=error)
                self.timing.append(timing)
                return {
                    "status": "failed",
                    "source": stage.source,
                    "error": error,
                    "timing": timing,
                }

    def run(
        self,
        context: Dict[str, Any],
        *,
        filing: StageSpec,
        market: StageSpec,
        news: StageSpec,
        environment: StageSpec,
        allow_cache: bool = True,
    ) -> Dict[str, Any]:
        """Run filing first, market/news in parallel, then environment."""
        filing_result = self._run_stage(filing, context, allow_cache=allow_cache)
        enriched_context = dict(context)
        enriched_context["filing"] = filing_result.get("data")

        independent = [market, news]
        results: Dict[str, Any] = {"filing": filing_result}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, 2)) as executor:
            futures = {
                executor.submit(
                    self._run_stage,
                    stage,
                    enriched_context,
                    allow_cache=allow_cache,
                ): stage.name
                for stage in independent
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()

        environment_context = dict(enriched_context)
        environment_context["market"] = results.get(market.name, {}).get("data")
        environment_context["news"] = results.get(news.name, {}).get("data")
        results["environment"] = self._run_stage(
            environment,
            environment_context,
            allow_cache=allow_cache,
        )
        results["run_id"] = self.run_id
        results["timing"] = list(self.timing)
        results["status"] = (
            "failed"
            if any(result.get("status") == "failed" for result in results.values() if isinstance(result, dict))
            else "completed"
        )
        return results
