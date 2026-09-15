# Findings for the site

Merged requests for work reach the public site as findings. A finding is one row with one claim about a site, a country
or the whole inventory. After every merge, the Site data workflow rebuilds the site from `main`. Each finding then:

- appears in its site's panel on the quarterly detail and research views;
- is counted on the site's card on the map and in the list;
- is listed on [the findings page](https://openobservatory.info/findings.html).

Findings sit beside the estimates and never change a number. To change a capacity, a date or a polygon, edit the inventory
files as `CONTRIBUTING.md` describes. An imagery verdict is the only finding that changes a site's status: on an entry found
by radar, it replaces "unconfirmed" in the Built line.

## Two ways in

- **A file in this folder.** Add `data/evidence/<ID>.csv`, for example `RFW-04.csv`, by hand or from your script. This
  suits most work.
- **An adapter.** Use one when a script regenerates your results. Add a function to `tools/evidence.py` that turns the
  result rows into findings, and the site follows every rerun with no second file to keep up to date. RFW-01, 03, 07, 14,
  19, 20 and 32 were merged before this format existed, so they use adapters.

## Columns

| Column | Required | Contents |
|---|---|---|
| `subject` | yes | One of three: a `site_id` from `data/sites.csv` (hub entries such as `ulanqab_hub` count), `country:` with a two-letter code such as `country:CN`, or `global` |
| `request` | yes | The ID the work delivers against, as a heading in `REQUESTS_FOR_WORK.md`: `RFW-04`, `T-02` or `PAID-01` |
| `answers` | yes | The question the finding answers: `where`, `built`, `capacity`, `running`, `utilisation`, `workload` or `sources` |
| `finding` | yes | One line of at most 400 characters that stands on its own: the result, with its number, unit and date |
| `detail` | no | Method, limits and what the finding does not show, in at most 1,500 characters |
| `verdict` | no | `data-hall complex`, `unclear` or `not a data centre`. Allowed only when `answers` is `where` and the subject is a site |
| `confidence` | yes | `high`, `medium` or `low`: how far the finding can be relied on as stated |
| `period` | no | When the finding applies: `2025`, `2025-01`, `2025-01-31`, `2025Q1` or `FY2025`, or a range such as `2024-07..2025-01` |
| `source` | yes | A public URL, or the path of a committed file in this repository |
| `pull_request` | no | The pull request's number |
| `recorded` | no | The date the finding was recorded, as `YYYY-MM-DD` |

Quote any value that contains a comma. The row shape, with placeholders in angle brackets:

```csv
subject,request,answers,finding,detail,verdict,confidence,period,source,pull_request,recorded
<site_id>,RFW-04,built,"<what the record shows, with its number and date>","<its limits>",,medium,2024-03,<URL or results/your_file.csv>,<number>,2026-09-20
```

## Rules

- Write each finding so a reader can check it: give the number, what it measures and the date.
- Keep negative results. "No capacity figure in 12 annual reports" is a finding.
- Put one claim in each row, and do not repeat what the inventory already shows.
- A `source` must be public or committed. Never point one at `data/private/` or at a page behind a login.
- `python tools/evidence.py --check` validates every row and names each problem. The tests run the same check, and the site
  build stops on any bad row, so a bad finding never reaches the site.
