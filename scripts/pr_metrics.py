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
    excluded_labels_str = os.environ.get("EXCLUDED_LABELS", "")
    sla_hours_str = os.environ.get("ACTIONABLE_SLA_HOURS", "48")

    if not all([token, repo_name]):
        raise ValueError("Missing one or more required environment variables: GH_TOKEN, GITHUB_REPOSITORY")

    excluded_labels = {label.strip() for label in excluded_labels_str.split(",") if label.strip()}
    
    try:
        sla_hours = int(sla_hours_str)
    except ValueError:
        print(f"Warning: Invalid ACTIONABLE_SLA_HOURS '{sla_hours_str}'. Defaulting to 48.")
        sla_hours = 48
        
    return token, repo_name, excluded_labels, sla_hours

def calculate_working_time(start, end):
    """
    Calculate the total duration between start and end, excluding weekends (Saturday/Sunday).
    Returns a timedelta.
    """
    if not start or not end:
        return None
    if start.tzinfo is None: start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None: end = end.replace(tzinfo=timezone.utc)

    if start > end:
        return timedelta(0)

    total_seconds = 0
    current = start

    # Iterate through time intervals, skipping weekends
    while current < end:
        # If current is a weekend, jump to the next Monday (or end of interval)
        if current.weekday() >= 5: # 5=Sat, 6=Sun
            next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            if next_day > end: 
                current = end
            else:
                current = next_day
            continue

        # Current is a weekday. Calculate time until next day or end of interval.
        next_day = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        chunk_end = min(next_day, end)
        
        # Add the duration of this chunk
        total_seconds += (chunk_end - current).total_seconds()
        
        # Move current forward
        current = chunk_end

    return timedelta(seconds=total_seconds)

def format_timedelta(td):
    """Format a timedelta into a readable string like '3d 4h 15m'."""
    if td is None: return "None"
    total_seconds = int(td.total_seconds())
    if total_seconds == 0: return "0m"
    
    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder %= 3600
    minutes = remainder // 60

    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    
    if not parts: return "<1m"
    return " ".join(parts)

def get_stats(data_list):
    """Calculate Average, Median, and 90th Percentile for a list of timedeltas."""
    seconds = [td.total_seconds() for td in data_list if td]
    if not seconds:
        return "None", "None", "None"

    avg = statistics.mean(seconds)
    med = statistics.median(seconds)
    
    # Calculate 90th percentile safely
    if len(seconds) >= 2:
        p90 = statistics.quantiles(seconds, n=10)[8]
    else:
        p90 = seconds[0]

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
    # User stats structure: 
    # { user: { 'opened': 0, 'reviewed': 0, 'assigned': 0, 'review_times': [], 'close_times': [] } }
    user_stats = defaultdict(lambda: {
        "opened": 0, "reviewed": 0, "assigned": 0, 
        "review_times": [], "close_times": []
    })

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
            "time_to_answer": None 
        }

        # --- Author Stats ---
        user_stats[pr.user.login]["opened"] += 1

        # --- Assignee Stats ---
        for assignee in pr.assignees:
            user_stats[assignee.login]["assigned"] += 1

        # --- Time to Close ---
        if pr.state == 'closed' and pr.closed_at:
            ttc = calculate_working_time(pr.created_at, pr.closed_at)
            pr_data["time_to_close"] = ttc
            user_stats[pr.user.login]["close_times"].append(ttc)

        # --- Review Timings ---
        # Fetch timeline to find when reviews were requested
        review_requests = {}
        try:
            # NOTE: Getting timeline can be expensive (API calls), but necessary for accurate "time from request"
            for event in pr.get_issue_events():
                if event.event == "review_requested" and event.requested_reviewer:
                    # Store the FIRST time a reviewer was requested
                    reviewer_name = event.requested_reviewer.login
                    if reviewer_name not in review_requests:
                        review_requests[reviewer_name] = event.created_at
        except Exception:
            # Fallback if issue events fail (e.g. permissions)
            pass

        # NOTE: pr.get_reviews() issues an API request per pull request. 
        # For repositories with a high volume of PRs, this may be expensive.
        reviews = list(pr.get_reviews())
        reviewers_in_pr = set()
        
        if reviews:
            # Sort reviews by submitted_at, handling potential None values defensively
            reviews.sort(key=lambda x: x.submitted_at or datetime.min.replace(tzinfo=timezone.utc))
            first_review = reviews[0]
            pr_data["time_to_first_review"] = calculate_working_time(pr.created_at, first_review.submitted_at)
            pr_data["time_to_answer"] = pr_data["time_to_first_review"]

            for review in reviews:
                reviewer = review.user.login
                if reviewer != pr.user.login and reviewer not in reviewers_in_pr:
                    user_stats[reviewer]["reviewed"] += 1
                    reviewers_in_pr.add(reviewer)

                    # Calculate individual time to review (from request to submission)
                    if reviewer in review_requests:
                        requested_at = review_requests[reviewer]
                        ttr = calculate_working_time(requested_at, review.submitted_at)
                        user_stats[reviewer]["review_times"].append(ttr)
        
        processed_prs.append(pr_data)
    
    return processed_prs, user_stats

