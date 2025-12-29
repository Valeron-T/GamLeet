import schedule
import time
from threading import Thread
from helpers.leetcode import is_leetcode_solved_today
from helpers.mails import build_penalty_email
from kite import generate_session
from kiteconnect.exceptions import InputException
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
import os
import resend
from security import decrypt_token
from models import User, UserStat

resend.api_key = os.getenv("RESEND_API_KEY")

def check_all_users_dsa(db: Session):
    print("Running daily DSA completion check for all users...")
    users = db.query(User).all()
    for user in users:
        try:
            check_dsa_completion(user, db)
        except Exception as e:
            print(f"Error checking DSA completion for user {user.id}: {e}")

def check_dsa_completion(user: User, db: Session):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        return

    from helpers.problems import get_curated_problems_for_user
    from helpers.leetcode import get_problems_status, is_leetcode_solved_today
    from models import QuestionCompletion

    today = datetime.now().date()
    today_str = today.isoformat()
    
    curated_problems = get_curated_problems_for_user(db, user, today_str)
    curated_slugs = [p["slug"] for p in curated_problems.values() if p and "slug" in p]
    
    # 1. Check curated problems status
    status_map = get_problems_status(curated_slugs, username=user.leetcode_username, session=user.leetcode_session)
    
    rewards_granted = False
    
    # Use lowercase keys for easier matching
    reward_config = {
        "easy": {"coins": 10, "xp": 50},
        "medium": {"coins": 25, "xp": 100},
        "hard": {"coins": 50, "xp": 200}
    }

    for diff_key, problem in curated_problems.items():
        if not problem:
            continue
            
        slug = problem["slug"]
        difficulty = problem["difficulty"] # e.g. "Easy"
        
        if status_map.get(slug) == "completed":
            # Check if already rewarded
            question_id = problem["id"]
            already_rewarded = db.query(QuestionCompletion).filter(
                QuestionCompletion.user_id == user.id,
                QuestionCompletion.question_id == question_id
            ).first()
            
            if not already_rewarded:
                print(f"User {user.id} completed curated problem {slug} ({difficulty}). Granting rewards.")
                # Map difficulty to lowercase for lookup
                lookup_diff = difficulty.lower()
                rewards = reward_config.get(lookup_diff, {"coins": 0, "xp": 0})
                
                if rewards["coins"] > 0:
                    stats.gamcoins += rewards["coins"]
                    stats.total_xp += rewards["xp"]
                    
                    # Record completion
                    completion = QuestionCompletion(user_id=user.id, question_id=question_id)
                    db.add(completion)
                    rewards_granted = True
                    print(f"Rewards granted for {slug}: +{rewards['coins']} GC, +{rewards['xp']} XP")
                else:
                    print(f"Warning: No rewards config found for difficulty: {difficulty}")

    # 2. Handle Streak / Streak Maintenance logic
    dsa_solved = is_leetcode_solved_today(username=user.leetcode_username, session=user.leetcode_session)
    
    mode = stats.difficulty_mode.lower()

    if dsa_solved:
        if stats.last_activity_date == today:
            if rewards_granted:
                db.commit()
            return

        print(f"DSA solved today. Updating streak stats for user {user.id}")
        stats.problems_solved += 1
        stats.problems_since_last_life += 1
        stats.last_activity_date = today
        
        if stats.problems_since_last_life >= 7:
            max_lives = 5 if mode == "normal" else 1 if mode == "hardcore" else 0
            if max_lives > 0 and stats.lives < max_lives:
                stats.lives += 1
            stats.problems_since_last_life = 0
        
        db.commit()
        return
    
    if rewards_granted:
        db.commit()

    # Penalty Logic
    if mode == "sandbox":
        return

    should_execute_penalty = False
    if mode == "hardcore" or mode == "god":
        should_execute_penalty = True
    elif mode == "normal":
        if stats.lives > 0:
            stats.lives -= 1
            db.commit()
            if stats.lives == 0:
                should_execute_penalty = True
        else:
            should_execute_penalty = True

    if should_execute_penalty:
        execute_zerodha_penalty(user, db)

def execute_zerodha_penalty(user, db: Session):
    if not user.access_token or not user.zerodha_api_key:
        print(f"User {user.id} has no Zerodha credentials set. Skipping penalty.")
        return

    from kite import get_kite_client
    from security import decrypt_token
    
    kite_client = get_kite_client(decrypt_token(user.zerodha_api_key))
    kite_client.set_access_token(decrypt_token(user.access_token))

    try:
        order_id = kite_client.place_order(
            variety=kite_client.VARIETY_REGULAR,
            tradingsymbol="IDEA",
            exchange=kite_client.EXCHANGE_NSE,
            transaction_type=kite_client.TRANSACTION_TYPE_BUY,
            quantity=1, # Reduce to 1 for generic safety
            order_type=kite_client.ORDER_TYPE_MARKET,
            product=kite_client.PRODUCT_CNC,
            validity=kite_client.VALIDITY_DAY,
        )
        print(f"Penalty order placed for user {user.id}. Order ID: {order_id}")
        resend.Emails.send(build_penalty_email())
    except InputException as e:
        if "Markets are closed right now." in str(e):
            try:
                order_id = kite_client.place_order(
                    variety=kite_client.VARIETY_AMO,
                    tradingsymbol="IDEA",
                    exchange=kite_client.EXCHANGE_NSE,
                    transaction_type=kite_client.TRANSACTION_TYPE_BUY,
                    quantity=1,
                    order_type=kite_client.ORDER_TYPE_MARKET,
                    product=kite_client.PRODUCT_CNC,
                    validity=kite_client.VALIDITY_DAY,
                )
                print(f"Penalty AMO order placed for user {user.id}. Order ID: {order_id}")
                resend.Emails.send(build_penalty_email())
            except Exception as ex:
                print(f"Failed to place penalty AMO order for user {user.id}: {ex}")
    except Exception as e:
        print(f"Failed to place penalty order for user {user.id}: {e}")

def daily_reset(db: Session):
    print("Performing daily reset...")
    db.query(UserStat).update({UserStat.powerups_used_today: 0})
    db.commit()


def schedule_daily_check(db):
    def job_wrapper():
        india_tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(india_tz)
        if now.strftime("%H:%M") == "15:00":
            check_all_users_dsa(db)
        if now.strftime("%H:%M") == "00:00":
            daily_reset(db)

    schedule.every().minute.do(job_wrapper)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    Thread(target=run_scheduler, daemon=True).start()
