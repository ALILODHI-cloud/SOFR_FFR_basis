#!/usr/bin/env python3
"""
Does PhD-institution prestige gate hiring into pharma R&D?

A reproducible pipeline that measures the PhD-institution mix of publishing
scientists at a named employer (default: Pfizer) and compares it against the
national base rate of PhD production, so that "lots of elite graduates work
here" can be separated from "elite graduates are preferentially hired here".

The estimand
------------
For institution tier t, the representation ratio

    RR(t) = share of employer's scientists trained in tier t
            -----------------------------------------------
            share of all US bio/biomedical PhDs awarded by tier t

RR(t) == 1  -> the employer's intake looks exactly like the applicant pool.
RR(t) >  1  -> tier t is over-represented (prestige premium).
RR(t) <  1  -> tier t is under-represented.

Reporting only the numerator is the error that makes every "80% of our staff
went to a top school" claim uninterpretable: top schools also award a large
share of the doctorates.

Data sources (all open, no ToS-violating scraping)
--------------------------------------------------
1. OpenAlex (CC0, https://api.openalex.org) - author records carry an
   `affiliations` history of {institution, years}, which lets the training
   institution be reconstructed from an author's earliest academic affiliation.
2. NSF NCSES Survey of Earned Doctorates - doctorates by institution and field,
   the denominator. Not an API; download the data table once (see README).
3. NIH RePORTER (optional, https://api.reporter.nih.gov) - award totals per
   organisation, used as a bioscience-specific prestige axis so that results do
   not depend on a commercial ranking.

LinkedIn is deliberately not used: scraping it breaches its terms, and its
self-reported education fields are unverifiable.

Usage
-----
    python3 pedigree_pipeline.py fetch    --employer Pfizer
    python3 pedigree_pipeline.py tier
    python3 pedigree_pipeline.py analyse  --employer Pfizer
    python3 pedigree_pipeline.py validate --employer Pfizer --n 100

Requires network egress to api.openalex.org (and api.reporter.nih.gov for the
optional NIH tiering).
"""

from __future__ import annotations

import argparse
import csv
import functools
import json
import os
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

import requests

DATA = Path(__file__).parent / "data"
OPENALEX = "https://api.openalex.org"
REPORTER = "https://api.reporter.nih.gov/v2/projects/search"

# OpenAlex asks for an email to route you to the faster "polite pool".
MAILTO = os.environ.get("OPENALEX_MAILTO", "")

# Bioscience-relevant OpenAlex topic domains. Used to keep the analysis to
# scientists doing life-science work rather than, say, corporate IT staff who
# happen to have co-authored a paper.
LIFE_SCIENCE_DOMAINS = {"Life Sciences", "Health Sciences"}

# An author's first publications can appear during a PhD, but also during an
# undergraduate project or a masters. Affiliations that start within this many
# years of the very first publication are treated as candidate training sites.
TRAINING_WINDOW_YEARS = 4

# Tier cut points, applied to a prestige rank (1 = strongest).
TIERS = [
    ("T1: top 10", 1, 10),
    ("T2: 11-30", 11, 30),
    ("T3: 31-75", 31, 75),
    ("T4: 76-150", 76, 150),
    ("T5: 151+", 151, 10_000),
]


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _get(url: str, params: dict[str, Any] | None = None, tries: int = 5) -> dict:
    """GET with exponential backoff. OpenAlex rate-limits rather than errors."""
    params = dict(params or {})
    if MAILTO:
        params["mailto"] = MAILTO
    delay = 2.0
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 429:
                raise requests.HTTPError("429 rate limited")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == tries - 1:
                raise
            print(f"  retry {attempt + 1}/{tries} after {exc}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")