def generate_report(repo_name, processed_prs, user_stats, sla_hours):
    """Generates a markdown report from the processed PR data."""
    report = [f"# PR Metrics for `{repo_name}`\n"]

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
    report.append(f"| Number of PRs that remain open | {open_count} |")
    report.append(f"| Number of PRs closed | {closed_count} |")
    report.append(f"| Total number of PRs created | {total_count} |")

    # --- User Activity Table ---
    report.append("\n## Team Activity\n")
    report.append("| User | PRs Opened | PRs Assigned | Reviews Given | Median Time to Review (Assigned -> Done) | Median Time to Close (As Author) |")
    report.append("|---|---|---|---|---|---|")
    
    # Filter active users
    active_users = {u: s for u, s in user_stats.items() if s["opened"] > 0 or s["assigned"] > 0 or s["reviewed"] > 0}
    sorted_users = sorted(active_users.items(), key=lambda x: (x[1]["opened"] + x[1]["reviewed"] + x[1]["assigned"]), reverse=True)

    for user, stats in sorted_users:
        # Calculate medians for individual stats
        med_ttr = "None"
        if stats["review_times"]:
            med_seconds = statistics.median([t.total_seconds() for t in stats["review_times"]])
            med_ttr = format_timedelta(timedelta(seconds=med_seconds))
            
        med_ttc = "None"
        if stats["close_times"]:
            med_seconds = statistics.median([t.total_seconds() for t in stats["close_times"]])
            med_ttc = format_timedelta(timedelta(seconds=med_seconds))

        report.append(f"| {user} | {stats['opened']} | {stats['assigned']} | {stats['reviewed']} | {med_ttr} | {med_ttc} |")

    # --- SLA Violations Table ---
    report.append(f"\n## ⚠️ PRs Needing Attention (>{sla_hours} business hours)\n")
    
    sla_td = timedelta(hours=sla_hours)
    
    # 1. Slow Reviews: 
    #    - Closed/Reviewed PRs where TTR > SLA
    #    - Open PRs with NO reviews where Age (working hours) > SLA
    
    slow_review_prs = []
    current_time = datetime.now(timezone.utc)
    
    for pr in processed_prs:
        # Case A: Review happened but took too long
        if pr["time_to_first_review"] and pr["time_to_first_review"] > sla_td:
            slow_review_prs.append({
                "pr": pr, 
                "reason": f"Review took {format_timedelta(pr['time_to_first_review'])}"
            })
        # Case B: No review yet, and PR age (working time) > SLA
        elif not pr["time_to_first_review"]:
             # Calculate current age in working hours
             age_working_hours = calculate_working_time(pr["created_at"], current_time)
             if age_working_hours and age_working_hours > sla_td:
                 slow_review_prs.append({
                     "pr": pr,
                     "reason": f"Waiting for review ({format_timedelta(age_working_hours)})"
                 })

    if slow_review_prs:
        report.append("### Slow Reviews\n")
        report.append("| PR | Author | Issue |")
        report.append("|---|---|---|")
        for item in slow_review_prs:
            pr = item["pr"]
            report.append(f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {item['reason']} |")
    else:
        report.append("### Slow Reviews\n")
        report.append("_None! 🎉_")


    # 2. Slow Closes:
    #    - Closed PRs where TTC > SLA
    #    - Open PRs where Age (working hours) > SLA
    
    slow_close_prs = []
    
    for pr in processed_prs:
        # Case A: Closed but took too long
        if pr["time_to_close"] and pr["time_to_close"] > sla_td:
             slow_close_prs.append({
                "pr": pr, 
                "reason": f"Took {format_timedelta(pr['time_to_close'])} to close"
            })
        # Case B: Still open and age > SLA
        elif pr["state"] == "open":
             age_working_hours = calculate_working_time(pr["created_at"], current_time)
             if age_working_hours and age_working_hours > sla_td:
                 slow_close_prs.append({
                     "pr": pr,
                     "reason": f"Open for {format_timedelta(age_working_hours)}"
                 })

    report.append("\n### Slow Resolutions\n")
    if slow_close_prs:
        report.append("| PR | Author | Issue |")
        report.append("|---|---|---|")
        for item in slow_close_prs:
            pr = item["pr"]
            report.append(f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {item['reason']} |")
    else:
        report.append("_None! 🎉_")


    # --- PR List Table ---
    report.append("\n## Processed PRs\n")
    report.append("| Title | URL | Assignee | Author | Time to first response | Time to close | Time to answer |")
    report.append("|---|---|---|---|---|---|---|")

    for pr in processed_prs:
        assignees_str = ", ".join(pr["assignees"]) if pr["assignees"] else "None"
        ttr = format_timedelta(pr["time_to_first_review"])
        ttc = format_timedelta(pr["time_to_close"])
        tta = format_timedelta(pr["time_to_answer"])
        
        title = pr["title"]
        if len(title) > 50:
            title = title[:47] + "..."
            
        report.append(f"| {title} | [#{pr['number']}]({pr['url']}) | {assignees_str} | {pr['author']} | {ttr} | {ttc} | {tta} |")

    report.append(f"\n_Report generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}_")
    return "\n".join(report)

def main():
    """Main function to generate PR metrics report."""
    try:
        token, repo_name, excluded_labels, sla_hours = get_env_vars()
        auth = Auth.Token(token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)

        print(f"Analyzing repository: {repo_name}")
        processed_prs, user_stats = analyze_pulls(repo, excluded_labels)
        report_md = generate_report(repo_name, processed_prs, user_stats, sla_hours)

        with open("pr_metrics_report.md", "w") as f:
            f.write(report_md)

        print("Successfully generated PR metrics report.")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
