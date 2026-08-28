# FAERS Deduplication Method

**Status:** Documented before running the full FAERS ingestion pipeline (project brief Sec. 10:
"Create docs/faers_deduplication.md explaining the method" before dropping any duplicates).

FAERS is known to contain two **distinct** kinds of duplication, and this project treats them
differently. Conflating them is a common source of error in pharmacovigilance data pipelines.

## 1. Version history (the same case, updated over time)

FDA's own guidance states: *"Rather than updating individual records in FAERS, subsequent updates
are submitted in separate reports"* (open.fda.gov, Drug Adverse Event Overview, fetched
2026-08-28). In the raw FAERS quarterly extract files, this is modeled as `caseid` (stable) +
`caseversion` (increments on each update), with `primaryid` = a composite of the two.

**What we found empirically against the live openFDA `/drug/event` API** (not assumed from
documentation, which does not describe this at the JSON-field level):

- Every JSON record returned by openFDA has a `safetyreportid` field and a separate
  `safetyreportversion` field (e.g. `safetyreportid: "10028019"`, `safetyreportversion: "3"`).
- Querying `/drug/event.json?search=safetyreportid:10028019` returns **exactly one** record.
- Across a full query result set (367 records for `nandrolone`), all 367 `safetyreportid` values
  were unique, despite `safetyreportversion` ranging from 1 to 10+ across the set.

Together, this is consistent with `safetyreportid` functioning as openFDA's **stable, per-case**
identifier (i.e. FAERS `caseid`), with the API index reflecting only the **current/latest**
content for each case — `safetyreportversion` tells us how many times that case has been amended,
but older amendment content is not separately retrievable through this endpoint. We could not find
an FDA-published statement confirming this indexing behavior explicitly (only the general
"updates are submitted as separate reports" statement above), so this project treats it as a
**strong empirical inference, not a documented guarantee**, and defends against it being wrong:

**Rule actually implemented:** `faers_reports` has a unique constraint on `(case_id, version)`
(`case_id` = `safetyreportid`, `version` = `safetyreportversion`). After each ingestion run, a
post-ingestion pass groups all rows by `case_id`; if more than one `version` was ever ingested for
the same `case_id` (which our empirical testing did not observe via the live API, but which our
schema does not assume is impossible), the row with the **maximum** `version` is kept as
`is_deduplicated_latest = True`; all others are kept in the table (never deleted) with
`is_deduplicated_latest = False` and `dedup_reason = "superseded_by_newer_version"`. This is the
standard FDA-recommended max-caseversion-per-caseid approach, applied defensively to whatever was
actually ingested rather than assumed never to trigger.

**All downstream analyses (ROR calculation, safety phenotype construction, etc.) filter to
`is_deduplicated_latest = True` only.**

## 2. Cross-source duplicate reports (the same real-world event, reported independently twice)

This is a separate, well-documented pharmacovigilance problem: the same adverse event can be
reported to FDA independently by, e.g., both the treating clinician and the drug manufacturer,
producing two *genuinely different* `safetyreportid`/case numbers that describe the same
underlying incident. FAERS records include a `duplicate` flag and a `reportduplicate` object
(`duplicatesource`, `duplicatenumb`) intended to flag this — we observed this in a real fetched
record (a Soliris/PNH case also listing nandrolone, flagged `duplicate: "1"` with
`reportduplicate.duplicatenumb` referencing a company case number).

**This project does not currently resolve cross-source duplicates.** `duplicatenumb` is a
free-text company case number, not a `safetyreportid` we can reliably join against, and published
literature on this problem (see `research/literature_review.md`) describes purpose-built
algorithms — including NLP over narrative text — to resolve it well beyond what structured
fields alone support. Attempting a naive resolution here risks silently dropping genuinely
independent reports or, worse, merging genuinely distinct cases. This is documented as an
**explicit limitation** (not ingested as a structured field, not acted upon), tracked in
`TODO.md` as a candidate future enhancement, and disclosed in `reports/data_quality.md` and the
Limitations section of the research report once populated.

## What this means for report counts

Every count reported in this project's figures/tables (e.g. "N reports for compound X") refers to
`is_deduplicated_latest = True` rows only, and is explicitly a **count of distinct FAERS cases**
(by the above definition), not a count of unique real-world patients or events — cross-source
duplication (Sec. 2 above) means the true number of distinct real-world events could be somewhat
lower than the case count, in an unknown and undocumented proportion. This caveat is repeated in
`research/exclusion_rules.md` and the research report's Limitations section.