def _paged(endpoint: str, filt: str, select: str,
           sort: str | None = None) -> Iterator[dict]:
    """Cursor-paginate an OpenAlex list endpoint. Cursor paging has no 10k cap."""
    cursor = "*"
    seen = 0
    while cursor:
        params = {"filter": filt, "per-page": 200, "cursor": cursor,
                  "select": select}
        if sort:
            params["sort"] = sort
        payload = _get(f"{OPENALEX}/{endpoint}", params)
        results = payload.get("results", [])
        yield from results
        seen += len(results)
        cursor = payload.get("meta", {}).get("next_cursor")
        if not results:
            break
        print(f"  ...{seen} {endpoint}", file=sys.stderr)


# --------------------------------------------------------------------------
# Step 1 - resolve the employer
# --------------------------------------------------------------------------

def resolve_employer(name: str) -> list[dict]:
    """
    Find every OpenAlex institution record for an employer.

    Large pharma appears under many records (`Pfizer`, `Pfizer UK`, `Pfizer La
    Jolla`, acquired subsidiaries). Missing them silently shrinks the sample and
    biases it toward whichever site happens to use the canonical string, so all
    company-type matches are unioned.
    """
    payload = _get(
        f"{OPENALEX}/institutions",
        {
            "search": name,
            "per-page": 200,
            "select": "id,display_name,ror,type,country_code,works_count",
        },
    )
    needle = name.lower()
    matches = [
        inst
        for inst in payload.get("results", [])
        if inst.get("type") == "company" and needle in inst["display_name"].lower()
    ]
    if not matches:
        raise SystemExit(f"No company-type OpenAlex institution matched {name!r}")
    matches.sort(key=lambda i: -i.get("works_count", 0))
    return matches


# --------------------------------------------------------------------------
# Step 2 - pull the employer's publishing scientists
# --------------------------------------------------------------------------

def fetch_employees(name: str) -> list[dict]:
    employers = resolve_employer(name)
    for e in employers:
        print(f"employer record: {e['display_name']} ({e['id']}) "
              f"works={e.get('works_count')}", file=sys.stderr)
    ids = "|".join(e["id"].rsplit("/", 1)[-1] for e in employers)

    authors: dict[str, dict] = {}
    for author in _paged(
        "authors",
        f"last_known_institutions.id:{ids}",
        "id,display_name,works_count,cited_by_count,affiliations,topics,counts_by_year",
    ):
        authors[author["id"]] = author

    out = DATA / f"authors_{_slug(name)}.json"
    out.write_text(json.dumps(
        {"employer": name, "employer_records": employers,
         "authors": list(authors.values())}, indent=1))
    print(f"wrote {len(authors)} authors -> {out}")
    return list(authors.values())


def _slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")


# --------------------------------------------------------------------------
# Step 3 - infer where the scientist trained
# --------------------------------------------------------------------------

def is_life_scientist(author: dict) -> bool:
    for topic in author.get("topics", [])[:5]:
        domain = (topic.get("domain") or {}).get("display_name")
        if domain in LIFE_SCIENCE_DOMAINS:
            return True
    return False


def infer_training(author: dict) -> dict | None:
    """
    Reconstruct the training institution from the affiliation history.

    Rule: among academic (education-type) affiliations, take the one whose
    earliest year is earliest overall. Any other academic affiliation starting
    within TRAINING_WINDOW_YEARS is recorded too, because a PhD and an
    immediately following postdoc are not reliably separable from publication
    metadata alone -- so `ambiguous` flags the cases where the PhD institution
    could be either, and the analysis is reported with and without them.

    Returns None when the history carries no dated academic affiliation, which
    is itself a reportable quantity (coverage).
    """
    academic: list[tuple[int, str, str, str]] = []
    for aff in author.get("affiliations", []):
        inst = aff.get("institution") or {}
        years = [y for y in (aff.get("years") or []) if isinstance(y, int)]
        if not years or inst.get("type") != "education":
            continue
        academic.append((min(years), inst.get("id", ""),
                         inst.get("display_name", ""), inst.get("country_code") or ""))
    if not academic:
        return None

    academic.sort()
    first_year, inst_id, inst_name, country = academic[0]
    candidates = [a for a in academic if a[0] <= first_year + TRAINING_WINDOW_YEARS]

    all_years = [
        y
        for aff in author.get("affiliations", [])
        for y in (aff.get("years") or [])
        if isinstance(y, int)
    ]
    return {
        "author_id": author["id"],
        "name": author["display_name"],
        "phd_institution_id": inst_id,
        "phd_institution": inst_name,
        "country": country,
        "first_affiliation_year": first_year,
        "career_start": min(all_years) if all_years else first_year,
        "career_years": (max(all_years) - min(all_years)) if all_years else 0,
        "works_count": author.get("works_count", 0),
        "cited_by_count": author.get("cited_by_count", 0),
        "ambiguous": len(candidates) > 1,
        "candidate_institutions": [c[2] for c in candidates],
    }


