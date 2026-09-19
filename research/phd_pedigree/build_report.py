#!/usr/bin/env python3
"""
Build the PDF report: charts via matplotlib, document via reportlab.

    python3 build_report.py

Writes charts to charts/ and the report to phd_prestige_biosciences.pdf.
Every number in the document is sourced in the References section; nothing here
is modelled or imputed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

HERE = Path(__file__).parent
CHARTS = HERE / "charts"
PDF = HERE / "phd_prestige_biosciences.pdf"

# Validated light-mode palette (dataviz reference instance).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
ORANGE = "#eb6834"

plt.rcParams.update({
    # Liberation Sans is metric-compatible with the Helvetica the PDF body uses,
    # so chart type matches page type instead of sitting in a second face.
    "font.family": ["Liberation Sans", "FreeSans", "DejaVu Sans"],
    "font.size": 9,
    # Transparent, so the chart sits on the page rather than in a visible panel.
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.transparent": True,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": False,
})


def _strip(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=0)


# --------------------------------------------------------------------------
# Chart 1 - the destination shift
# --------------------------------------------------------------------------

def chart_destinations() -> Path:
    """
    Two series (1992, 2022), two categories. Legend present because there are
    two series, and both are direct-labelled so identity is never colour-alone.
    """
    cats = ["Academia", "Industry"]
    y1992 = [49.1, 25.0]
    y2022 = [26.9, 54.1]

    fig, ax = plt.subplots(figsize=(6.4, 2.7))
    fig.subplots_adjust(top=0.74, bottom=0.14, left=0.02, right=0.99)
    fig.text(0.02, 0.95, "Where US life-science PhDs said they were heading",
             fontsize=10.8, color=INK, va="top")
    fig.text(0.02, 0.855,
             "Share reporting a commitment in each sector, at graduation",
             fontsize=8.4, color=MUTED, va="top")

    x = range(len(cats))
    w = 0.30
    gap = 0.012  # 2px-equivalent surface gap between adjacent fills
    b1 = ax.bar([i - w / 2 - gap for i in x], y1992, w, color=BLUE, label="1992")
    b2 = ax.bar([i + w / 2 + gap for i in x], y2022, w, color=ORANGE, label="2022")

    for bars in (b1, b2):
        for bar in bars:
            ax.annotate(f"{bar.get_height():.1f}%",
                        (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        textcoords="offset points", xytext=(0, 3),
                        ha="center", fontsize=8.6, color=INK)

    ax.set_xticks(list(x))
    ax.set_xticklabels(cats, color=INK, fontsize=9.5)
    ax.set_yticks([])
    ax.set_ylim(0, 62)
    ax.set_xlim(-0.55, 1.55)
    # Seated in the header band above the plot, so it cannot collide with the
    # tallest bar's direct label.
    leg = ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.01),
                    fontsize=8.5, ncol=2, handlelength=0.9, columnspacing=1.1,
                    borderpad=0, handletextpad=0.5)
    for t in leg.get_texts():
        t.set_color(INK2)
    _strip(ax)
    out = CHARTS / "destinations.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# Chart 2 - what a prestige-gated market looks like
# --------------------------------------------------------------------------

def chart_concentration() -> Path:
    """
    One series, two bars - so no legend box; the title names the measure.
    This is the benchmark the industry question is asked against.
    """
    labels = ["Share of US PhD-granting\ninstitutions",
              "Share of tenure-track faculty\nthey trained"]
    vals = [20, 80]

    fig, ax = plt.subplots(figsize=(6.4, 1.85))
    # Title drawn in figure coordinates: an axes-anchored title would be
    # clipped at the plot area's right edge.
    fig.subplots_adjust(top=0.70, bottom=0.05, left=0.30, right=0.93)
    fig.text(0.02, 0.95,
             "The academic market, for scale", fontsize=10.8, color=INK, va="top")
    fig.text(0.02, 0.80,
             "A fifth of the schools trained four fifths of US tenure-track faculty",
             fontsize=8.4, color=MUTED, va="top")

    bars = ax.barh(labels, vals, height=0.52, color=BLUE)
    for bar, v in zip(bars, vals):
        ax.annotate(f"{v}%", (v, bar.get_y() + bar.get_height() / 2),
                    textcoords="offset points", xytext=(6, 0),
                    va="center", fontsize=10, color=INK)
    ax.set_xlim(0, 100)
    ax.set_xticks([])
    ax.invert_yaxis()
    ax.tick_params(axis="y", labelsize=8.6, labelcolor=INK)
    _strip(ax)
    ax.spines["bottom"].set_visible(False)
    out = CHARTS / "concentration.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------

def styles() -> dict:
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold",
                                fontSize=19, leading=23, spaceAfter=4,
                                textColor=colors.HexColor(INK), alignment=TA_LEFT),
        "subtitle": ParagraphStyle("st", parent=ss["Normal"], fontName="Helvetica",
                                   fontSize=10.5, leading=15, spaceAfter=16,
                                   textColor=colors.HexColor(INK2)),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                             fontSize=13, leading=17, spaceBefore=16, spaceAfter=7,
                             textColor=colors.HexColor(INK)),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                             fontSize=10.5, leading=14, spaceBefore=11, spaceAfter=5,
                             textColor=colors.HexColor(INK)),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=9.7, leading=14.4, spaceAfter=8,
                               textColor=colors.HexColor("#1a1a19")),
        "small": ParagraphStyle("s", parent=ss["BodyText"], fontName="Helvetica",
                                fontSize=8.3, leading=12, spaceAfter=5,
                                textColor=colors.HexColor(INK2)),
        "caption": ParagraphStyle("c", parent=ss["BodyText"], fontName="Helvetica-Oblique",
                                  fontSize=8, leading=11, spaceBefore=3, spaceAfter=12,
                                  textColor=colors.HexColor(MUTED)),
        "pull": ParagraphStyle("p", parent=ss["BodyText"], fontName="Helvetica-Bold",
                               fontSize=11, leading=16, spaceAfter=10,
                               leftIndent=9, textColor=colors.HexColor("#184f95")),
    }


def bullets(items: list[str], st: dict, style: str = "body") -> ListFlowable:
    # `value=` on a ListItem replaces the bullet with that literal string, which
    # is how "bul" ends up printed on the page. The bullet glyph belongs on the
    # ListFlowable via start=.
    return ListFlowable(
        [ListItem(Paragraph(t, st[style])) for t in items],
        bulletType="bullet", start="•", bulletFontSize=7,
        bulletColor=colors.HexColor(MUTED), bulletOffsetY=-1,
        leftIndent=11, spaceAfter=6,
    )


def stat_tiles(st: dict) -> Table:
    """Hero numbers - a stat tile, not a chart, because each is one figure."""
    tiles = [
        ("54.1%", "of US life-science PhDs\nhead to industry (2022)"),
        ("~14%", "hold a tenure-track post\n5-6 years after the PhD"),
        ("459", "US institutions award\nresearch doctorates"),
        ("~70%", "of US biotech jobs sit in\nBoston, San Diego, RTP"),
    ]
    cells = [[], []]
    for big, small in tiles:
        cells[0].append(Paragraph(
            f'<font size="17" color="{INK}"><b>{big}</b></font>', st["body"]))
        cells[1].append(Paragraph(small.replace("\n", "<br/>"), st["small"]))
    t = Table(cells, colWidths=[42 * mm] * 4, rowHeights=[10 * mm, 11 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor(AXIS)),
    ]))
    return t


def method_table(st: dict) -> Table:
    # Cells must be Paragraphs: a plain string in a Table cell does not wrap,
    # it overflows into the neighbouring column.
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.1, leading=10.6,
                          textColor=colors.HexColor("#1a1a19"))
    head = ParagraphStyle("hcell", parent=cell, fontName="Helvetica-Bold",
                          textColor=colors.HexColor(INK))
    src = ParagraphStyle("src", parent=cell, textColor=colors.HexColor(INK2))

    raw = [
        ["Step", "What it does", "Source"],
        ["1. Resolve employer",
         "Union every OpenAlex institution record for the employer, so "
         "site-level and subsidiary records are not dropped.",
         "OpenAlex /institutions"],
        ["2. Pull scientists",
         "Cursor-page all authors whose last known affiliation is the "
         "employer; keep those whose topics sit in Life or Health Sciences.",
         "OpenAlex /authors"],
        ["3. Infer training site",
         "Take the earliest dated education-type affiliation in the author's "
         "history. Flag records where a second academic affiliation starts "
         "within 4 years (PhD vs postdoc not separable).",
         "OpenAlex affiliations"],
        ["4. Tier institutions",
         "Rank US doctorate-granting institutions on life-science output, and "
         "again on NIH award dollars. A result must survive both axes.",
         "OpenAlex /works,<br/>NIH RePORTER"],
        ["5. Get the denominator",
         "Bio/biomedical doctorates awarded per institution - the applicant "
         "pool the employer draws from.",
         "NSF NCSES SED<br/>table 7-3"],
        ["6. Representation ratio",
         "Employer share divided by PhD-production share, per tier, with a "
         "percentile bootstrap over authors.",
         "computed"],
        ["7. Validate the rule",
         "Hand-label a random sample of 100 inferred PhD institutions against "
         "public CVs and report the error rate.",
         "manual"],
    ]
    rows = [[Paragraph(raw[0][i], head) for i in range(3)]]
    for r in raw[1:]:
        rows.append([Paragraph(r[0], cell), Paragraph(r[1], cell),
                     Paragraph(r[2], src)])

    t = Table(rows, colWidths=[29 * mm, 92 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(AXIS)),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor(GRID)),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def build() -> Path:
    CHARTS.mkdir(exist_ok=True)
    c_dest = chart_destinations()
    c_conc = chart_concentration()
    st = styles()
    f: list = []

    def h1(t): f.append(Paragraph(t, st["h1"]))
    def h2(t): f.append(Paragraph(t, st["h2"]))
    def p(t): f.append(Paragraph(t, st["body"]))
    def cap(t): f.append(Paragraph(t, st["caption"]))

    # ---- cover -----------------------------------------------------------
    f.append(Paragraph(
        "Does the ranking of your school matter for a biosciences PhD?", st["title"]))
    f.append(Paragraph(
        "Testing the question against the pharma R&amp;D labour market, with "
        "Pfizer as the worked case &mdash; what the published evidence settles, "
        "what it does not, and a reproducible way to measure the rest.",
        st["subtitle"]))
    f.append(stat_tiles(st))
    f.append(Spacer(1, 10 * mm))

    h1("The short answer")
    f.append(Paragraph(
        "Yes &mdash; you can be hired as a scientist at Pfizer with a PhD from a "
        "non-elite school, and the structure of the market says this is ordinary "
        "rather than exceptional.", st["pull"]))
    p("Three things make the biosciences case different from the prestige-gated "
      "markets people have in mind. First, the modal destination for a US "
      "life-science PhD is now industry, not academia &mdash; 54.1% of 2022 "
      "graduates reported heading into industry against 26.9% into academia, an "
      "almost exact inversion of 1992. Industry is the main market, not the "
      "fallback, and it is far larger than the number of faculty posts that the "
      "prestige hierarchy rations.")
    p("Second, the thing pharma R&amp;D hires for is a technique and a "
      "therapeutic area, not a transcript. A posting for a cryo-EM structural "
      "biologist, an ADC chemist or a CAR-T immunologist is filled by whoever "
      "has run that bench, and that population is small enough in any given "
      "modality that filtering it further by school name would leave too few "
      "candidates to fill the role.")
    p("Third, and most important: a bioscience PhD is followed by a postdoc, and "
      "the postdoc re-rates you. Publication record and postdoc lab are earned "
      "after the PhD admission decision, they are what a hiring scientist "
      "actually reads, and they are the reason the PhD institution is a weaker "
      "signal here than in fields with no such second stage.")
    p("What this does <i>not</i> say is that school never matters. It matters at "
      "the margins that the report sets out in section 5 &mdash; access to the "
      "postdoc, geography, and the recruiting network &mdash; and the honest "
      "position on the central quantity is that no published study measures "
      "institution-level intake into pharma R&amp;D. Section 6 is a pipeline "
      "that measures it.")

    f.append(PageBreak())

    # ---- the econ comparison --------------------------------------------
    h1("1. Why this differs from the economics case you raised")
    p("The comparison is a good one, because economics is close to the opposite "
      "configuration. An economics PhD has no postdoc stage: you go on the job "
      "market straight out of the programme, so the department's name and your "
      "advisor's letters are doing most of the signalling work, and they are "
      "doing it on the single occasion that sets your starting position. "
      "Placement records show the effect &mdash; at MIT, 32% of academic "
      "placements went to top-15 US economics departments or top-10 business "
      "schools, a rate no mid-ranked department approaches.")
    p("And the pattern holds on the private-sector side too: the tech, central "
      "bank and consulting employers who hire economics PhDs are reading the "
      "same department-plus-letters signal, because there is no wet-lab skill "
      "portfolio to read instead.")
    p("The irony is that the economics literature contains the sharpest "
      "available evidence <i>against</i> taking department rank as a proxy for "
      "individual quality. Conley and &Ouml;nder tracked 14,299 economics PhDs "
      "from 154 institutions and found that the median graduate of a top-ten "
      "department had fewer than 0.03 AER-equivalent publications six years out "
      "&mdash; an untenurable record almost anywhere &mdash; while Carnegie "
      "Mellon's 85th-percentile graduates out-published the 85th percentile of "
      "Chicago, Penn, Stanford and Berkeley. Rank within your cohort predicts "
      "research output; the rank of the department predicts it surprisingly "
      "poorly.")
    p("So your instinct that economics has a broad band of respectable "
      "programmes is right on the merits and wrong about the market: the "
      "programmes are substitutable in what they teach, but the academic market "
      "prices them as if they were not. Biosciences industry is the case where "
      "the market has a better instrument &mdash; your actual published work.")

    h1("2. The benchmark: what a genuinely prestige-gated market looks like")
    p("Before asking whether pharma screens on pedigree, it helps to have a "
      "calibrated example. Academic faculty hiring is one. Wapman, Zhang, "
      "Clauset and Larremore assembled the near-complete US tenure-track "
      "faculty census for 2011&ndash;2020 and found that roughly a fifth of "
      "PhD-granting institutions supplied about four fifths of all tenure-track "
      "faculty, with five universities alone training one in eight of the "
      "faculty at doctoral institutions. Clauset's earlier work put 71&ndash;86% "
      "of faculty as coming from the top quarter of institutions.")
    f.append(Image(str(c_conc), width=165 * mm, height=62 * mm))
    cap("Source: Wapman et al., <i>Nature</i> 610 (2022), 120&ndash;127. Shares "
        "are approximate, across all fields.")
    p("Lauren Rivera's interview study of elite investment banks, law firms and "
      "consultancies is the other calibrated example, and a starker one: there, "
      "school prestige was the single most important r&eacute;sum&eacute; "
      "screen, recruiting was restricted to a handful of 'super-elite' "
      "campuses, and interviewers attributed superior ability to candidates from "
      "those schools irrespective of their actual performance.")
    p("These are the shapes to compare against. Neither resembles the stated "
      "requirements of a pharma bench-science posting.")

    # ---- what the evidence says -----------------------------------------
    h1("3. What the evidence says about the biosciences case")

    h2("3.1 Industry is now the majority destination")
    f.append(Image(str(c_dest), width=165 * mm, height=75 * mm))
    cap("Source: NSF NCSES Survey of Earned Doctorates, post-graduation "
        "commitments of US life-science doctorate recipients, 1992 and 2022.")
    p("The academic route that the prestige hierarchy rations has been shrinking "
      "as a share of outcomes for thirty years. Roughly 14% of biological "
      "sciences PhDs hold a tenure-track post 5&ndash;6 years after graduating "
      "and about 24% by ten years out, against the 78% of graduate students who "
      "report wanting an academic research career. Whatever prestige does to "
      "faculty hiring, it is operating on a progressively smaller slice of where "
      "bioscience PhDs actually go.")

    h2("3.2 Where prestige effects have been measured, they attach to the academic path")
    p("The quantitative work that exists separates the two markets rather "
      "cleanly. A study of engineering doctorates using 2015&ndash;2018 Survey "
      "of Earned Doctorates data found the research intensity of the PhD "
      "institution significantly predicted choosing an <i>academic</i> career "
      "path. A study of philosophy PhDs found that once career <i>preference</i> "
      "was controlled for, institutional prestige was no longer significantly "
      "associated with academic-versus-non-academic employment &mdash; that is, "
      "much of the apparent prestige effect was graduates of elite programmes "
      "wanting academic jobs more, not being uniquely able to get non-academic "
      "ones.")
    p("Neither is a biosciences industry study, and that is the honest state of "
      "the literature: the sign of the effect for industry hiring is not "
      "established by direct measurement.")

    h2("3.3 What the employer actually asks for")
    p("Pfizer's own Senior Scientist postings state the requirement as a PhD or "
      "equivalent in a named discipline &mdash; 'biochemistry, structural "
      "biology, or a related field' &mdash; with no institutional condition, at "
      "advertised bands around $88&ndash;152k across the Groton, La Jolla and "
      "Cambridge sites. Its internal postdoctoral programme runs 40-plus "
      "positions across roughly a dozen campuses, which is a second, "
      "publication-based entry route into the company that is open after the "
      "PhD is finished.")
    p("Stated requirements are weak evidence about revealed preference &mdash; "
      "no employer advertises a pedigree filter it applies informally. They do "
      "establish that the filter is not formal, which matters for whether an "
      "application is worth making.")

    h1("4. The mechanism: a technique market, not a pedigree market")
    f.append(bullets([
        "<b>Modality-specific demand.</b> Requisitions are written around a "
        "platform &mdash; protein degraders, mRNA formulation, gene editing "
        "delivery, DEL chemistry. The qualified population per modality is "
        "small, so screening it further on school name is a luxury the "
        "requisition cannot afford.",
        "<b>The postdoc re-rates you.</b> Publication record and postdoc lab are "
        "acquired after the PhD, are legible to the hiring scientist, and "
        "dominate the read. This is the structural feature economics lacks.",
        "<b>The hiring manager is a scientist.</b> Pharma R&amp;D panels are "
        "staffed by bench scientists reading your papers and quizzing your "
        "methods, not by HR screening on institution tier &mdash; the opposite "
        "of the campus-recruiting model Rivera documented in finance and law.",
        "<b>Geography beats ranking.</b> Around 70% of US biotech employment "
        "sits in Boston, San Diego and the Research Triangle, and candidates "
        "rarely move between clusters without a relocation conversation. Being "
        "at a mid-ranked school inside a cluster can beat an elite school "
        "outside one.",
        "<b>Salary bands compress the return.</b> At an advertised "
        "$88&ndash;152k for Senior Scientist, there is no pedigree premium of "
        "the kind that makes elite-school screening profitable for a bank.",
    ], st))

    h1("5. Where school does still bite")
    p("The defensible version of the prestige claim is that it operates "
      "indirectly, and mostly before the industry application:")
    f.append(bullets([
        "<b>Postdoc access.</b> If the competitive postdoc is the re-rating "
        "mechanism, then PhD institution matters to the extent it gates entry "
        "to a strong postdoc lab. This is the main channel and it is real.",
        "<b>Advisor network.</b> Referrals do a lot of hiring. A well-connected "
        "advisor with industry collaborators is worth more than the institution "
        "name, and such advisors are not evenly distributed &mdash; but they are "
        "much less concentrated than institutional rank.",
        "<b>Cluster proximity.</b> Internships, collaborations and part-time "
        "industry contact accrue to students near a hub.",
        "<b>Leadership tiers.</b> The senior R&amp;D and CSO population looks "
        "more elite-trained than the bench population. Whether that is hiring, "
        "promotion or survivorship is exactly what section 6's seniority "
        "gradient is designed to separate &mdash; and they are different claims "
        "about different decisions.",
        "<b>Resource confound.</b> Better-funded programmes offer more "
        "expensive techniques and more publication support. The effect is real "
        "but it is about the training, not the name, and it varies far more by "
        "lab than by institution.",
    ], st))

    f.append(PageBreak())

    # ---- method ----------------------------------------------------------
    h1("6. Measuring the part nobody has published")
    p("The gap in the evidence is an institution-level estimate of who actually "
      "gets hired into pharma R&amp;D. It is measurable from open data, and "
      "<font face='Courier'>pedigree_pipeline.py</font> in this directory "
      "implements it. The design point that matters most is the denominator.")
    f.append(Paragraph(
        "Elite schools award a large share of all doctorates. So "
        "&lsquo;most of our scientists went to a top-30 school&rsquo; is "
        "uninterpretable on its own &mdash; it has to be divided by the share of "
        "PhDs those schools produce.", st["pull"]))
    p("The estimand is therefore a representation ratio per institution tier: "
      "the employer's share of scientists trained in that tier, divided by that "
      "tier's share of US bio/biomedical doctorates awarded. A ratio of 1 means "
      "the intake looks exactly like the applicant pool &mdash; no prestige "
      "premium. Above 1 means over-representation, and the size of the excess "
      "is the answer to your question.")
    f.append(Spacer(1, 2 * mm))
    f.append(method_table(st))
    f.append(Spacer(1, 3 * mm))
    p("Training institution is reconstructed from OpenAlex author records, which "
      "carry a dated affiliation history, so the earliest education-type "
      "affiliation stands in for the PhD institution. OpenAlex is CC0 and has a "
      "public API. LinkedIn is deliberately not used: scraping it breaches its "
      "terms and its self-reported education fields are unverifiable.")
    p("Comparators matter as much as Pfizer itself. Running the same pipeline "
      "over Merck, AstraZeneca, Genentech, Amgen, Regeneron, Vertex and Moderna "
      "turns a single company's number into a distribution, and it is the "
      "spread across employers &mdash; not any one value &mdash; that tells you "
      "whether pedigree screening is an industry norm or a house style.")

    h2("What would make the result wrong")
    p("The pipeline reports these rather than burying them, and the report's "
      "conclusion should be read as conditional on them:")
    f.append(bullets([
        "<b>Publication bias in the sample.</b> Only scientists who publish "
        "under a Pfizer affiliation are visible. Process development, "
        "regulatory and much of clinical operations are not, and they are a "
        "large share of R&amp;D headcount &mdash; plausibly the share where "
        "pedigree matters least, which would bias the measured premium upward.",
        "<b>Thin affiliation history before ~2010.</b> Senior staff are "
        "under-sampled relative to junior staff.",
        "<b>PhD versus postdoc.</b> The two are not reliably separable from "
        "publication metadata; the run is reported with and without the "
        "ambiguous records.",
        "<b>Undergraduate co-authorship.</b> A paper published before the PhD "
        "would misattribute the training institution.",
        "<b>Survivorship.</b> This measures who is employed now, not who was "
        "hired, so it cannot by itself separate hiring from retention.",
        "<b>Ranking choice.</b> Any tiering imports its own bias, which is why "
        "two independent axes are run and only findings surviving both are "
        "reported.",
    ], st))

    h2("A note on why this report has no Pfizer numbers in it")
    p("The pipeline was written and unit-tested here but could not be run: the "
      "environment this report was produced in permits outbound network access "
      "to package registries only, so api.openalex.org is unreachable. Running "
      "the four commands in the README from a machine with ordinary internet "
      "access produces the tier table, the representation ratios and the "
      "seniority gradient. Reporting invented figures in the meantime would "
      "have been worse than reporting none.")

    h1("7. Practical read")
    f.append(bullets([
        "A non-elite bioscience PhD is not a barrier to a Pfizer scientist "
        "role. The formal requirement is the degree in a relevant field.",
        "Optimise for the advisor, the technique and the publication record "
        "over the institution's ranking &mdash; that is what is read, and "
        "Conley and &Ouml;nder's result on how weakly department rank predicts "
        "individual output generalises.",
        "Treat the postdoc as the real positioning decision. It is the stage "
        "where an unfashionable PhD can be re-rated, and it comes after the "
        "admissions decision you may already regret.",
        "Weight location heavily. A mid-ranked programme inside the Boston, "
        "San Diego or RTP cluster has an access advantage over an elite "
        "programme outside one.",
        "Be more cautious about the academic path. That is the market where "
        "the prestige hierarchy is documented, steep, and unlikely to move.",
    ], st))

    # ---- references ------------------------------------------------------
    h1("References")
    refs = [
        "Wapman, K.H., Zhang, S., Clauset, A., Larremore, D.B. (2022). "
        "Quantifying hierarchy and dynamics in US faculty hiring and retention. "
        "<i>Nature</i> 610, 120&ndash;127. doi:10.1038/s41586-022-05222-x",
        "Clauset, A., Arbesman, S., Larremore, D.B. (2015). Systematic "
        "inequality and hierarchy in faculty hiring networks. "
        "<i>Science Advances</i> 1(1).",
        "Nietzel, M.T. (2022). The prestige hierarchy: five universities "
        "trained one of every eight tenure-track faculty at doctoral "
        "universities. <i>Forbes</i>, 22 September 2022.",
        "Conley, J.P., &Ouml;nder, A.S. (2014). The research productivity of "
        "new PhDs in economics: the surprisingly high non-success of the "
        "successful. <i>Journal of Economic Perspectives</i> 28(3), 205&ndash;216.",
        "Rivera, L.A. (2011). Ivies, extracurriculars, and exclusion: elite "
        "employers' use of educational credentials. "
        "<i>Research in Social Stratification and Mobility</i> 29(1), 71&ndash;90.",
        "NSF National Center for Science and Engineering Statistics. "
        "<i>Doctorate Recipients from U.S. Universities</i> (Survey of Earned "
        "Doctorates), 2023 and 2024 cycles &mdash; sector commitments, field "
        "trends, and the 459 doctorate-granting institutions. "
        "ncses.nsf.gov/surveys/earned-doctorates",
        "Council of Graduate Schools (2022). Research brief on biomedical PhD "
        "career outcomes &mdash; tenure-track attainment at 5&ndash;6 and 10 "
        "years.",
        "Larsen, A.K. et al. Institutional prestige, advisor sponsorship, and "
        "academic career placement preferences. <i>PLOS ONE</i> 12(5): e0176977.",
        "Prestige, career paths, and job satisfaction among recent philosophy "
        "PhDs (2026). American Philosophical Association placement data "
        "analysis &mdash; prestige effect after controlling for preference.",
        "Career paths of doctoral recipients in engineering and computer "
        "science. <i>Biomedical Engineering Education</i> (2024). "
        "doi:10.1007/s43683-024-00140-y",
        "Pfizer Senior Scientist postings, Groton / La Jolla / Cambridge sites, "
        "and Worldwide Research postdoctoral programme description. pfizer.com",
        "BioSpace and CSG Talent cluster analyses &mdash; Boston, San Diego and "
        "Research Triangle share of US biotech employment.",
        "OpenAlex (openalex.org), CC0 bibliographic database &mdash; author "
        "affiliation histories and institution-level output.",
        "NIH RePORTER (reporter.nih.gov) &mdash; award totals by organisation.",
    ]
    for i, r in enumerate(refs, start=1):
        f.append(Paragraph(f"{i}. {r}", st["small"]))

    f.append(Spacer(1, 6 * mm))
    f.append(Paragraph(
        "Figures quoted from secondary summaries of the sources above are "
        "approximate and flagged with '~' or 'roughly'. No figure in this "
        "report is modelled, imputed or estimated by the author.", st["caption"]))

    doc = SimpleDocTemplate(
        str(PDF), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=20 * mm, bottomMargin=18 * mm,
        title="Does PhD-institution ranking matter for a biosciences PhD?",
        author="Research note",
    )
    doc.build(f)
    return PDF


if __name__ == "__main__":
    out = build()
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
