"""CLI entry point.  python -m show_its_work.run <command>

  build        (re)build the dataset (Olist if present, else synthetic) + answer key
  investigate  run one investigation and print the memo + telemetry
  demo         run the full scenario suite (flagship, entitlement, abstain, sparse, noise)
  eval         print the evaluation scorecard vs the answer key
  serve        launch the web UI (FastAPI) at http://localhost:8533
"""
from __future__ import annotations

import argparse
import json


def _print_result(r):
    print(r.memo)
    t = r.telemetry
    print("\n" + "-" * 66)
    print(f"telemetry · {t['total_latency_ms']:.0f}ms total | "
          f"LLM calls {t['llm_calls']} ({t['llm_latency_ms']:.0f}ms, {t['input_tokens']+t['output_tokens']} tok, "
          f"${t['estimated_cost_usd']:.5f}) | non-LLM {t['non_llm_calls']} | producers {t['work_by_producer']}")
    print(f"receipts   · {r.verification['citations_valid']}/{r.verification['citations_found']} "
          f"citations resolve, clean={r.verification['clean']}")


def cmd_demo(_args):
    from .engine import investigate
    scenes = [
        ("FLAGSHIP — analyst asks why revenue dropped", "Why did our net revenue drop last week?", "revenue_analyst", None),
        ("ENTITLEMENT — same question, Ops Lead (no finance access)", "Why did our net revenue drop last week?", "ops_lead", None),
        ("AMBIGUOUS — a diffuse move; engine must abstain", "Why did revenue move in mid-March?", "revenue_analyst", ("2024-03-12", "2024-03-22")),
        ("SPARSE — a newly launched window", "How is revenue in the first days?", "revenue_analyst", ("2024-01-02", "2024-01-12")),
        ("NOISE — a quiet week the gate should ignore", "Why did revenue move?", "revenue_analyst", ("2024-02-05", "2024-02-20")),
    ]
    for title, q, persona, window in scenes:
        print("\n" + "#" * 72 + f"\n# {title}\n" + "#" * 72)
        _print_result(investigate(q, persona, window=window))


def cmd_investigate(args):
    from .engine import investigate
    window = tuple(args.window) if args.window else None
    _print_result(investigate(args.question, args.persona, window=window))


def cmd_eval(_args):
    from .eval import print_scorecard
    print_scorecard()


def cmd_build(_args):
    from .data.build import build
    build()


def cmd_serve(args):
    import uvicorn
    uvicorn.run("web.api:app", host="127.0.0.1", port=args.port, app_dir=str(_repo_root()))


def _repo_root():
    from pathlib import Path
    return Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="show_its_work", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    ps = sub.add_parser("serve"); ps.add_argument("--port", type=int, default=8533); ps.set_defaults(fn=cmd_serve)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    sub.add_parser("eval").set_defaults(fn=cmd_eval)
    pi = sub.add_parser("investigate")
    pi.add_argument("question")
    pi.add_argument("--persona", default="revenue_analyst")
    pi.add_argument("--window", nargs=2, metavar=("START", "END"))
    pi.set_defaults(fn=cmd_investigate)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