# --------------------------------------------------------------------------
# Step 4 - tier institutions on a bioscience-specific prestige axis
# --------------------------------------------------------------------------

def build_tiers(source: str = "openalex", top_n: int = 400) -> dict[str, dict]:
    """
    Rank US doctorate-granting institutions by bioscience research strength.

    Two independent axes, because any single ranking imports its own biases:

      openalex - count of life/health-science works, 2015 onward. Cheap, global,
                 and no commercial ranking in the loop.
      nih      - total NIH award dollars. Closer to what a bioscience PhD's
                 training environment actually looks like, US-only.

    A finding that survives both axes is about prestige; one that appears under
    only one is about that ranking.
    """
    if source == "nih":
        ranks = _nih_org_totals()
    else:
        ranks = _openalex_institution_strength(top_n)

    ordered = sorted(ranks.items(), key=lambda kv: -kv[1])
    table: dict[str, dict] = {}
    for i, (name, score) in enumerate(ordered, start=1):
        table[_norm_inst(name)] = {
            "display_name": name, "rank": i, "score": score,
            "tier": _tier_of(i), "source": source,
        }
    out = DATA / f"tiers_{source}.json"
    out.write_text(json.dumps(table, indent=1))
    print(f"ranked {len(table)} institutions ({source}) -> {out}")
    return table


def _tier_of(rank: int) -> str:
    for label, lo, hi in TIERS:
        if lo <= rank <= hi:
            return label
    return TIERS[-1][0]


def _life_science_domain_ids() -> str:
    """Resolve OpenAlex domain ids at runtime rather than hardcoding them."""
    payload = _get(f"{OPENALEX}/domains", {"per-page": 50})
    ids = [
        d["id"].rsplit("/", 1)[-1]
        for d in payload.get("results", [])
        if d.get("display_name") in LIFE_SCIENCE_DOMAINS
    ]
    if not ids:
        raise SystemExit("could not resolve OpenAlex life-science domain ids")
    return "|".join(ids)


def _openalex_institution_strength(top_n: int, since: int = 2015) -> dict[str, float]:
    """
    Score US doctorate-granting institutions by *life-science* output.

    Total works_count would rank institutions on all fields at once, which is
    the wrong axis for a bioscience question -- a strong engineering school
    would outrank a strong medical one. So the candidate set is drawn by overall
    size (sorted, not arbitrary), then each candidate is re-scored on
    life/health-science work only.
    """
    domains = _life_science_domain_ids()

    candidates: list[dict] = []
    for inst in _paged(
        "institutions",
        "type:education,country_code:US",
        "id,display_name,works_count",
        sort="works_count:desc",
    ):
        candidates.append(inst)
        if len(candidates) >= top_n:
            break

    scores: dict[str, float] = {}
    for i, inst in enumerate(candidates, start=1):
        short = inst["id"].rsplit("/", 1)[-1]
        payload = _get(
            f"{OPENALEX}/works",
            {
                "filter": (f"authorships.institutions.lineage:{short},"
                           f"primary_topic.domain.id:{domains},"
                           f"publication_year:>{since - 1},type:article"),
                "per-page": 1,
            },
        )
        scores[inst["display_name"]] = payload.get("meta", {}).get("count", 0)
        if i % 25 == 0:
            print(f"  ...scored {i}/{len(candidates)} institutions", file=sys.stderr)
        time.sleep(0.12)  # stay under the 10 req/s courtesy limit
    return scores


