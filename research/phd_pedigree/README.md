# Does PhD-institution ranking matter for a biosciences PhD?

Asks whether the prestige of your PhD institution gates hiring into pharma R&D,
with Pfizer as the worked case, and contrasts it against economics — where the
academic market is far more prestige-stratified.

**Deliverable:** [`phd_prestige_biosciences.pdf`](phd_prestige_biosciences.pdf)

## Contents

| File | What it is |
|---|---|
| `phd_prestige_biosciences.pdf` | The report: evidence review, mechanism, and the measurement design |
| `pedigree_pipeline.py` | The systematic measurement pipeline (needs network egress) |
| `build_report.py` | Regenerates the charts and the PDF |
| `test_pipeline.py` | Offline tests for the inference and ratio logic — `python3 test_pipeline.py` |
| `charts/` | Generated chart images |
| `data/` | Pipeline inputs and outputs (gitignored except the alias file) |

## The measurement question

The trap in this question is the denominator. "Most of our scientists went to a
top-30 school" tells you nothing on its own, because top-30 schools also award a
large share of all doctorates. So the estimand is a **representation ratio** per
institution tier:

```
RR(tier) = employer's share of scientists trained in that tier
           ------------------------------------------------------
           that tier's share of US bio/biomedical doctorates awarded
```

`RR = 1` means the employer's intake looks exactly like the pool it draws from —
no prestige premium. `RR > 1` is over-representation, and its size is the answer.

## Running it

Needs outbound HTTPS to `api.openalex.org` (and `api.reporter.nih.gov` for the
NIH tiering axis). It could not be run in the environment that produced the
report, which allows egress to package registries only.

```bash
pip install requests matplotlib reportlab
export OPENALEX_MAILTO="you@example.com"   # OpenAlex's faster "polite pool"

python3 pedigree_pipeline.py fetch    --employer Pfizer     # ~minutes
python3 pedigree_pipeline.py tier     --tier-source openalex
python3 pedigree_pipeline.py analyse  --employer Pfizer
python3 pedigree_pipeline.py validate --employer Pfizer --n 100
```

Then re-run with `--tier-source nih` and report only what survives both axes,
and with `--drop-ambiguous` to exclude records where PhD and postdoc cannot be
separated.

### The denominator file (required for representation ratios)

Not an API. Download once:

1. Go to NSF NCSES, *Doctorate Recipients from U.S. Universities* data tables
   (<https://ncses.nsf.gov/surveys/earned-doctorates/2023>).
2. Take the table of **doctorate recipients by doctorate-granting institution
   and broad field of study** (table 7-3 in the NSF 24-336 release), and keep
   the life-sciences column.
3. Save as `data/sed_biomed_phds_by_institution.csv` with headers
   `institution,doctorates`.

Without it the pipeline still reports raw tier shares, but raw shares cannot
answer the question.

### Comparators

One company's number is not a finding. Run the same pipeline across employers to
get a distribution — the spread is what tells you whether pedigree screening is
an industry norm or one company's house style:

```bash
for co in Pfizer Merck AstraZeneca Genentech Amgen Regeneron Vertex Moderna; do
  python3 pedigree_pipeline.py fetch   --employer "$co"
  python3 pedigree_pipeline.py analyse --employer "$co"
done
```

## Method in brief

Training institution is reconstructed from OpenAlex author records, which carry
a dated affiliation history: the earliest education-type affiliation stands in
for the PhD institution. Institutions are tiered on two independent axes —
life-science publication output and NIH award dollars — so a finding can be
checked against the choice of ranking.

OpenAlex is CC0 with a public API. **LinkedIn is deliberately not used**:
scraping it breaches its terms, and its self-reported education fields are
unverifiable.

## Known limitations

Reported by `analyse` rather than buried, and the report's conclusion is
conditional on them:

- **Publication bias.** Only scientists publishing under the employer's
  affiliation are visible. Process development, regulatory and much of clinical
  operations are not — plausibly the roles where pedigree matters least, which
  would bias the measured premium *upward*.
- **Thin affiliation history before ~2010**, so senior staff are under-sampled.
- **PhD vs postdoc** are not reliably separable from publication metadata; see
  the `ambiguous` flag.
- **Undergraduate co-authorship** can precede the PhD and be misread as the
  training institution. `validate` measures how often.
- **Survivorship.** Measures who is employed now, not who was hired, so it
  cannot by itself separate hiring from retention.
- **Fuzzy institution matching.** Check `top_unmatched_institutions` in the
  analysis output and add fixes to `data/institution_aliases.csv`
  (`variant,canonical`).

## Regenerating the report

```bash
python3 test_pipeline.py      # 10 offline tests
python3 build_report.py       # charts + PDF
```
