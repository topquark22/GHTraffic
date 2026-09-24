# GHTraffic Command-Line Usage

GHTraffic provides four command-line commands through `ghtraffic.py`: `collect`, `show`, `referrers`, and `export-csv`.

By default, the program reads the SQLite database location from `database.path` in the per-user `ghtraffic.properties` file. It does not look for a properties file in the current directory or beside `ghtraffic.py`.

The properties file is located at:

```text
Windows / Cygwin:
%LOCALAPPDATA%\GHTraffic\ghtraffic.properties

Linux:
~/.config/ghtraffic/ghtraffic.properties
```

This means that running `ghtraffic.py` manually from a source checkout still uses the same configuration as the deployed application.

## Collect traffic

Run:

```bash
python ghtraffic.py collect
```

The `collect` command connects to GitHub using every access token stored as `github.token` or `github.token.<name>` in `ghtraffic.properties`, discovers all non-fork repositories owned by each authenticated user, and collects the latest available:

- views and unique visitors;
- clones and unique cloners; and
- referrer traffic.

The collected data is written to the local SQLite database configured by `database.path`. Existing daily traffic records are updated when GitHub returns revised values, so repeated collection does not create duplicate daily records.

See [GITHUB_SETUP.md](GITHUB_SETUP.md) for GitHub authentication setup.

To collect only one configured GitHub account, use:

```bash
python ghtraffic.py collect --account topquark22
```

The account name is the GitHub login discovered from the token; it does not need
to match the suffix used on the corresponding property name. The web interface
uses the same discovered owner names for its **Account** dropdown.

## Show traffic

Run:

```bash
python ghtraffic.py show
```

With no argument, `show` reports traffic for the last 14 days.

To request another reporting period, supply the number of days:

```bash
python ghtraffic.py show 7
python ghtraffic.py show 30
python ghtraffic.py show 90
```

The report shows, for each repository with traffic during the selected period:

- views;
- unique visitors;
- clones; and
- unique cloners.

GHTraffic can report only history that has actually been collected into the local database. A newly installed database may therefore contain less history than the requested reporting period.

## Show referrers

Run:

```bash
python ghtraffic.py referrers
```

The `referrers` command shows the most recently collected referrer snapshot for each repository, including:

- repository name;
- the date on which the snapshot was collected (`As of`);
- referrer;
- views; and
- unique visitors.

GitHub supplies referrer statistics as a rolling aggregate rather than daily historical values. The `As of` date identifies when GHTraffic observed the snapshot; it is not the date on which the referred traffic occurred.

## Export traffic to CSV

### Web user interface

In the web user interface, select the repository and reporting period, then click **Export CSV**.

### Command line

The same daily traffic data can be exported from the command line with:

```bash
python ghtraffic.py export-csv Snarkypuss
```

The default reporting period is 14 days. To export another period, supply the number of days:

```bash
python ghtraffic.py export-csv Snarkypuss 30
```

The repository may be given as either its current repository name or full `owner/name`.

By default, the CLI uses the same filename format as the web UI. For example, exporting 30 days for `Snarkypuss` writes:

```text
Snarkypuss-traffic-30d.csv
```

Use `--output` (or `-o`) to select another path:

```bash
python ghtraffic.py export-csv Snarkypuss 30 --output traffic.csv
```

Both the web and CLI exports contain:

- `Date`
- `Views`
- `Clones`
- `Unique Cloners`

Only dates present in the local GHTraffic database are exported; missing historical dates are not synthesized as zero-valued rows.

## Use another database

The normal database path is configured in `ghtraffic.properties`. A typical Linux value is:

```text
database.path=/path/to/github_traffic.db
```

The `--db` option selects an explicit SQLite database file for a single command and must appear before the command:

```bash
python ghtraffic.py --db ./github_traffic.db show
python ghtraffic.py --db ./github_traffic.db show 30
python ghtraffic.py --db ./github_traffic.db referrers
python ghtraffic.py --db ./github_traffic.db export-csv Snarkypuss 30
python ghtraffic.py --db ./github_traffic.db collect
```

The `--db` command-line option takes precedence over `database.path` and is intended primarily for testing and manual use.

## Help

General command-line help is available with:

```bash
python ghtraffic.py --help
```

Command-specific help is available with, for example:

```bash
python ghtraffic.py show --help
```
