/**
 * Persistent reminder of what FAERS-derived statistics are (and are not). Project brief Sec. 37:
 * separate OBSERVED DATA / DERIVED STATISTICS / MODEL OUTPUT / INTERPRETATION, and Sec. 23:
 * FAERS cannot establish incidence, prevalence, absolute risk, or causation.
 */
export function DisclaimerBanner() {
  return (
    <div className="bg-amber-50 border-b border-amber-200 text-amber-900 text-sm">
      <div className="mx-auto max-w-6xl px-4 py-2">
        <strong>Reporting associations, not clinical risk:</strong> FAERS is a voluntary,
        spontaneous reporting system. Every statistic on this site is a disproportionality signal
        or reporting association -- it does not establish incidence, prevalence, absolute risk, or
        causation. See the{" "}
        <a href="/limitations" className="underline">
          Limitations
        </a>{" "}
        page.
      </div>
    </div>
  );
}
