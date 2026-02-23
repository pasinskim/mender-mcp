# src/mcp_server_mender/pr_metrics.py
import os
from datetime import datetime, timedelta
from github import Github

def get_env_vars():
    """Get and validate required environment variables."""
    token = os.environ.get("GH_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    team_slug = os.environ.get("TEAM_SLUG")
    excluded_labels_str = os.environ.get("EXCLUDED_LABELS", "")

    if not all([token, repo_name, team_slug]):
        raise ValueError("Missing one or more required environment variables: GH_TOKEN, GITHUB_REPOSITORY, TEAM_SLUG")

    excluded_labels = {label.strip() for label in excluded_labels_str.split(",") if label.strip()}
    return token, repo_name, team_slug, excluded_labels

def is_weekend(date):
    """Check if a date is on a weekend."""
    return date.weekday() >= 5  # Saturday or Sunday

def get_business_timedelta(start, end):
    """Calculate the timedelta excluding weekends."""
    total_hours = 0
    current = start
    while current < end:
        if not is_weekend(current):
            total_hours += 1
        current += timedelta(hours=1)
    return timedelta(hours=total_hours)

def main():
    """Main function to generate PR metrics report."""
    token, repo_name, team_slug, excluded_labels = get_env_vars()

    g = Github(token)
    repo = g.get_repo(repo_name)
    org_name = repo_name.split('/')[0]
    team = g.get_organization(org_name).get_team_by_slug(team_slug)
    team_members = {member.login for member in team.get_members()}

    thirty_days_ago = datetime.now() - timedelta(days=30)
    pulls = repo.get_pulls(state='all', sort='created', direction='desc')

    report_lines = [f"# PR Metrics Report for `{repo_name}`", f"## Team: `{team_slug}`"]
    
    stale_prs = []
    member_stats = {member: {"opened": 0, "reviewed": 0, "review_times": [], "time_to_first_review": []} for member in team_members}
    
    for pr in pulls:
        if pr.created_at < thirty_days_ago:
            break
        if any(label.name in excluded_labels for label in pr.labels):
            continue

        author = pr.user.login
        if author in team_members:
            member_stats[author]["opened"] += 1

        first_review_time = None
        reviews = list(pr.get_reviews())
        for review in reviews:
            reviewer = review.user.login
            if reviewer in team_members:
                member_stats[reviewer]["reviewed"] += 1
                if first_review_time is None:
                    first_review_time = review.submitted_at
                    time_to_review = get_business_timedelta(pr.created_at, first_review_time)
                    member_stats[reviewer]["time_to_first_review"].append(time_to_review)

        if pr.state == 'open' and not reviews:
            wait_time = get_business_timedelta(pr.created_at, datetime.now())
            if wait_time > timedelta(hours=48):
                stale_prs.append(f"- [#{pr.number}]({pr.html_url}) by {author} - waiting {wait_time.days}d {wait_time.seconds//3600}h")

    report_lines.append("---")
    report_lines.append("## Team Member Statistics")
    for member, stats in member_stats.items():
        report_lines.append(f"### {member}")
        report_lines.append(f"- **PRs Opened**: {stats['opened']}")
        report_lines.append(f"- **PRs Reviewed**: {stats['reviewed']}")
        if stats['time_to_first_review']:
            avg_time = sum(stats['time_to_first_review'], timedelta()) / len(stats['time_to_first_review'])
            report_lines.append(f"- **Avg. Time to First Review**: {avg_time.days}d {avg_time.seconds//3600}h")
    
    if stale_prs:
        report_lines.append("---")
        report_lines.append("## PRs Awaiting Review (> 48 business hours)")
        report_lines.extend(stale_prs)

    with open("pr_metrics_report.md", "w") as f:
        f.write("\n".join(report_lines))

    print("Successfully generated PR metrics report.")

if __name__ == "__main__":
    main()
