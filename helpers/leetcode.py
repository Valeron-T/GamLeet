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


def fetch_daily_problem():
    url = "https://leetcode.com/graphql"

    current_year = datetime.now().year
    current_month = datetime.now().month

    payload = f'{{"operationName":"codingChallengeMedal","variables":{{"year":{current_year},"month":{current_month}}},"query":"query codingChallengeMedal($year: Int!, $month: Int!) {{  dailyChallengeMedal(year: $year, month: $month) {{    name    config {{      icon      __typename    }}    __typename  }}  activeDailyCodingChallengeQuestion {{    link    __typename  }}}}"}}'
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "origin": "https://leetcode.com",
        "priority": "u=1, i",
        "referer": "https://leetcode.com/explore/",
        "sec-ch-ua-arch": "x86",
        "sec-ch-ua-bitness": "64",
        "sec-ch-ua-full-version-list": '"Brave";v="135.0.0.0", "Not-A.Brand";v="8.0.0.0", "Chromium";v="135.0.0.0"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    }

    response = requests.request("POST", url, data=payload, headers=headers)
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    link = "https://leetcode.com" + response.json()['data']['activeDailyCodingChallengeQuestion']['link'] + f"?envType=daily-question&envId={today_date}"

    return link

# print(fetch_daily_problem())