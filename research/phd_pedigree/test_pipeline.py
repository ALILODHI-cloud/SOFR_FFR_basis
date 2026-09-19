#!/usr/bin/env python3
"""
Offline tests for the parts of the pipeline that do not need network access:
the training-institution inference rule, name normalisation, tiering, and the
representation-ratio arithmetic.

Run:  python3 test_pipeline.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pedigree_pipeline as pp

DATA = pp.DATA


def _aff(name: str, kind: str, years: list[int], country: str = "US") -> dict:
    return {
        "institution": {
            "id": f"https://openalex.org/I{abs(hash(name)) % 10**8}",
            "display_name": name, "type": kind, "country_code": country,
        },
        "years": years,
    }


def test_infer_training_picks_earliest_academic() -> None:
    author = {
        "id": "A1", "display_name": "Sam Early", "works_count": 21,
        "cited_by_count": 400,
        "affiliations": [
            _aff("Pfizer", "company", [2020, 2021, 2022]),
            _aff("University of Iowa", "education", [2012, 2013, 2014]),
            _aff("Stanford University", "education", [2019, 2020]),
        ],
    }
    r = pp.infer_training(author)
    assert r is not None
    assert r["phd_institution"] == "University of Iowa", r
    assert r["first_affiliation_year"] == 2012
    # Stanford starts 7 years later - clearly a later move, not a rival
    # candidate for the PhD, so this record is not ambiguous.
    assert r["ambiguous"] is False, r
    assert r["career_years"] == 10


def test_ambiguity_window_boundary_is_inclusive() -> None:
    """A second academic affiliation exactly TRAINING_WINDOW_YEARS later still
    counts as a rival candidate; one year further out does not."""
    def build(second_year: int) -> dict:
        return {
            "id": "A5", "display_name": "Edge Case", "works_count": 5,
            "cited_by_count": 10,
            "affiliations": [
                _aff("Kansas State University", "education", [2010]),
                _aff("Yale University", "education", [second_year]),
            ],
        }

    at_edge = 2010 + pp.TRAINING_WINDOW_YEARS
    assert pp.infer_training(build(at_edge))["ambiguous"] is True
    assert pp.infer_training(build(at_edge + 1))["ambiguous"] is False


def test_infer_training_flags_phd_postdoc_ambiguity() -> None:
    author = {
        "id": "A2", "display_name": "Ada Overlap", "works_count": 9,
        "cited_by_count": 50,
        "affiliations": [
            _aff("Pfizer", "company", [2023]),
            _aff("Ohio State University", "education", [2015, 2016]),
            _aff("Harvard University", "education", [2017, 2018]),
        ],
    }
    r = pp.infer_training(author)
    assert r["ambiguous"] is True, r
    assert set(r["candidate_institutions"]) == {
        "Ohio State University", "Harvard University"}


def test_infer_training_returns_none_without_academic_history() -> None:
    author = {
        "id": "A3", "display_name": "Ivy Industry", "works_count": 3,
        "cited_by_count": 4,
        "affiliations": [_aff("Pfizer", "company", [2021, 2022])],
    }
    assert pp.infer_training(author) is None


def test_infer_training_ignores_undated_affiliations() -> None:
    author = {
        "id": "A4", "display_name": "No Years", "works_count": 1,
        "cited_by_count": 0,
        "affiliations": [
            _aff("Some University", "education", []),
            _aff("Rutgers University", "education", [2019]),
        ],
    }
    r = pp.infer_training(author)
    assert r["phd_institution"] == "Rutgers University"


def test_norm_inst_collapses_spelling_variants() -> None:
    assert pp._norm_inst("The University of Michigan-Ann Arbor") == \
           pp._norm_inst("University of Michigan at Ann Arbor")
    assert pp._norm_inst("Univ. of Iowa") == pp._norm_inst("University of Iowa")
    assert pp._norm_inst("Mass. Inst. of Technology") == \
           pp._norm_inst("Massachusetts Institute of Technology".replace(
               "Massachusetts", "Mass"))


def test_norm_inst_does_not_collide_distinct_schools() -> None:
    """The failure mode worth guarding: stripping type words or sorting tokens
    merges schools that merely share a place name."""
    distinct = [
        ("Boston University", "Boston College"),
        ("University of Washington", "Washington University in St. Louis"),
        ("University of Miami", "Miami University"),
        ("Indiana University", "Indiana State University"),
    ]
    for a, b in distinct:
        assert pp._norm_inst(a) != pp._norm_inst(b), (a, b)


def test_tier_boundaries() -> None:
    assert pp._tier_of(1) == "T1: top 10"
    assert pp._tier_of(10) == "T1: top 10"
    assert pp._tier_of(11) == "T2: 11-30"
    assert pp._tier_of(150) == "T4: 76-150"
    assert pp._tier_of(9_999) == "T5: 151+"


def test_life_scientist_filter() -> None:
    bio = {"topics": [{"domain": {"display_name": "Life Sciences"}}]}
    it = {"topics": [{"domain": {"display_name": "Physical Sciences"}}]}
    assert pp.is_life_scientist(bio) is True
    assert pp.is_life_scientist(it) is False
    assert pp.is_life_scientist({"topics": []}) is False


def test_analyse_representation_ratio_end_to_end() -> None:
    """
    Fixture: 10 scientists, 6 from a top-10 school and 4 from a rank-100 school.
    The top-10 school awards 20% of national PhDs, the other 80%.

        RR(T1) = 0.6 / 0.2 = 3.0      RR(T4) = 0.4 / 0.8 = 0.5

    This is the arithmetic the whole report turns on, so it is pinned.
    """
    employer = "TestCo"
    authors = []
    for i in range(6):
        authors.append({
            "id": f"E{i}", "display_name": f"Elite {i}",
            "works_count": 30, "cited_by_count": 900,
            "topics": [{"domain": {"display_name": "Life Sciences"}}],
            "affiliations": [
                _aff("TestCo", "company", [2022]),
                _aff("Apex University", "education", [2010 + i]),
            ],
        })
    for i in range(4):
        authors.append({
            "id": f"S{i}", "display_name": f"State {i}",
            "works_count": 12, "cited_by_count": 120,
            "topics": [{"domain": {"display_name": "Health Sciences"}}],
            "affiliations": [
                _aff("TestCo", "company", [2022]),
                _aff("Plains State University", "education", [2011 + i]),
            ],
        })

    slug = pp._slug(employer)
    authors_path = DATA / f"authors_{slug}.json"
    tiers_path = DATA / "tiers_fixture.json"
    base_path = DATA / "sed_biomed_phds_by_institution.csv"
    base_existed = base_path.exists()
    base_backup = base_path.read_text() if base_existed else None

    try:
        authors_path.write_text(json.dumps(
            {"employer": employer, "employer_records": [], "authors": authors}))
        tiers_path.write_text(json.dumps({
            pp._norm_inst("Apex University"): {
                "display_name": "Apex University", "rank": 3,
                "score": 1, "tier": pp._tier_of(3), "source": "fixture"},
            pp._norm_inst("Plains State University"): {
                "display_name": "Plains State University", "rank": 100,
                "score": 1, "tier": pp._tier_of(100), "source": "fixture"},
        }))
        base_path.write_text(
            "institution,doctorates\nApex University,200\n"
            "Plains State University,800\n")

        result = pp.analyse(employer, tier_source="fixture")
        by_tier = {r["tier"]: r for r in result["tiers"]}

        assert result["coverage"]["life_science_authors"] == 10
        assert result["coverage"]["with_dated_academic_affiliation"] == 10
        assert by_tier["T1: top 10"]["n"] == 6
        assert by_tier["T1: top 10"]["representation_ratio"] == 3.0
        assert by_tier["T4: 76-150"]["n"] == 4
        assert by_tier["T4: 76-150"]["representation_ratio"] == 0.5
        lo, hi = by_tier["T1: top 10"]["ci95"]
        assert lo < 0.6 < hi, (lo, hi)
        assert result["seniority_gradient"], result["seniority_gradient"]
    finally:
        for p in (authors_path, tiers_path,
                  DATA / f"analysis_{slug}_fixture.json"):
            p.unlink(missing_ok=True)
        if base_existed:
            base_path.write_text(base_backup)
        else:
            base_path.unlink(missing_ok=True)


def main() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
