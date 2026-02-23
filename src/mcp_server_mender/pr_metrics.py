# src/mcp_server_mender/pr_metrics.py
import os
from datetime import datetime, timedelta, timezone
from github import Github, Auth
import statistics

def get_env_vars():
    """Get and validate required environment variables."""
    token = os.environ.get("GH_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    team_members_str = os.environ.get("TEAM_MEMBERS")
    excluded_labels_str = os.environ.get("EXCLUDED_LABELS", "")

    if not all([token, repo_name, team_members_str]):
        raise ValueError("Missing one or more required environment variables: GH_TOKEN, GITHUB_REPOSITORY, TEAM_MEMBERS")

    team_members = {member.strip() for member in team_members_str.split(",") if member.strip()}
    excluded_labels = {label.strip() for label in excluded_labels_str.split(",") if label.strip()}
    return token, repo_name, team_members, excluded_labels

def is_weekend(date):
    """Check if a date is on a weekend."""
    return date.weekday() >= 5

def get_business_timedelta(start, end):
    """Calculate the timedelta in business hours between two datetimes."""
    if not start or not end:
        return timedelta()
    
    # Ensure both datetimes are timezone-aware for comparison
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    business_hours = 0
    current_date = start
    while current_date < end:
        if not is_weekend(current_date):
            business_hours += 1
        current_date += timedelta(hours=1)
    return timedelta(hours=business_hours)

def format_timedelta(td):
    """Format a timedelta into a readable string like '3d 4h 15m'."""
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"

def analyze_pulls(pulls, team_members, excluded_labels):
    """Analyzes a list of pull requests and returns detailed statistics."""
    stats = {
        "open_prs": [], "closed_prs_count": 0, "lines_changed": [],
        "time_to_first_review": [], "time_to_close": [],
        "prs_over_48h_to_review": [], "prs_over_48h_to_close": []
    }
    member_stats = {member: {
        "opened": 0, "reviewed": 0, "open_prs": [], "assigned_for_review": 0,
        "time_to_first_review": [], "time_to_close": [], "lines_changed": []
    } for member in team_members}

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    for pr in pulls:
        if pr.created_at < thirty_days_ago:
            break
        if any(label.name in excluded_labels for label in pr.labels):
            continue

        # General Repo Stats
        lines = pr.additions + pr.deletions
        stats["lines_changed"].append(lines)

        # Member specific author stats
        author = pr.user.login
        if author in team_members:
            member_stats[author]["opened"] += 1
            member_stats[author]["lines_changed"].append(lines)

        # Handle Open/Closed PRs
        if pr.state == 'open':
            stats["open_prs"].append(pr.html_url)
            if author in team_members:
                member_stats[author]["open_prs"].append(pr.html_url)
            if pr.requested_reviewers:
                for reviewer in pr.requested_reviewers:
                    if reviewer.login in team_members:
                        member_stats[reviewer.login]["assigned_for_review"] += 1
        else: # Closed PRs
            stats["closed_prs_count"] += 1
            if pr.closed_at:
                time_to_close = get_business_timedelta(pr.created_at, pr.closed_at)
                stats["time_to_close"].append(time_to_close)
                if author in team_members:
                    member_stats[author]["time_to_close"].append(time_to_close)
                if time_to_close > timedelta(hours=48):
                    stats["prs_over_48h_to_close"].append(pr.html_url)

        # Review stats
        reviews = list(pr.get_reviews())
        reviewers_in_pr = set()
        first_review_time = None
        for review in reviews:
            reviewer = review.user.login
            if reviewer in team_members and reviewer not in reviewers_in_pr:
                member_stats[reviewer]["reviewed"] += 1
                reviewers_in_pr.add(reviewer)

            if first_review_time is None:
                first_review_time = review.submitted_at
        
        if first_review_time:
            time_to_review = get_business_timedelta(pr.created_at, first_review_time)
            stats["time_to_first_review"].append(time_to_review)
            if time_to_review > timedelta(hours=48):
                stats["prs_over_48h_to_review"].append(pr.html_url)
            # Attribute review time to the first reviewer in the team
            first_team_reviewer = next((r.user.login for r in reviews if r.user.login in team_members), None)
            if first_team_reviewer:
                member_stats[first_team_reviewer]["time_to_first_review"].append(time_to_review)


    return stats, member_stats

def generate_report(repo_name, stats, member_stats):
    """Generates a markdown report from the statistics."""
    
    def get_avg_and_median(data, time_format=False):
        if not data:
            return "N/A", "N/A"
        if time_format:
            avg_val = timedelta(seconds=statistics.mean(d.total_seconds() for d in data))
            median_val = timedelta(seconds=statistics.median(d.total_seconds() for d in data))
            return format_timedelta(avg_val), format_timedelta(median_val)
        else:
            return f"{statistics.mean(data):.2f}", f"{statistics.median(data):.2f}"

    avg_ttr, median_ttr = get_avg_and_median(stats["time_to_first_review"], time_format=True)
    avg_ttc, median_ttc = get_avg_and_median(stats["time_to_close"], time_format=True)
    avg_size, median_size = get_avg_and_median(stats["lines_changed"])

    report = [f"# PR Metrics Report for `{repo_name}`\n"]
    report.append("## 📈 Repository Summary (Last 30 Days)\n")
    report.append(f"- **Open PRs**: {len(stats['open_prs'])}")
    report.append(f"- **Closed PRs**: {stats['closed_prs_count']}")
    report.append(f"- **Avg. Time to First Review**: {avg_ttr} (Median: {median_ttr})")
    report.append(f"- **Avg. Time to Close PR**: {avg_ttc} (Median: {median_ttc})")
    report.append(f"- **Avg. PR Size (lines)**: {avg_size} (Median: {median_size})")

    if stats["prs_over_48h_to_review"]:
        report.append("\n### PRs taking >48 business hours for first review:")
        report.extend([f"  - {url}" for url in stats["prs_over_48h_to_review"]])
    
    if stats["prs_over_48h_to_close"]:
        report.append("\n### PRs taking >48 business hours to close:")
        report.extend([f"  - {url}" for url in stats["prs_over_48h_to_close"]])

    report.append("\n---\n")
    report.append("## 🧑‍💻 Team Member Statistics\n")

    for member, m_stats in member_stats.items():
        report.append(f"### {member}\n")
        m_avg_ttr, m_median_ttr = get_avg_and_median(m_stats["time_to_first_review"], time_format=True)
        m_avg_ttc, m_median_ttc = get_avg_and_median(m_stats["time_to_close"], time_format=True)
        m_avg_size, m_median_size = get_avg_and_median(m_stats["lines_changed"])

        report.append(f"- **Opened PRs**: {m_stats['opened']} (Currently open: {len(m_stats['open_prs'])})")
        report.append(f"- **Reviewed PRs**: {m_stats['reviewed']}")
        report.append(f"- **PRs Assigned for Review**: {m_stats['assigned_for_review']}")
        report.append(f"- **Avg. Time to First Review**: {m_avg_ttr} (Median: {m_median_ttr})")
        report.append(f"- **Avg. Time to Close PR**: {m_avg_ttc} (Median: {m_median_ttc})")
        report.append(f"- **Avg. PR Size (lines)**: {m_avg_size} (Median: {m_median_size})\n")

    return "\n".join(report)


def main():
    """Main function to generate PR metrics report."""
    token, repo_name, team_members, excluded_labels = get_env_vars()

    auth = Auth.Token(token)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    pulls = repo.get_pulls(state='all', sort='created', direction='desc')
    
    repo_stats, member_stats = analyze_pulls(pulls, team_members, excluded_labels)
    report_md = generate_report(repo_name, repo_stats, member_stats)

    with open("pr_metrics_report.md", "w") as f:
        f.write(report_md)

    print("Successfully generated PR metrics report.")

if __name__ == "__main__":
    main()
