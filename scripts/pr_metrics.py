# scripts/pr_metrics.py
import os
from datetime import datetime, timedelta, timezone
from github import Github, Auth
import statistics
from collections import defaultdict

def get_env_vars():
    """Get and validate required environment variables."""
    token = os.environ.get("GH_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    # TEAM_MEMBERS is no longer required as we discover users dynamically
    excluded_labels_str = os.environ.get("EXCLUDED_LABELS", "")

    if not all([token, repo_name]):
        raise ValueError("Missing one or more required environment variables: GH_TOKEN, GITHUB_REPOSITORY")

    excluded_labels = {label.strip() for label in excluded_labels_str.split(",") if label.strip()}
    return token, repo_name, excluded_labels

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
    if td is None: return "None"
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def get_stats(data):
    """Calculate Average, Median, and 90th Percentile for a list of timedeltas."""
    if not data:
        return "None", "None", "None"
    
    seconds = [td.total_seconds() for td in data if td]
    if not seconds:
        return "None", "None", "None"

    avg = statistics.mean(seconds)
    med = statistics.median(seconds)
    p90 = statistics.quantiles(seconds, n=10)[8] if len(seconds) >= 2 else seconds[0]

    return (
        format_timedelta(timedelta(seconds=avg)),
        format_timedelta(timedelta(seconds=med)),
        format_timedelta(timedelta(seconds=p90))
    )

def analyze_pulls(repo, excluded_labels):
    """Analyzes pull requests and returns structured stats."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pulls = repo.get_pulls(state='all', sort='created', direction='desc')
    
    processed_prs = []
    user_stats = defaultdict(lambda: {"opened": 0, "reviewed": 0, "assigned": 0})

    for pr in pulls:
        if pr.created_at < thirty_days_ago: break
        if any(label.name in excluded_labels for label in pr.labels): continue

        pr_data = {
            "title": pr.title,
            "url": pr.html_url,
            "number": pr.number,
            "author": pr.user.login,
            "assignees": [a.login for a in pr.assignees],
            "state": pr.state,
            "created_at": pr.created_at,
            "time_to_first_review": None,
            "time_to_close": None,
            "time_to_answer": None # Placeholder if we track comments later
        }

        # Track Author Activity
        user_stats[pr.user.login]["opened"] += 1

        # Track Assignee Activity
        for assignee in pr.assignees:
            user_stats[assignee.login]["assigned"] += 1

        # Calculate Time to Close
        if pr.state == 'closed' and pr.closed_at:
            pr_data["time_to_close"] = get_business_timedelta(pr.created_at, pr.closed_at)

        # Process Reviews
        reviews = list(pr.get_reviews())
        reviewers_in_pr = set()
        
        if reviews:
            # Sort reviews by submitted_at just in case
            reviews.sort(key=lambda x: x.submitted_at)
            first_review = reviews[0]
            pr_data["time_to_first_review"] = get_business_timedelta(pr.created_at, first_review.submitted_at)
            # Use TTR as "Time to Answer" proxy for now
            pr_data["time_to_answer"] = pr_data["time_to_first_review"]

            for review in reviews:
                reviewer = review.user.login
                # Exclude author from review stats on their own PR (though unlikely to happen)
                if reviewer != pr.user.login and reviewer not in reviewers_in_pr:
                    user_stats[reviewer]["reviewed"] += 1
                    reviewers_in_pr.add(reviewer)
        
        processed_prs.append(pr_data)
    
    return processed_prs, user_stats

def generate_report(repo_name, processed_prs, user_stats):
    """Generates a markdown report from the processed PR data."""
    report = [f"# Issue Metrics for `{repo_name}`\n"]

    # --- Metrics Summary Table ---
    report.append("## Metrics Summary\n")
    report.append("| Metric | Average | Median | 90th percentile |")
    report.append("|---|---|---|---|")

    ttr_list = [pr["time_to_first_review"] for pr in processed_prs if pr["time_to_first_review"]]
    ttc_list = [pr["time_to_close"] for pr in processed_prs if pr["time_to_close"]]
    tta_list = [pr["time_to_answer"] for pr in processed_prs if pr["time_to_answer"]]

    ttr_stats = get_stats(ttr_list)
    ttc_stats = get_stats(ttc_list)
    tta_stats = get_stats(tta_list)

    report.append(f"| Time to first response | {ttr_stats[0]} | {ttr_stats[1]} | {ttr_stats[2]} |")
    report.append(f"| Time to close | {ttc_stats[0]} | {ttc_stats[1]} | {ttc_stats[2]} |")
    report.append(f"| Time to answer | {tta_stats[0]} | {tta_stats[1]} | {tta_stats[2]} |")

    # --- Counts Table ---
    open_count = sum(1 for pr in processed_prs if pr["state"] == "open")
    closed_count = sum(1 for pr in processed_prs if pr["state"] == "closed")
    total_count = len(processed_prs)

    report.append("\n## Activity Counts\n")
    report.append("| Metric | Count |")
    report.append("|---|---|")
    report.append(f"| Number of items that remain open | {open_count} |")
    report.append(f"| Number of items closed | {closed_count} |")
    report.append(f"| Total number of items created | {total_count} |")

    # --- User Activity Table ---
    report.append("\n## Team Activity\n")
    report.append("| User | PRs Opened | PRs Assigned | Reviews Given |")
    report.append("|---|---|---|---|")
    
    # Filter active users (at least one activity)
    active_users = {u: s for u, s in user_stats.items() if s["opened"] > 0 or s["assigned"] > 0 or s["reviewed"] > 0}
    
    # Sort by activity (opened + reviewed + assigned) descending
    sorted_users = sorted(active_users.items(), key=lambda x: (x[1]["opened"] + x[1]["reviewed"] + x[1]["assigned"]), reverse=True)

    for user, stats in sorted_users:
        report.append(f"| {user} | {stats['opened']} | {stats['assigned']} | {stats['reviewed']} |")

    # --- PR List Table ---
    report.append("\n## Processed Items\n")
    report.append("| Title | URL | Assignee | Author | Time to first response | Time to close | Time to answer |")
    report.append("|---|---|---|---|---|---|---|")

    for pr in processed_prs:
        assignees_str = ", ".join(pr["assignees"]) if pr["assignees"] else "None"
        ttr = format_timedelta(pr["time_to_first_review"])
        ttc = format_timedelta(pr["time_to_close"])
        tta = format_timedelta(pr["time_to_answer"])
        
        # Truncate title if too long for table
        title = pr["title"]
        if len(title) > 50:
            title = title[:47] + "..."
            
        report.append(f"| {title} | [#{pr['number']}]({pr['url']}) | {assignees_str} | {pr['author']} | {ttr} | {ttc} | {tta} |")

    report.append(f"\n_Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    return "\n".join(report)

def main():
    """Main function to generate PR metrics report."""
    try:
        token, repo_name, excluded_labels = get_env_vars()
        auth = Auth.Token(token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)

        print(f"Analyzing repository: {repo_name}")
        processed_prs, user_stats = analyze_pulls(repo, excluded_labels)
        report_md = generate_report(repo_name, processed_prs, user_stats)

        with open("pr_metrics_report.md", "w") as f:
            f.write(report_md)

        print("Successfully generated PR metrics report.")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
