from datetime import datetime
import os
import pytz
import requests
import uuid

def is_leetcode_solved_today():
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.6",
        "authorization": "",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "priority": "u=1, i",
        "random-uuid": str(uuid.uuid4()),
        "referer": f'https://leetcode.com/u/{os.getenv("LEETCODE_USERNAME")}/',
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    json_data = {
        "query": "\n    query recentAcSubmissions($username: String!, $limit: Int!) {\n  recentAcSubmissionList(username: $username, limit: $limit) {\n    id\n    title\n    titleSlug\n    timestamp\n  }\n}\n    ",
        "variables": {
            "username": os.getenv("LEETCODE_USERNAME"),
            "limit": 15,
        },
        "operationName": "recentAcSubmissions",
    }

    response = requests.post(
        "https://leetcode.com/graphql/", headers=headers, json=json_data
    )
    latest_submission = response.json()["data"]["recentAcSubmissionList"][0]
    submission_time = int(latest_submission["timestamp"])
    submission_date = datetime.fromtimestamp(
        submission_time, pytz.timezone("Asia/Kolkata")
    ).date()
    today_date = datetime.now(pytz.timezone("Asia/Kolkata")).date()

    return submission_date == today_date