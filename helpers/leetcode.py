from datetime import datetime
import os
import pytz
import requests
import httpx
import uuid
import json


def is_leetcode_solved_today(username: str = None, session: str = None, daily_slug: str = None):
    # Use env as fallback for backward compatibility / single-tenant default
    username = username or os.getenv("LEETCODE_USERNAME")
    
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.6",
        "authorization": "",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "priority": "u=1, i",
        "random-uuid": str(uuid.uuid4()),
        "referer": f'https://leetcode.com/u/{username}/',
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    cookies = {}
    if session:
        cookies["LEETCODE_SESSION"] = session

    # If daily slug is provided, we check for that specifically
    if daily_slug:
         # Fetch recent submissions (both AC and non-AC)
        json_data = {
            "query": """
            query recentSubmissions($username: String!, $limit: Int!) {
                recentSubmissionList(username: $username, limit: $limit) {
                    titleSlug
                    statusDisplay
                    timestamp
                }
            }
            """,
            "variables": {
                "username": username,
                "limit": 30,
            },
            "operationName": "recentSubmissions",
        }
        
        try:
            response = requests.post(
                "https://leetcode.com/graphql/", headers=headers, json=json_data, cookies=cookies,
                timeout=15
            )
            data = response.json().get("data", {}).get("recentSubmissionList", [])
            
            # Check if any accepted submission matches the daily slug and is from today
            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
            # Daily reset is at 5:30 AM IST usually for global daily problem? Actually LeetCode daily resets at 00:00 UTC = 5:30 AM IST.
            # But the user logic handled 3:30 PM for some reason in get_problems_status.
            # Let's align with "today" in local time for simplicity or stick to the 3:30 PM logic if consistent.
            # However, for the OFFICIAL daily problem, it follows UTC.
            
            # Let's just check if it was solved "today" in standard terms roughly.
            # Or better, check if the timestamp matches the current daily problem day window.
            # For simplicity, let's just check if it appears in the recent list with 'Accepted' status.
            # Assuming people don't re-solve old dailies just for fun often, searching for slug in recent AC is decent.
            
            for sub in data:
                if sub["titleSlug"] == daily_slug and sub["statusDisplay"] == "Accepted":
                    # Potentially check timestamp if needed, but recent list (limit 30) is usually fresh enough
                    return True
            return False

        except Exception as e:
            print(f"Error checking daily problem status: {e}")
            return False

    # Fallback to generic "any problem solved today" logic
    json_data = {
        "query": "\n    query recentAcSubmissions($username: String!, $limit: Int!) {\n  recentAcSubmissionList(username: $username, limit: $limit) {\n    id\n    title\n    titleSlug\n    timestamp\n  }\n}\n    ",
        "variables": {
            "username": username,
            "limit": 15,
        },
        "operationName": "recentAcSubmissions",
    }

    try:
        response = requests.post(
            "https://leetcode.com/graphql/", headers=headers, json=json_data, cookies=cookies,
            timeout=15
        )
        data = response.json().get("data", {})
    except Exception as e:
        print(f"Error checking if LeetCode solved today: {e}")
        return False
    if not data or not data.get("recentAcSubmissionList"):
        return False
        
    latest_submission = data["recentAcSubmissionList"][0]
    submission_time = int(latest_submission["timestamp"])
    submission_date = datetime.fromtimestamp(
        submission_time, pytz.timezone("Asia/Kolkata")
    ).date()
    today_date = datetime.now(pytz.timezone("Asia/Kolkata")).date()

    return submission_date == today_date