def _nih_org_totals(fiscal_year: int = 2023) -> dict[str, float]:
    """Sum NIH award dollars per organisation for one fiscal year."""
    totals: Counter[str] = Counter()
    offset, limit = 0, 500
    while True:
        body = {
            "criteria": {"fiscal_years": [fiscal_year],
                         "org_countries": ["UNITED STATES"]},
            "include_fields": ["OrgName", "AwardAmount"],
            "offset": offset, "limit": limit,
        }
        r = requests.post(REPORTER, json=body, timeout=120)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("results", [])
        for row in rows:
            if row.get("org_name") and row.get("award_amount"):
                totals[row["org_name"].title()] += float(row["award_amount"])
        offset += limit
        print(f"  ...{offset} NIH projects", file=sys.stderr)
        if len(rows) < limit or offset >= 14_500:  # RePORTER offset ceiling
            break
        time.sleep(0.5)
    return dict(totals)


# Abbreviations are folded to a canonical long form; institution *type* words
# are kept, because dropping them collides distinct schools that share a place
# name ("Boston University" vs "Boston College", "University of Washington" vs
# "Washington University"). Token order is preserved for the same reason.
_TYPE_CANON = {
    "univ": "university", "universities": "university", "universite": "university",
    "inst": "institute", "institutes": "institute", "institut": "institute",
    "coll": "college", "ctr": "center", "centre": "center",
    "sch": "school", "tech": "technology", "st": "saint", "ste": "saint",
    "med": "medical", "hosp": "hospital", "grad": "graduate",
}
_DROP_TOKENS = {"the", "of", "at", "in", "and", "for", "a", "an"}


@functools.lru_cache(maxsize=1)
def _aliases() -> dict[str, str]:
    """
    Optional hand-maintained variant -> canonical map.

    Fuzzy matching cannot be made perfect, so the pipeline reports its misses
    (`top_unmatched_institutions`) and lets them be fixed explicitly here rather
    than pretending the normaliser caught everything.
    """
    path = DATA / "institution_aliases.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            if row.get("variant") and row.get("canonical"):
                out[row["variant"].strip().lower()] = row["canonical"].strip()
    return out


def _norm_inst(name: str) -> str:
    """Collapse the spelling variants that otherwise split one institution."""
    name = _aliases().get(name.strip().lower(), name)
    tokens = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]
    return " ".join(
        _TYPE_CANON.get(t, t) for t in tokens if t not in _DROP_TOKENS
    )


# --------------------------------------------------------------------------
# Step 5 - the denominator: PhDs actually awarded, by institution
# --------------------------------------------------------------------------

def load_base_rates() -> dict[str, float]:
    """
    Load bio/biomedical doctorates awarded per institution.

    Expects data/sed_biomed_phds_by_institution.csv with columns
    institution,doctorates - see README for the exact NSF table to download.
    Without it only raw shares can be computed, and raw shares cannot answer
    the question.
    """
    path = DATA / "sed_biomed_phds_by_institution.csv"
    if not path.exists():
        return {}
    rates: dict[str, float] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            try:
                rates[_norm_inst(row["institution"])] = float(row["doctorates"])
            except (KeyError, ValueError):
                continue
    return rates


# --------------------------------------------------------------------------
# Step 6 - analysis
# --------------------------------------------------------------------------

