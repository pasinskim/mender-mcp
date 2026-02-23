# scripts/pr_metrics.py
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
        return None
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)

    business_hours = 0
    current_date = start
    while current_date < end:
        if not is_weekend(current_date):
            business_hours += 1
        current_date += timedelta(hours=1)
    return timedelta(hours=business_hours)

def format_timedelta(td):
    """Format a timedelta into a readable string like '3d 4h 15m'."""
    if td is None: return "N/A"
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m"

def analyze_pulls(repo, team_members, excluded_labels):
    """Analyzes pull requests and returns structured stats."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pulls = repo.get_pulls(state='all', sort='created', direction='desc')
    
    processed_prs = []
    member_stats = {member: {
        "opened_count": 0, "reviewed_count": 0, "open_prs_count": 0, 
        "assigned_for_review_count": 0, "time_to_first_review": [], 
        "time_to_close": [], "lines_changed": []
    } for member in team_members}

    for pr in pulls:
        if pr.created_at < thirty_days_ago: break
        if any(label.name in excluded_labels for label in pr.labels): continue

        pr_data = {
            "url": pr.html_url, "number": pr.number, "title": pr.title, "author": pr.user.login,
            "state": pr.state, "created_at": pr.created_at, "lines": pr.additions + pr.deletions,
            "time_to_first_review": None, "time_to_close": None
        }

        author = pr.user.login
        if author in team_members:
            member_stats[author]["opened_count"] += 1
            member_stats[author]["lines_changed"].append(pr_data["lines"])
            if pr.state == 'open':
                member_stats[author]["open_prs_count"] += 1

        if pr.state == 'closed' and pr.closed_at:
            pr_data["time_to_close"] = get_business_timedelta(pr.created_at, pr.closed_at)
            if author in team_members:
                member_stats[author]["time_to_close"].append(pr_data["time_to_close"])
        
        if pr.requested_reviewers:
            for reviewer in pr.requested_reviewers:
                if reviewer.login in team_members:
                    member_stats[reviewer.login]["assigned_for_review_count"] += 1

        reviews = list(pr.get_reviews())
        reviewers_in_pr = set()
        if reviews:
            first_review = reviews[0]
            pr_data["time_to_first_review"] = get_business_timedelta(pr.created_at, first_review.submitted_at)
            
            for review in reviews:
                reviewer = review.user.login
                if reviewer in team_members and reviewer not in reviewers_in_pr:
                    member_stats[reviewer]["reviewed_count"] += 1
                    reviewers_in_pr.add(reviewer)
                    # Attribute first review time to the first team member who reviewed
                    if len(reviewers_in_pr) == 1:
                         member_stats[reviewer]["time_to_first_review"].append(pr_data["time_to_first_review"])
        
        processed_prs.append(pr_data)
    
    return processed_prs, member_stats

def generate_report(repo_name, processed_prs, member_stats):
    """Generates a markdown report from the processed PR data."""
    
    def get_avg_median_str(data, formatter=None):
        if not data: return "N/A"
        avg = statistics.mean(data)
        med = statistics.median(data)
        if formatter:
            return f"{formatter(timedelta(seconds=avg))} / {formatter(timedelta(seconds=med))}"
        return f"{avg:.1f} / {med:.1f}"

    report = [f"# PR Metrics Report for `{repo_name}`\n"]

    # --- Repo Summary Table ---
    closed_prs = [pr for pr in processed_prs if pr["state"] == "closed"]
    times_to_review_s = [pr["time_to_first_review"].total_seconds() for pr in processed_prs if pr["time_to_first_review"]]
    times_to_close_s = [pr["time_to_close"].total_seconds() for pr in closed_prs if pr["time_to_close"]]
    lines_changed = [pr["lines"] for pr in processed_prs]
    
    report.append("## 📈 Repository Summary (Last 30 Days)\n")
    report.append("| Metric | Value (Average / Median) |")
    report.append("|---|---|")
    report.append(f"| Open PRs | {len(processed_prs) - len(closed_prs)} |")
    report.append(f"| Closed PRs | {len(closed_prs)} |")
    report.append(f"| Time to First Review | {get_avg_median_str(times_to_review_s, format_timedelta)} |")
    report.append(f"| Time to Close PR | {get_avg_median_str(times_to_close_s, format_timedelta)} |")
    report.append(f"| PR Size (lines) | {get_avg_median_str(lines_changed)} |")

    # --- Individual Stats Table ---
    report.append("\n---\n## 🧑‍💻 Team Member Statistics\n")
    report.append("| Member | Opened | Reviewed | Assigned | Avg/Med TTR | Avg/Med TTC | Avg/Med Lines |")
    report.append("|---|---|---|---|---|---|---|")
    for member, stats in member_stats.items():
        ttr_s = [td.total_seconds() for td in stats["time_to_first_review"] if td]
        ttc_s = [td.total_seconds() for td in stats["time_to_close"] if td]
        lines = stats["lines_changed"]
        report.append(f"| {member} | {stats['opened_count']} | {stats['reviewed_count']} | {stats['assigned_for_review_count']} | {get_avg_median_str(ttr_s, format_timedelta)} | {get_avg_median_str(ttc_s, format_timedelta)} | {get_avg_median_str(lines)} |")

    # --- Long Running PRs Table ---
    report.append("\n---\n## ⚠️ PRs Needing Attention\n")
    long_review_prs = [pr for pr in processed_prs if pr["time_to_first_review"] and pr["time_to_first_review"] > timedelta(hours=48)]
    long_close_prs = [pr for pr in closed_prs if pr["time_to_close"] and pr["time_to_close"] > timedelta(hours=48)]

    report.append("### PRs > 48 business hours for first review\n")
    if long_review_prs:
        report.append("| PR | Author | Time to First Review |")
        report.append("|---|---|---|")
        for pr in long_review_prs:
            report.append(f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {format_timedelta(pr['time_to_first_review'])} |")
    else:
        report.append("_None! 🎉_")

    report.append("\n### PRs > 48 business hours to close\n")
    if long_close_prs:
        report.append("| PR | Author | Time to Close |")
        report.append("|---|---|---|")
        for pr in long_close_prs:
            report.append(f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {format_timedelta(pr['time_to_close'])} |")
    else:
        report.append("_None! 🎉_")

    return "\n".join(report)

def main():
    """Main function to generate PR metrics report."""
    token, repo_name, team_members, excluded_labels = get_env_vars()
    auth = Auth.Token(token)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    processed_prs, member_stats = analyze_pulls(repo, team_members, excluded_labels)
    report_md = generate_report(repo_name, processed_prs, member_stats)

    with open("pr_metrics_report.md", "w") as f:
        f.write(report_md)

    print("Successfully generated PR metrics report.")

if __name__ == "__main__":
    main()
