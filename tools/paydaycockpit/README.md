# PaydayCockpit — Sprint tab builder

Adds a single `Sprint` tab to an existing PaydayCockpit workbook: a 3-day
milestone system (scoreboard, sprint contract + kill row, 3-day plan,
shift-aware day planner, shiny-object parking lot, sprint log with a chain
counter, pre-seeded sprint queue, rules of engagement).

No existing tab, cell, or defined name is modified. The only change outside
the new tab is moving `Sprint` to sheet index 0.

## Run

    python3 build_sprint.py          # edit SRC / OUT at the top first
    python3 <xlsx-skill>/scripts/recalc.py <out.xlsx> 1200
    python3 patch_styles.py <out.xlsx>

`patch_styles.py` is required after the recalc: the LibreOffice round-trip
mangles three font records into `<name val="<int>"/>` with every other
attribute dropped. Only Sprint-tab cells reference them, so the script
restores the three intended definitions in `xl/styles.xml` in place and
leaves the recalculated values untouched.

## Formula notes

Excel-2007-era functions only (`COUNTA`, `COUNTIF`, `INDEX`/`MATCH`,
`IFERROR`, `LOOKUP`, `TODAY`, `N`, `SUM`) so the file recalculates cleanly
in LibreOffice as well as Excel.

- Business-hours target is `INDEX`/`MATCH` against the day-planner key row,
  so the `Off / Day shift / Night shift` dropdown drives 6.5 / 1.5 / 2.5.
- The sprint-log `Chain` column is a running counter
  (`=IF(result="","",IF(result="SHIPPED ✓",N(prev)+1,0))`); the scoreboard
  reads its last non-empty value with the `LOOKUP(2,1/(range<>""),range)`
  pattern.
- Dropdown source lists live on the Sprint tab in hidden columns AA:AC —
  the `Lists` tab is not touched.
