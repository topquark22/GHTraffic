# GitHubMonitor Requirements

## Core

### 1. Purpose

GitHubMonitor collects repository traffic statistics from GitHub and maintains a local historical record that is not limited by GitHub's short traffic-retention window.

The initial version focuses on repository views and clones across all non-fork repositories owned by the authenticated GitHub user.

### 2. Repository discovery

1. The application shall determine the authenticated GitHub user through the GitHub API.
2. The application shall retrieve the repositories owned by that user through the GitHub API.
3. Repository discovery shall not depend on a manually maintained repository list.
4. Forked repositories shall be excluded from monitoring.
5. Public and private repositories shall be eligible for monitoring.
6. Archived repositories shall remain eligible for monitoring.
7. Newly created repositories shall be discovered automatically on subsequent runs.
8. Repositories that are renamed shall be tracked using their stable GitHub repository ID.

### 3. Repository metadata

For each discovered repository, the application shall retain at least:

- GitHub repository ID
- owner login
- repository name
- full repository name
- visibility or private/public status
- archived status
- fork status
- default branch

Repository metadata shall be refreshed during collection runs.

### 4. Traffic collection

For every monitored repository, the application shall retrieve GitHub traffic data for:

- views
- unique visitors
- clones
- unique cloners
- top referral sources

The application shall use GitHub's daily traffic breakdown for views and clones rather than relying only on rolling aggregate totals.

The application shall refresh the complete views/clones traffic window returned by GitHub on each collection run. Existing records for a repository and date shall be updated when GitHub returns revised values.

Collection shall therefore be idempotent: running the collector repeatedly with the same GitHub data shall not create duplicate traffic records.

Referral traffic shall be stored as snapshots of the top-referrer data reported by GitHub. Successive referral snapshots shall not be treated as independent daily traffic counts.

### 5. Historical persistence

Traffic history shall be stored in SQLite.

The database shall retain historical daily traffic after the corresponding data is no longer available from GitHub.

Each repository/date pair shall have at most one daily traffic record.

Each daily traffic record shall retain the time at which it was most recently collected.

For referral traffic, each repository/collection-date/referrer combination shall have at most one record.

Dates shall be stored in ISO 8601 form suitable for chronological ordering and SQLite date operations.

### 6. Initial data model

The database shall contain four tables:

- `repositories`
- `repository_names`
- `daily_traffic`
- `referral_traffic`

The numeric GitHub repository ID shall be used directly as the canonical repository key. No separate local surrogate repository key is required.

Repository names shall be stored separately from repository identity so that name changes can be tracked over time without changing the repository key used by traffic records.

A daily traffic record shall contain:

- repository reference
- traffic date
- views
- unique visitors
- clones
- unique cloners
- collection timestamp

The repository reference and traffic date together shall uniquely identify a daily traffic record.

A referral traffic record shall contain:

- repository reference
- collection date
- referrer
- views
- unique visitors

The repository reference, collection date, and referrer together shall uniquely identify a referral traffic record.

### 7. Reporting

The application shall provide a `show [days]` command that reports traffic from the local database.

When `days` is omitted, `show` shall report the most recent 14 days.

The report shall include, for each repository:

- views
- unique visitors
- clones
- unique cloners

Repositories with no views and no clones during the selected period may be omitted from the default report.

The application shall allow the user to request other reporting windows by supplying a positive integer number of days, for example:

```text
show 7
show 30
```

Daily unique visitor and unique cloner counts shall not be represented as true multi-day unique-user totals when aggregated across dates, because GitHub does not provide identity-level data needed to deduplicate users across days.

The application shall provide a `referrers` command that reports the most recently collected referrer data for each repository. The collection date shall be presented as the date the values were observed ("As of"), not as the date on which the underlying traffic occurred.

### 8. Scheduling

The collector shall be suitable for unattended execution once per day.

Scheduling shall be external to the core collector so the program can be run manually or by an operating-system scheduler.

On Windows, the supported deployment uses Windows Task Scheduler under the user's account and may run while the user is logged out.

A failed collection run shall not corrupt or discard previously collected traffic history.

### 9. Authentication

The application shall authenticate to GitHub using a dedicated access token supplied through the `GITHUB_TOKEN` environment variable.

Credentials shall not be stored in the SQLite database or committed to the source repository.

The authenticated credentials must have sufficient permission to retrieve traffic data for every repository to be monitored.

### 10. Error handling

Failure to collect traffic for one repository shall not prevent collection from continuing for other repositories.

Collection failures shall identify the affected repository and provide enough diagnostic information to determine whether the failure was caused by authentication, permissions, API limits, or another error.

The application shall return a non-zero exit status when a collection run contains failures that require operator attention.

### 11. Core scope exclusions

The core does not require:

- monitoring repositories owned by other users or organizations
- monitoring forked repositories
- a graphical or web user interface
- GitHub Actions as the required scheduler
- storage of individual visitor identities
- reconstruction of historical traffic older than the data available when GitHubMonitor is first run
- popular-path collection

Popular paths may be added in a later version without changing the core daily traffic model.

### 12. Design goals

The implementation should remain small, understandable, and easy to operate.

The collector should prefer GitHub's documented API over scraping GitHub web pages.

The SQLite database should remain portable and directly inspectable with standard SQLite tools.

## User interface

### 1. Architecture

The user interface shall be implemented as a separate application from the core collector.

The user interface shall read traffic data from the existing SQLite database and shall not require direct access to the GitHub API for normal reporting.

The user interface shall run from the same codebase on Windows and Linux.

The user interface shall use only the Python standard library for its HTTP server and API endpoints, together with a small HTML/JavaScript front end displayed in a web browser.

The UI shall serve its required JavaScript assets locally so normal use does not depend on an external CDN.

The UI shall not require third-party Python packages.

### 2. Repository selection

The user interface shall provide a drop-down control for selecting a repository.

Repository selection shall use the current repository name from `repository_names`. Historical repository names shall not appear as separate repositories.

### 3. Traffic display

For the selected repository, the user interface shall display daily views and clones as a bar chart.

The user interface shall provide a control for selecting the reporting period. The default reporting period shall be 14 days.

### 4. Referrers

For the selected repository, the user interface shall display the most recently collected referrer data available in `referral_traffic`.

The referrer display shall include:

- referrer
- views
- unique visitors
- the collection date, identified as "As of"

The collection date shall not be presented as the date on which the underlying referred traffic occurred.
