from datetime import datetime
import os
import pytz
import requests
import httpx
import uuid
import json
import base64
import asyncio


def extract_uuuserid(session_jwt: str) -> str | None:
    try:
        parts = session_jwt.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)
            device_with_ip = payload.get("device_with_ip")
            if (
                device_with_ip
                and isinstance(device_with_ip, list)
                and len(device_with_ip) > 0
            ):
                return str(device_with_ip[0])
    except Exception:
        pass
    return None


def is_leetcode_solved_today(
    username: str = None, session: str = None, daily_slug: str = None
):
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
        "referer": f"https://leetcode.com/u/{username}/",
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
                "https://leetcode.com/graphql/",
                headers=headers,
                json=json_data,
                cookies=cookies,
                timeout=15,
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
                if (
                    sub["titleSlug"] == daily_slug
                    and sub["statusDisplay"] == "Accepted"
                ):
                    # Potentially check timestamp if needed, but recent list (limit 30) is usually fresh enough
                    return True
            return False

        except Exception as e:
            print(f"Error checking daily problem status: {e}")
            return False

    # Fallback to generic "any submission made today" logic
    json_data = {
        "query": """
        query recentSubmissions($username: String!, $limit: Int!) {
            recentSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
            }
        }
        """,
        "variables": {
            "username": username,
            "limit": 15,
        },
        "operationName": "recentSubmissions",
    }

    try:
        response = requests.post(
            "https://leetcode.com/graphql/",
            headers=headers,
            json=json_data,
            cookies=cookies,
            timeout=15,
        )
        data = response.json().get("data", {})
    except Exception as e:
        print(f"Error checking if LeetCode activity today: {e}")
        return False
    if not data or not data.get("recentSubmissionList"):
        return False

    latest_submission = data["recentSubmissionList"][0]
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
            "https://leetcode.com/graphql/",
            headers=headers,
            json=json_data,
            cookies=cookies,
            timeout=15,
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


