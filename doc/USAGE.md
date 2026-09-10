# GHTraffic Command-Line Usage

GHTraffic provides three command-line commands through `ghtraffic.py`: `collect`, `show`, and `referrers`.

By default, the program reads the SQLite database location from `database.path` in `ghtraffic.properties`.

## Collect traffic

Run:

```bash
python ghtraffic.py collect
```

The `collect` command connects to GitHub using the access token stored as `github.token` in `ghtraffic.properties`, discovers all non-fork repositories owned by the authenticated user, and collects the latest available:

- views and unique visitors;
- clones and unique cloners; and
- referrer traffic.

The collected data is written to the local SQLite database configured by `database.path`. Existing daily traffic records are updated when GitHub returns revised values, so repeated collection does not create duplicate daily records.

See [GITHUB_SETUP.md](GITHUB_SETUP.md) for GitHub authentication setup.

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

## Use another database

The normal database path is configured in `ghtraffic.properties`:

```text
database.path=/path/to/ghtraffic.db
```

The `--db` option selects an explicit SQLite database file for a single command and must appear before the command:

```bash
python ghtraffic.py --db ./ghtraffic.db show
python ghtraffic.py --db ./ghtraffic.db show 30
python ghtraffic.py --db ./ghtraffic.db referrers
python ghtraffic.py --db ./ghtraffic.db collect
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
