import random
import time
import requests
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from dependencies import verify_api_key
from models import Questions

cookies = {
    "csrftoken": "bBwUtHX4wvL8DGhoYXdm370e963x5dnuIFCe8BtZkUilabCRppeT9U04oPHuw0Ig",
    "ip_check": '(false, "111.125.253.162")',
    "LEETCODE_SESSION": os.getenv("LEETCODE_SESSION"),
    "INGRESSCOOKIE": "ca32d585127c97b652dbe419e1c3f8a2|8e0876c7c1464cc0ac96bc2edceabd27",
}

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.5",
    "authorization": "",
    "content-type": "application/json",
    "origin": "https://leetcode.com",
    "priority": "u=1, i",
    "random-uuid": "1af3788d-cc2c-2a6f-adc6-1af00990f0a8",
    "referer": "https://leetcode.com/problemset/",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version-list": '"Chromium";v="140.0.0.0", "Not=A?Brand";v="24.0.0.0", "Brave";v="140.0.0.0"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Linux"',
    "sec-ch-ua-platform-version": '"6.8.0"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-gpc": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
}
leetcode_data_router = APIRouter()


@leetcode_data_router.get("/test")
async def load_leetcode_questions(db: Session = Depends(get_db)):
    has_more = True
    offset = 0
    while has_more:
        json_data = {
            "query": "\n    query problemsetQuestionListV2($filters: QuestionFilterInput, $limit: Int, $searchKeyword: String, $skip: Int, $sortBy: QuestionSortByInput, $categorySlug: String) {\n  problemsetQuestionListV2(\n    filters: $filters\n    limit: $limit\n    searchKeyword: $searchKeyword\n    skip: $skip\n    sortBy: $sortBy\n    categorySlug: $categorySlug\n  ) {\n    questions {\n      id\n      titleSlug\n      title\n      translatedTitle\n      questionFrontendId\n      paidOnly\n      difficulty\n      topicTags {\n        name\n        slug\n        nameTranslated\n      }\n      status\n      isInMyFavorites\n      frequency\n      acRate\n      contestPoint\n    }\n    totalLength\n    finishedLength\n    hasMore\n  }\n}\n    ",
            "variables": {
                "skip": offset,
                "limit": 100,
                "categorySlug": "all-code-essentials",
                "filters": {
                    "filterCombineType": "ALL",
                    "statusFilter": {
                        "questionStatuses": [],
                        "operator": "IS",
                    },
                    "difficultyFilter": {
                        "difficulties": [],
                        "operator": "IS",
                    },
                    "languageFilter": {
                        "languageSlugs": [],
                        "operator": "IS",
                    },
                    "topicFilter": {
                        "topicSlugs": [],
                        "operator": "IS",
                    },
                    "acceptanceFilter": {},
                    "frequencyFilter": {},
                    "frontendIdFilter": {},
                    "lastSubmittedFilter": {},
                    "publishedFilter": {},
                    "companyFilter": {
                        "companySlugs": [],
                        "operator": "IS",
                    },
                    "positionFilter": {
                        "positionSlugs": [],
                        "operator": "IS",
                    },
                    "contestPointFilter": {
                        "contestPoints": [],
                        "operator": "IS",
                    },
                    "premiumFilter": {
                        "premiumStatus": [],
                        "operator": "IS",
                    },
                },
                "searchKeyword": "",
                "sortBy": {
                    "sortField": "FRONTEND_ID",
                    "sortOrder": "ASCENDING",
                },
                "filtersV2": {
                    "filterCombineType": "ALL",
                    "statusFilter": {
                        "questionStatuses": [],
                        "operator": "IS",
                    },
                    "difficultyFilter": {
                        "difficulties": [],
                        "operator": "IS",
                    },
                    "languageFilter": {
                        "languageSlugs": [],
                        "operator": "IS",
                    },
                    "topicFilter": {
                        "topicSlugs": [],
                        "operator": "IS",
                    },
                    "acceptanceFilter": {},
                    "frequencyFilter": {},
                    "frontendIdFilter": {},
                    "lastSubmittedFilter": {},
                    "publishedFilter": {},
                    "companyFilter": {
                        "companySlugs": [],
                        "operator": "IS",
                    },
                    "positionFilter": {
                        "positionSlugs": [],
                        "operator": "IS",
                    },
                    "contestPointFilter": {
                        "contestPoints": [],
                        "operator": "IS",
                    },
                    "premiumFilter": {
                        "premiumStatus": [],
                        "operator": "IS",
                    },
                },
            },
            "operationName": "problemsetQuestionListV2",
        }

        response = requests.post(
            "https://leetcode.com/graphql/", headers=headers, json=json_data
        )

        questions = (
            response.json()
            .get("data", {})
            .get("problemsetQuestionListV2", {})
            .get("questions", [])
        )
        for question in questions:
            question_id = question.get("id")
            title = question.get("title")
            title_slug = question.get("titleSlug")
            acc_rate = question.get("acRate")
            paid_only = question.get("paidOnly")
            difficulty = question.get("difficulty")
            topics = ", ".join(tag.get("name") for tag in question.get("topicTags", []))
            print(
                f"ID: {question_id}-{difficulty}, TitleSlug: {title_slug}, AccRate: {acc_rate}, PaidOnly: {paid_only}, Topics: {topics}"
            )

         # Build insert statement
        existing_ids = {
            q.id for q in db.query(Questions.id).all()
        }

        new_objs = []
        for q in questions:
            q_data = {
                "title": q["title"],
                "slug": q["titleSlug"],
                "acc_rate": q["acRate"],
                "paid_only": q["paidOnly"],
                "difficulty": q["difficulty"],
                "topics": ", ".join(tag["name"] for tag in q.get("topicTags", [])),
            }

            if q["id"] in existing_ids:
                db.query(Questions).filter_by(id=q["id"]).update(q_data)
            else:
                q_data["id"] = q["id"]
                new_objs.append(Questions(**q_data))

        if new_objs:
            db.bulk_save_objects(new_objs)

        db.commit()
        
        has_more = response.json()['data']['problemsetQuestionListV2']['hasMore']
        offset += 100
        time.sleep(random.uniform(0,0.5))
        
        
    return {"msg":"Data Loaded successfully"}