def get_problems_status(slugs: list[str], username: str = None, session: str = None):
    username = username or os.getenv("LEETCODE_USERNAME")
    if not username:
        return {slug: "unattempted" for slug in slugs}

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "referer": f"https://leetcode.com/u/{username}/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    cookies = {}
    if session:
        cookies["LEETCODE_SESSION"] = session

    # Fetch recent submissions (both AC and non-AC)
    json_data = {
        "query": """
        query recentSubmissions($username: String!, $limit: Int!) {
            recentSubmissionList(username: $username, limit: $limit) {
                titleSlug
                statusDisplay
                timestamp
            }
        }
        """,
        "variables": {
            "username": username,
            "limit": 30,
        },
        "operationName": "recentSubmissions",
    }

    try:
        response = requests.post(
            "https://leetcode.com/graphql/", headers=headers, json=json_data, cookies=cookies,
            timeout=15
        )
        data = response.json().get("data", {}).get("recentSubmissionList", [])
    except Exception as e:
        print(f"Error fetching LeetCode status: {e}")
        return {slug: "unattempted" for slug in slugs}

    # Evaluation time (3:30 PM today or yesterday)
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    eval_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < eval_time:
        # If it's before 3:30 PM, the "day" started at 3:30 PM yesterday
        from datetime import timedelta
        eval_time = eval_time - timedelta(days=1)
    
    eval_timestamp = int(eval_time.timestamp())

    status_map = {slug: "unattempted" for slug in slugs}
    for sub in data:
        slug = sub["titleSlug"]
        if slug in status_map:
            sub_ts = int(sub["timestamp"])
            
            # Only count submissions after the last curation/evaluation reset
            if sub_ts >= eval_timestamp:
                if sub["statusDisplay"] == "Accepted":
                    status_map[slug] = "completed"
                elif status_map[slug] != "completed":
                    status_map[slug] = "attempted"
    return status_map


async def get_problems_status_async(slugs: list[str], username: str = None, session: str = None):
    username = username or os.getenv("LEETCODE_USERNAME")
    if not username:
        return {slug: "unattempted" for slug in slugs}

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "referer": f"https://leetcode.com/u/{username}/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    cookies = {}
    if session:
        cookies["LEETCODE_SESSION"] = session

    # Fetch recent submissions (both AC and non-AC)
    json_data = {
        "query": """
        query recentSubmissions($username: String!, $limit: Int!) {
            recentSubmissionList(username: $username, limit: $limit) {
                titleSlug
                statusDisplay
                timestamp
            }
        }
        """,
        "variables": {
            "username": username,
            "limit": 30,
        },
        "operationName": "recentSubmissions",
    }

    try:
        # Set a generous timeout for the async client
        timeout = httpx.Timeout(30.0, read=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # httpx uses 'cookies' as a Cookies object or dict, similar to requests
            # But let's verify if 'cookies' contains None or empty values
            response = await client.post(
                "https://leetcode.com/graphql/", 
                headers=headers, 
                json=json_data, 
                cookies={k: v for k, v in cookies.items() if v is not None}
            )
            data = response.json().get("data", {}).get("recentSubmissionList", [])
            if data is None:
                data = []
    except Exception as e:
        import traceback
        print(f"Error fetching LeetCode status async: {e}")
        traceback.print_exc()
        return {slug: "unattempted" for slug in slugs}

    # Evaluation time (3:30 PM today or yesterday)
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    eval_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < eval_time:
        # If it's before 3:30 PM, the "day" started at 3:30 PM yesterday
        from datetime import timedelta
        eval_time = eval_time - timedelta(days=1)
    
    eval_timestamp = int(eval_time.timestamp())

    status_map = {slug: "unattempted" for slug in slugs}
    for sub in data:
        slug = sub["titleSlug"]
        if slug in status_map:
            sub_ts = int(sub["timestamp"])
            
            # Only count submissions after the last curation/evaluation reset
            if sub_ts >= eval_timestamp:
                if sub["statusDisplay"] == "Accepted":
                    status_map[slug] = "completed"
                elif status_map[slug] != "completed":
                    status_map[slug] = "attempted"
    return status_map


def fetch_daily_problem():
    url = "https://leetcode.com/graphql"

    current_year = datetime.now().year
    current_month = datetime.now().month

    payload = f'{{"operationName":"codingChallengeMedal","variables":{{"year":{current_year},"month":{current_month}}},"query":"query codingChallengeMedal($year: Int!, $month: Int!) {{  dailyChallengeMedal(year: $year, month: $month) {{    name    config {{      icon      __typename    }}    __typename  }}  activeDailyCodingChallengeQuestion {{    link    question {{      questionId      titleSlug      title    }}    __typename  }}}}"}}'
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

    try:
        response = requests.request("POST", url, data=payload, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching daily problem: {e}")
        return {"link": "https://leetcode.com/problemset/all/", "slug": None, "title": "Daily Problem"}
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    data = response.json()['data']['activeDailyCodingChallengeQuestion']
    link = "https://leetcode.com" + data['link'] + f"?envType=daily-question&envId={today_date}"
    
    return {
        "link": link,
        "slug": data['question']['titleSlug'],
        "id": data['question']['questionId'],
        "title": data['question']['title']
    }

# print(fetch_daily_problem())