async def get_problems_status_async(
    slugs: list[str], username: str = None, session: str = None
):
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
                cookies={k: v for k, v in cookies.items() if v is not None},
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
        response = requests.request(
            "POST", url, data=payload, headers=headers, timeout=15
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching daily problem: {e}")
        return {
            "link": "https://leetcode.com/problemset/all/",
            "slug": None,
            "title": "Daily Problem",
        }

    today_date = datetime.now().strftime("%Y-%m-%d")
    data = response.json()["data"]["activeDailyCodingChallengeQuestion"]
    link = (
        "https://leetcode.com"
        + data["link"]
        + f"?envType=daily-question&envId={today_date}"
    )

    return {
        "link": link,
        "slug": data["question"]["titleSlug"],
        "id": data["question"]["questionId"],
        "title": data["question"]["title"],
    }


async def fetch_all_solved_slugs(
    username: str = None, session: str = None
) -> list[str]:
    """Fetch all historically solved problem slugs for a user from LeetCode.

    Uses fetch_solved_problem_progress internally.
    """
    rows = await fetch_solved_problem_progress(username, session)
    return [row["titleSlug"] for row in rows if row.get("titleSlug")]


async def fetch_recent_submissions(
    username: str = None, session: str = None, limit: int = 20
) -> list[dict]:
    """Fetch recent LeetCode submissions directly from the user's profile.

    Returns both accepted and non-accepted submissions so the UI can show
    solves that were not part of GamLeet's curated problem set.
    """
    username = username or os.getenv("LEETCODE_USERNAME")
    if not username:
        return []

    base_headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "referer": f"https://leetcode.com/u/{username}/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    timeout = httpx.Timeout(30.0, read=30.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        if session:
            client.cookies.set(
                "LEETCODE_SESSION", session, domain=".leetcode.com", path="/"
            )
            uuuserid = extract_uuuserid(session)
            if uuuserid:
                client.cookies.set(
                    "uuuserid", uuuserid, domain=".leetcode.com", path="/"
                )
                base_headers["uuuserid"] = uuuserid

        try:
            await client.get(
                "https://leetcode.com",
                headers={"user-agent": base_headers["user-agent"]},
            )
            csrf_token = ""
            for cookie in client.cookies.jar:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                csrf_token = str(uuid.uuid4()).replace("-", "") * 2
                client.cookies.set(
                    "csrftoken", csrf_token, domain=".leetcode.com", path="/"
                )
            base_headers["x-csrftoken"] = csrf_token
        except Exception:
            csrf_token = str(uuid.uuid4()).replace("-", "") * 2
            client.cookies.set(
                "csrftoken", csrf_token, domain=".leetcode.com", path="/"
            )
            base_headers["x-csrftoken"] = csrf_token

        json_data = {
            "query": """
            query recentSubmissions($username: String!, $limit: Int!) {
                recentSubmissionList(username: $username, limit: $limit) {
                    id
                    title
                    titleSlug
                    statusDisplay
                    timestamp
                }
            }
            """,
            "variables": {"username": username, "limit": limit},
            "operationName": "recentSubmissions",
        }

        try:
            response = await client.post(
                "https://leetcode.com/graphql/",
                headers=base_headers,
                json=json_data,
            )
            data = response.json().get("data", {}).get("recentSubmissionList", [])
        except Exception as e:
            print(f"Error fetching recent submissions: {e}")
            return []

    submissions = []
    for sub in data or []:
        try:
            submissions.append(
                {
                    "id": sub.get("id"),
                    "title": sub.get("title"),
                    "slug": sub.get("titleSlug"),
                    "status": sub.get("statusDisplay"),
                    "timestamp": (
                        int(sub.get("timestamp"))
                        if sub.get("timestamp") is not None
                        else None
                    ),
                }
            )
        except Exception:
            continue

    return submissions


async def fetch_all_submissions(
    username: str | None = None,
    session: str | None = None,
    page_size: int = 20,
    since_timestamp: int | None = None,
) -> list[dict]:
    """Fetch the user's full submission history from LeetCode.

    LeetCode's `submissionList` endpoint is authenticated and paginated,
    so it is the durable source for a monthly submission archive.
    """
    username = username or os.getenv("LEETCODE_USERNAME")
    if not username or not session:
        return []

    base_headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "referer": f"https://leetcode.com/u/{username}/submissions/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    timeout = httpx.Timeout(30.0, read=30.0)
    submissions: list[dict] = []

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        client.cookies.set(
            "LEETCODE_SESSION", str(session), domain=".leetcode.com", path="/"
        )
        uuuserid = extract_uuuserid(str(session))
        if uuuserid:
            client.cookies.set("uuuserid", uuuserid, domain=".leetcode.com", path="/")
            base_headers["uuuserid"] = uuuserid

        try:
            await client.get(
                "https://leetcode.com",
                headers={"user-agent": base_headers["user-agent"]},
            )
            csrf_token = ""
            for cookie in client.cookies.jar:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                csrf_token = str(uuid.uuid4()).replace("-", "") * 2
                client.cookies.set(
                    "csrftoken", csrf_token, domain=".leetcode.com", path="/"
                )
            base_headers["x-csrftoken"] = csrf_token
        except Exception:
            csrf_token = str(uuid.uuid4()).replace("-", "") * 2
            client.cookies.set(
                "csrftoken", csrf_token, domain=".leetcode.com", path="/"
            )
            base_headers["x-csrftoken"] = csrf_token

        offset = 0
        while True:
            csrf_token = ""
            for cookie in client.cookies.jar:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                csrf_token = base_headers.get("x-csrftoken", "")
            base_headers["x-csrftoken"] = csrf_token

            json_data = {
                "query": """
                query submissionList($offset: Int!, $limit: Int!) {
                    submissionList(offset: $offset, limit: $limit) {
                        hasNext
                        submissions {
                            id
                            title
                            titleSlug
                            statusDisplay
                            timestamp
                        }
                    }
                }
                """,
                "variables": {"offset": offset, "limit": page_size},
                "operationName": "submissionList",
            }

            try:
                if offset > 0:
                    await asyncio.sleep(0.5)
                response = await client.post(
                    "https://leetcode.com/graphql/",
                    headers=base_headers,
                    json=json_data,
                )
                payload = response.json().get("data", {})
                submission_list = payload.get("submissionList") or {}
                page = submission_list.get("submissions") or []
                has_next = submission_list.get("hasNext")
            except Exception as e:
                print(f"Error fetching submission history: {e}")
                break

            if not page:
                break

            for sub in page:
                try:
                    timestamp = (
                        int(sub.get("timestamp"))
                        if sub.get("timestamp") is not None
                        else None
                    )
                    if (
                        since_timestamp is not None
                        and timestamp is not None
                        and timestamp < since_timestamp
                    ):
                        continue
                    submissions.append(
                        {
                            "id": sub.get("id"),
                            "title": sub.get("title"),
                            "slug": sub.get("titleSlug"),
                            "status": sub.get("statusDisplay"),
                            "timestamp": timestamp,
                        }
                    )
                except Exception:
                    continue

            offset += len(page)
            if since_timestamp is not None and page:
                oldest_timestamp = next(
                    (
                        int(sub.get("timestamp"))
                        for sub in reversed(page)
                        if sub.get("timestamp") is not None
                    ),
                    None,
                )
                if oldest_timestamp is not None and oldest_timestamp < since_timestamp:
                    break

            if has_next is False or len(page) < page_size:
                break

    return submissions




def _parse_leetcode_timestamp(value) -> int:
    if value is None or value == "":
        return 0

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(datetime.fromisoformat(value).timestamp())
            except ValueError:
                return 0

    return 0


async def fetch_solved_problem_progress(
    username: str | None = None, session: str | None = None
) -> list[dict]:
    """Fetch solved LeetCode problems with progress metadata.

    Returns dictionaries with at least:
      - titleSlug
      - questionStatus
      - lastSubmittedAt
      - numSubmitted

    This is useful when we need to sync solved problems within a time range
    without double counting rows already captured by GamLeet.
    """
    username = username or os.getenv("LEETCODE_USERNAME")
    if not username or not session:
        return []

    base_headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://leetcode.com",
        "referer": "https://leetcode.com/progress/",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    }

    timeout = httpx.Timeout(30.0, read=30.0)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        client.cookies.set(
            "LEETCODE_SESSION", session, domain=".leetcode.com", path="/"
        )
        uuuserid = extract_uuuserid(session)
        if uuuserid:
            client.cookies.set("uuuserid", uuuserid, domain=".leetcode.com", path="/")
            base_headers["uuuserid"] = uuuserid

        try:
            await client.get(
                "https://leetcode.com",
                headers={"user-agent": base_headers["user-agent"]},
            )
            csrf_token = ""
            for cookie in client.cookies.jar:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                csrf_token = str(uuid.uuid4()).replace("-", "") * 2
                client.cookies.set(
                    "csrftoken", csrf_token, domain=".leetcode.com", path="/"
                )
            base_headers["x-csrftoken"] = csrf_token
        except Exception:
            csrf_token = str(uuid.uuid4()).replace("-", "") * 2
            client.cookies.set(
                "csrftoken", csrf_token, domain=".leetcode.com", path="/"
            )
            base_headers["x-csrftoken"] = csrf_token

        query = """
        query userProgressQuestionList($filters: UserProgressQuestionListInput) {
          userProgressQuestionList(filters: $filters) {
            totalNum
            questions {
              titleSlug
              questionStatus
              lastSubmittedAt
              numSubmitted
              lastResult
            }
          }
        }
        """

        progress_rows: list[dict] = []
        skip = 0
        page_size = 50

        while True:
            csrf_token = ""
            for cookie in client.cookies.jar:
                if cookie.name == "csrftoken":
                    csrf_token = cookie.value
                    break
            if not csrf_token:
                csrf_token = base_headers.get("x-csrftoken", "")

            request_headers = dict(base_headers)
            request_headers["x-csrftoken"] = csrf_token
            request_headers["random-uuid"] = str(uuid.uuid4())
            request_headers["x-operation-name"] = "userProgressQuestionList"
            request_headers["referer"] = (
                f"https://leetcode.com/progress/?page={skip // page_size + 1}"
            )

            json_data = {
                "query": query,
                "variables": {"filters": {"skip": skip, "limit": page_size}},
                "operationName": "userProgressQuestionList",
            }

            try:
                if skip > 0:
                    await asyncio.sleep(0.5)
                response = await client.post(
                    "https://leetcode.com/graphql/",
                    headers=request_headers,
                    json=json_data,
                )
                if response.status_code != 200:
                    print(
                        f"Progress metadata fetch failed: status={response.status_code} page={skip // page_size + 1}"
                    )
                    break

                payload = response.json()
                if payload.get("errors"):
                    print(
                        f"Progress metadata GraphQL errors on page {skip // page_size + 1}: {payload.get('errors')}"
                    )

                data = payload.get("data", {})
                progress = data.get("userProgressQuestionList")
            except Exception as e:
                print(f"Error in progress metadata fetch: {e}")
                break

            if progress is None:
                break

            questions = progress.get("questions", [])
            if not questions:
                break

            for q in questions:
                if q.get("questionStatus") != "SOLVED":
                    continue
                progress_rows.append(
                    {
                        "titleSlug": q.get("titleSlug"),
                        "questionStatus": q.get("questionStatus"),
                        "lastSubmittedAt": q.get("lastSubmittedAt"),
                        "numSubmitted": q.get("numSubmitted"),
                        "lastResult": q.get("lastResult"),
                    }
                )

            skip += page_size
            total = progress.get("totalNum") or 0
            if total and skip >= total:
                break

        if not progress_rows:
            print("userProgressQuestionList API failed or returned empty. Falling back to recentAcSubmissionList...")
            fallback_slugs = await _fetch_via_recent_ac(client, base_headers, username)
            progress_rows = [
                {
                    "titleSlug": slug,
                    "questionStatus": "SOLVED",
                    "lastSubmittedAt": None,
                    "numSubmitted": None,
                    "lastResult": "AC",
                }
                for slug in fallback_slugs
            ]
        else:
            print(f"LeetCode progress API: {len(progress_rows)} solved problems fetched")

        progress_rows.sort(
            key=lambda row: _parse_leetcode_timestamp(row.get("lastSubmittedAt")),
            reverse=True,
        )

        return progress_rows