def analyse(employer: str, tier_source: str = "openalex",
            drop_ambiguous: bool = False, us_only: bool = True) -> dict:
    blob = json.loads((DATA / f"authors_{_slug(employer)}.json").read_text())
    authors = blob["authors"]
    tiers = json.loads((DATA / f"tiers_{tier_source}.json").read_text())
    base = load_base_rates()

    life = [a for a in authors if is_life_scientist(a)]
    records = [r for r in (infer_training(a) for a in life) if r]
    if us_only:
        records = [r for r in records if r["country"] == "US"]
    if drop_ambiguous:
        records = [r for r in records if not r["ambiguous"]]

    coverage = {
        "authors_total": len(authors),
        "life_science_authors": len(life),
        "with_dated_academic_affiliation": len(records),
        "ambiguous_phd_vs_postdoc": sum(r["ambiguous"] for r in records),
    }

    tier_counts: Counter[str] = Counter()
    unmatched: Counter[str] = Counter()
    for r in records:
        hit = tiers.get(_norm_inst(r["phd_institution"]))
        if hit:
            r["tier"], r["prestige_rank"] = hit["tier"], hit["rank"]
            tier_counts[hit["tier"]] += 1
        else:
            r["tier"], r["prestige_rank"] = "unranked", None
            tier_counts["unranked"] += 1
            unmatched[r["phd_institution"]] += 1

    n = sum(tier_counts.values()) or 1
    base_by_tier: Counter[str] = Counter()
    for norm_name, count in base.items():
        hit = tiers.get(norm_name)
        base_by_tier[hit["tier"] if hit else "unranked"] += count
    base_total = sum(base_by_tier.values())

    rows = []
    for label, _, _ in TIERS + [("unranked", 0, 0)]:
        employer_share = tier_counts.get(label, 0) / n
        base_share = (base_by_tier.get(label, 0) / base_total) if base_total else None
        rows.append({
            "tier": label,
            "n": tier_counts.get(label, 0),
            "employer_share": round(employer_share, 4),
            "phd_production_share": round(base_share, 4) if base_share else None,
            "representation_ratio": (round(employer_share / base_share, 3)
                                     if base_share else None),
            "ci95": _bootstrap_share_ci(records, label),
        })

    seniority = _seniority_gradient(records)
    result = {
        "employer": employer,
        "tier_source": tier_source,
        "coverage": coverage,
        "tiers": rows,
        "seniority_gradient": seniority,
        "top_unmatched_institutions": unmatched.most_common(25),
        "caveats": CAVEATS,
    }
    out = DATA / f"analysis_{_slug(employer)}_{tier_source}.json"
    out.write_text(json.dumps(result, indent=1))
    _print_table(result)
    return result


def _bootstrap_share_ci(records: list[dict], label: str,
                        draws: int = 2000) -> list[float] | None:
    """Percentile bootstrap over authors - the sample is one draw, not a census."""
    if not records:
        return None
    flags = [1.0 if r.get("tier") == label else 0.0 for r in records]
    n = len(flags)
    shares = []
    rng = random.Random(0)
    for _ in range(draws):
        shares.append(sum(rng.choice(flags) for _ in range(n)) / n)
    shares.sort()
    return [round(shares[int(0.025 * draws)], 4), round(shares[int(0.975 * draws)], 4)]


def _seniority_gradient(records: list[dict]) -> list[dict]:
    """
    Does the prestige mix shift with career stage?

    If prestige is a hiring filter it should show up at intake. If it instead
    shows up only among the most senior, that is promotion or survivorship, and
    it is a different claim about a different decision.
    """
    buckets: dict[str, list[int]] = defaultdict(list)
    for r in records:
        if r.get("prestige_rank") is None:
            continue
        years = r["career_years"]
        key = ("early (<10y)" if years < 10
               else "mid (10-20y)" if years < 20
               else "senior (20y+)")
        buckets[key].append(r["prestige_rank"])
    return [
        {"stage": k, "n": len(v),
         "median_prestige_rank": statistics.median(v),
         "share_top10": round(sum(1 for x in v if x <= 10) / len(v), 3)}
        for k, v in sorted(buckets.items())
    ]


