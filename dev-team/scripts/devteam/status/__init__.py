"""`dt status`: what each skill needs before it starts. One module per skill; `common` holds the printer, the
docs line, next IDs and the SessionStart summary; `packages` holds package ids, Grow triggers, contract
freshness and drift. The CLI is `commands/status.py`."""
from __future__ import annotations

from ..repo import Repo
from .api_probe import api_probe
from .architecture_design import architecture_design
from .build_planning import build_planning
from .build_setup import build_setup
from .common import Report, add_common, add_graph
from .idea_refine import idea_refine
from .pipeline_design import pipeline_design
from .reference_intake import reference_intake
from .spec_writing import spec_writing
from .testplanning import test_planning

HANDLERS = {"idea-refine": idea_refine, "spec-writing": spec_writing, "architecture-design": architecture_design,
            "pipeline-design": pipeline_design, "test-planning": test_planning, "build-planning": build_planning,
            "build-setup": build_setup, "reference-intake": reference_intake, "api-probe": api_probe}
SKILLS = list(HANDLERS)


def report(repo: Repo, skill: str | None) -> Report:
    r = Report()
    r.add("skill", skill or "—")
    if skill:
        HANDLERS[skill](repo, r)
    else:
        r.mode("—")
        add_common(repo, r)
        add_graph(repo, r)
    return r