async def _fetch_via_recent_ac(
    client: httpx.AsyncClient, headers: dict, username: str
) -> list[str]:
    """Fallback: fetch solved slugs via recentAcSubmissionList (public API, limited results)."""
    json_data = {
        "query": """
        query recentAcSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                titleSlug
            }
        }
        """,
        "variables": {"username": username, "limit": 500},
        "operationName": "recentAcSubmissions",
    }

    try:
        response = await client.post(
            "https://leetcode.com/graphql/",
            headers=headers,
            json=json_data,
        )
        data = response.json().get("data", {}).get("recentAcSubmissionList", [])
        if data is None:
            data = []
    except Exception as e:
        print(f"Error in recentAcSubmissionList fallback: {e}")
        return []

    # Deduplicate
    seen = set()
    slugs = []
    for sub in data:
        slug = sub.get("titleSlug")
        if slug and slug not in seen:
            seen.add(slug)
            slugs.append(slug)

    return slugs


def recalculate_user_streak(user_id: int, db) -> int:
    """Recalculate the user's current and max streaks based on LeetCode submissions cache."""
    from models import LeetCodeSubmission, UserStat
    from datetime import datetime, timedelta
    import pytz

    stats = db.query(UserStat).filter(UserStat.user_id == user_id).first()
    if not stats:
        return 0

    # Retrieve all submissions
    submissions = (
        db.query(LeetCodeSubmission)
        .filter(
            LeetCodeSubmission.user_id == user_id,
            LeetCodeSubmission.timestamp.isnot(None),
        )
        .all()
    )

    tz = pytz.timezone("Asia/Kolkata")
    solved_dates = set()
    for sub in submissions:
        try:
            dt = datetime.fromtimestamp(sub.timestamp, tz)
            solved_dates.add(dt.date())
        except Exception:
            continue

    if not solved_dates:
        stats.current_streak = 0
        db.commit()
        return 0

    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    # A streak is active if the user solved a problem today or yesterday
    if today in solved_dates:
        start_date = today
    elif yesterday in solved_dates:
        start_date = yesterday
    else:
        stats.current_streak = 0
        db.commit()
        return 0

    current_streak = 0
    check_date = start_date
    while check_date in solved_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    stats.current_streak = current_streak
    if current_streak > stats.max_streak:
        stats.max_streak = current_streak

    db.commit()
    return current_streak



# print(fetch_daily_problem())
