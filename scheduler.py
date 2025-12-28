import schedule
import time
from threading import Thread
from helpers.leetcode import is_leetcode_solved_today
from helpers.mails import build_penalty_email
from kite import kite_connect, generate_session
from kiteconnect.exceptions import InputException
from sqlalchemy.orm import Session
from datetime import datetime
import pytz
import os
import resend
from security import decrypt_token
from models import User, UserStat

resend.api_key = os.getenv("RESEND_API_KEY")

def check_dsa_completion(db: Session):
    user = db.query(User).first() # Single-tenant
    if not user:
        return
        
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
    
    print(f"Checking rewards for user {user.id}. Curated slugs: {curated_slugs}")
    
    # 1. Check curated problems status
    status_map = get_problems_status(curated_slugs, username=user.leetcode_username, session=user.leetcode_session)
    print(f"Status map for {user.leetcode_username}: {status_map}")
    
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
    # If ANY curated problem is solved OR any other problem is solved today
    dsa_solved = is_leetcode_solved_today(username=user.leetcode_username, session=user.leetcode_session)
    
    mode = stats.difficulty_mode.lower()

    if dsa_solved:
        if stats.last_activity_date == today:
            if rewards_granted:
                db.commit()
            print(f"DSA streak already updated for today for user {user.id}")
            return

        print(f"DSA solved today. Updating streak stats for user {user.id}")
        stats.problems_solved += 1
        stats.problems_since_last_life += 1
        stats.last_activity_date = today
        
        # Life gain logic: every 7 problems
        if stats.problems_since_last_life >= 7:
            max_lives = 5 if mode == "normal" else 1 if mode == "hardcore" else 0
            if max_lives > 0 and stats.lives < max_lives:
                stats.lives += 1
                print(f"Gained a life! Total lives: {stats.lives}")
            stats.problems_since_last_life = 0
        
        db.commit()
        return
    
    if rewards_granted:
        db.commit() # Save reward updates even if streak is not yet met

    # If NOT solved, handle based on difficulty mode
    if mode == "sandbox":
        print("Sandbox mode: No penalty for missing challenge.")
        return

    should_execute_penalty = False
    if mode == "hardcore" or mode == "god":
        should_execute_penalty = True
        print(f"{mode.capitalize()} mode: Immediate penalty for missing challenge.")
    elif mode == "normal":
        if stats.lives > 0:
            stats.lives -= 1
            db.commit()
            print(f"Normal mode: Lost a life. Remaining lives: {stats.lives}")
            if stats.lives == 0:
                # The user says "Run out of lives, and the automated stock purchases begin."
                # Does it mean it starts immediately or on the NEXT failure? 
                # Usually it means this failure triggered the penalty because lives are gone.
                should_execute_penalty = True
        else:
            should_execute_penalty = True
            print("Normal mode: No lives left. Penalty triggered.")

    if should_execute_penalty:
        execute_zerodha_penalty(user, db)

def execute_zerodha_penalty(user, db: Session):
    if not kite_connect.access_token:
        decrypted_access_token = decrypt_token(user.access_token)
        kite_connect.set_access_token(decrypted_access_token)

    try:
        # Get selected stock from somewhere? For now use "IDEA" or use a default.
        # User UI has a stock picker, maybe I should store selected stock in UserStat or User.
        order_id = kite_connect.place_order(
            variety=kite_connect.VARIETY_REGULAR,
            tradingsymbol="IDEA",
            exchange=kite_connect.EXCHANGE_NSE,
            transaction_type=kite_connect.TRANSACTION_TYPE_BUY,
            quantity=10,
            order_type=kite_connect.ORDER_TYPE_MARKET,
            product=kite_connect.PRODUCT_CNC,
            validity=kite_connect.VALIDITY_DAY,
        )
        print(f"Penalty order placed. Order ID: {order_id}")
        resend.Emails.send(build_penalty_email())
    except InputException as e:
        if "Markets are closed right now." in str(e):
            try:
                order_id = kite_connect.place_order(
                    variety=kite_connect.VARIETY_AMO,
                    tradingsymbol="IDEA",
                    exchange=kite_connect.EXCHANGE_NSE,
                    transaction_type=kite_connect.TRANSACTION_TYPE_BUY,
                    quantity=10,
                    order_type=kite_connect.ORDER_TYPE_MARKET,
                    product=kite_connect.PRODUCT_CNC,
                    validity=kite_connect.VALIDITY_DAY,
                )
                print(f"Penalty AMO order placed. Order ID: {order_id}")
                resend.Emails.send(build_penalty_email())
            except Exception as ex:
                print(f"Failed to place penalty AMO order: {ex}")
    except Exception as e:
        print(f"Failed to place penalty order: {e}")

def daily_reset(db: Session):
    print("Performing daily reset...")
    db.query(UserStat).update({UserStat.powerups_used_today: 0})
    db.commit()


def schedule_daily_check(db):
    def job_wrapper():
        # Ensure the job runs at the correct time in the specified time zone
        india_tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(india_tz)
        if now.strftime("%H:%M") == "15:00":
            check_dsa_completion(db)
        if now.strftime("%H:%M") == "00:00":
            daily_reset(db)

    schedule.every().minute.do(job_wrapper)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    Thread(target=run_scheduler, daemon=True).start()