def _print_table(result: dict) -> None:
    c = result["coverage"]
    print(f"\n{result['employer']} - PhD institution mix "
          f"(tiering: {result['tier_source']})")
    print(f"  {c['life_science_authors']} life-science authors; "
          f"{c['with_dated_academic_affiliation']} with usable training history "
          f"({c['ambiguous_phd_vs_postdoc']} PhD/postdoc-ambiguous)")
    print(f"\n  {'tier':<14}{'n':>6}{'share':>9}{'PhDs awarded':>14}{'RR':>8}")
    for row in result["tiers"]:
        rr = f"{row['representation_ratio']:.2f}" if row["representation_ratio"] else "-"
        bs = f"{row['phd_production_share']:.3f}" if row["phd_production_share"] else "-"
        print(f"  {row['tier']:<14}{row['n']:>6}{row['employer_share']:>9.3f}"
              f"{bs:>14}{rr:>8}")
    print("\n  seniority gradient:")
    for s in result["seniority_gradient"]:
        print(f"    {s['stage']:<14} n={s['n']:<5} "
              f"median rank={s['median_prestige_rank']:<7} "
              f"top-10 share={s['share_top10']}")


# --------------------------------------------------------------------------
# Step 7 - validate the inference rule
# --------------------------------------------------------------------------

def validate(employer: str, n: int = 100) -> Path:
    """
    Emit a random sample for hand-checking against public CVs.

    The whole result rests on "earliest dated academic affiliation == PhD
    institution". That assumption has a measurable error rate, and a pipeline
    that never measures it is reporting an unknown quantity. Fill in the
    `true_phd_institution` column from public CVs, lab pages or dissertation
    records, then compute precision.
    """
    blob = json.loads((DATA / f"authors_{_slug(employer)}.json").read_text())
    records = [r for r in (infer_training(a) for a in blob["authors"]) if r]
    sample = random.Random(1).sample(records, min(n, len(records)))
    path = DATA / f"validation_{_slug(employer)}.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["author_id", "name", "inferred_phd_institution",
                    "first_affiliation_year", "ambiguous",
                    "candidates", "true_phd_institution", "correct"])
        for r in sample:
            w.writerow([r["author_id"], r["name"], r["phd_institution"],
                         r["first_affiliation_year"], r["ambiguous"],
                         "; ".join(r["candidate_institutions"]), "", ""])
    print(f"wrote {len(sample)} rows to hand-label -> {path}")
    return path


CAVEATS = [
    "Covers only scientists who publish under the employer's affiliation. "
    "Non-publishing roles (process development, regulatory, much of clinical "
    "operations) are invisible, and they are a large share of pharma R&D "
    "headcount.",
    "Affiliation-year coverage in OpenAlex thins out before roughly 2010, so "
    "senior staff are under-sampled relative to junior staff.",
    "An undergraduate co-authorship can precede the PhD affiliation and would "
    "be misread as the training institution.",
    "PhD and immediately-following postdoc are not reliably separable; see the "
    "ambiguous flag and re-run with --drop-ambiguous.",
    "Institution name matching is fuzzy; check top_unmatched_institutions "
    "before trusting the unranked bucket.",
    "Survivorship: this measures who is employed now, not who was hired and "
    "left, so it cannot separate hiring from retention.",
]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["fetch", "tier", "analyse", "validate"])
    p.add_argument("--employer", default="Pfizer")
    p.add_argument("--tier-source", default="openalex", choices=["openalex", "nih"])
    p.add_argument("--drop-ambiguous", action="store_true")
    p.add_argument("--include-non-us", action="store_true")
    p.add_argument("--n", type=int, default=100)
    args = p.parse_args()

    DATA.mkdir(exist_ok=True)
    if args.command == "fetch":
        fetch_employees(args.employer)
    elif args.command == "tier":
        build_tiers(args.tier_source)
    elif args.command == "analyse":
        analyse(args.employer, args.tier_source,
                drop_ambiguous=args.drop_ambiguous,
                us_only=not args.include_non_us)
    elif args.command == "validate":
        validate(args.employer, args.n)


if __name__ == "__main__":
    main()
