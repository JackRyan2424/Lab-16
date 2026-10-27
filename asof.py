"""Point-in-time price filter. Run with: python asof.py"""

from datetime import date


# Editable inputs: row number, ticker, month measured, publication date, price.
DECISION_DATE = "2026-03-31"
TABLE = [
    (1, "AAA", "2026-01", "2026-02-10", 101.0),
    (2, "AAA", "2026-02", "2026-03-10", 104.0),
    (3, "AAA", "2026-03", "2026-04-10", 109.0),
    (4, "AAA", "2026-02", "2026-03-25", 103.0),
    (5, "BBB", "2026-01", "2026-02-10", 98.0),
    (6, "BBB", "2026-02", "2026-03-10", 97.0),
    (7, "BBB", "2026-02", "2026-03-10", 97.0),
    (8, "BBB", "2026-03", "2026-04-10", 92.0),
    (9, "CCC", "2026-01", "2026-02-10", 110.0),
    (10, "CCC", "2026-02", "2026-04-05", 112.0),
    (11, "", "2026-02", "2026-03-10", 99.0),
    (12, "CCC", "2026-02", "2026-03-10", 111.0),
]


def latest_publications(rows):
    """Rule 4: keep the latest publication for each ticker/month pair."""
    latest = {}
    for row in rows:
        key = (row[1], row[2])
        if key not in latest or row[3] > latest[key][3]:
            latest[key] = row
        elif row[3] == latest[key][3] and row[4] != latest[key][4]:
            raise ValueError(f"Conflicting prices on the same publication date: {key}")
    return sorted(latest.values(), key=lambda row: row[0])


def filter_rows(table, decision_date):
    cutoff = date.fromisoformat(decision_date)
    rows = list(table)
    funnel = []

    # Rule 1: quarantine missing tickers.
    removed = [row for row in rows if not row[1].strip()]
    rows = [row for row in rows if row[1].strip()]
    funnel.append(("Quarantined: no ticker", removed))

    # Rule 2: row numbers identify source records, not duplicate content.
    seen = set()
    unique = []
    removed = []
    for row in rows:
        content = row[1:]
        if content in seen:
            removed.append(row)
        else:
            seen.add(content)
            unique.append(row)
    funnel.append(("Exact duplicate", removed))

    # Preserve cleaned records for the comparison that ignores publication time.
    naive_panel = latest_publications(unique)

    # Rule 3: only publications available by the decision date are admissible.
    removed = [row for row in unique if date.fromisoformat(row[3]) > cutoff]
    rows = [row for row in unique if date.fromisoformat(row[3]) <= cutoff]
    funnel.append((f"Published after {decision_date}", removed))

    # Rule 4 runs AFTER the cutoff, so a future revision cannot replace a known row.
    panel = latest_publications(rows)
    kept_ids = {row[0] for row in panel}
    removed = [row for row in rows if row[0] not in kept_ids]
    funnel.append(("Older vintage replaced by revision", removed))
    return funnel, panel, naive_panel


def signal(panel, ticker):
    rows = sorted((row for row in panel if row[1] == ticker), key=lambda row: row[2])
    if len(rows) < 2:
        return "N/A (fewer than two months)"
    previous, latest = rows[-2:]
    year, month = map(int, latest[2].split("-"))
    previous_month = f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"
    if previous[2] != previous_month:
        return f"N/A (missing previous month for {latest[2]})"
    if previous[4] == 0:
        return "N/A (previous price is zero)"
    change = (latest[4] / previous[4] - 1) * 100
    month_name = date(year, month, 1).strftime("%B %Y")
    return f"{change:+.2f}% ({month_name})"


def main():
    funnel, panel, naive_panel = filter_rows(TABLE, DECISION_DATE)
    print(f"Decision date: {DECISION_DATE}\n\nROW FUNNEL")
    print(f"Starting rows: {len(TABLE)}")
    remaining = len(TABLE)
    for label, removed in funnel:
        remaining -= len(removed)
        numbers = ", ".join(str(row[0]) for row in removed) or "none"
        print(f"{label}: {len(removed)} removed; rows: {numbers}; {remaining} remain")

    print("\nAS-OF PANEL")
    print(f"{'Row':>3}  {'Ticker':6}  {'Month':7}  {'Published':10}  {'Price':>7}")
    for number, ticker, month, published, price in panel:
        print(f"{number:>3}  {ticker:6}  {month:7}  {published:10}  {price:7.1f}")

    print("\nSIGNALS (price return, not bond yield)")
    for ticker in sorted({row[1] for row in panel + naive_panel}):
        print(f"{ticker}: as-of {signal(panel, ticker)}; naive {signal(naive_panel, ticker)}")


if __name__ == "__main__":
    main()
