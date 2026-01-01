import schedule
import time
from threading import Thread
from helpers.leetcode import is_leetcode_solved_today
from helpers.mails import build_penalty_email, build_nudge_email
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

    # --- Daily Problem Check ---
    from helpers.leetcode import fetch_daily_problem
    daily_problem = fetch_daily_problem()
    
    if daily_problem.get("slug"):
        daily_slug = daily_problem["slug"]
        daily_id = daily_problem["id"]

        is_daily_solved = is_leetcode_solved_today(username=user.leetcode_username, session=user.leetcode_session, daily_slug=daily_slug)
        
        if is_daily_solved:
             # Check if already rewarded for THIS specific daily problem ID (assuming ID is unique per daily occurrence or question)
             # Note: LeetCode questionId is static for the problem. 
             # We should probably track it with a specific completion marker or trust QuestionCompletion if we want to treat it as "just another question".
             # However, the user wants "Daily Problem" reward. The requirement implies a repeating reward potentially?
             # Actually, if I solve "Two Sum" today as a daily, and it comes up again next year, I should probably get rewarded again? 
             # But QuestionCompletion prevents duplicate rewards for the same question ID. 
             # Let's assume for now standard QuestionCompletion logic applies + Bonus. 
             # OR, since it's a "Quest", maybe we need a separate "DailyQuestCompletion" table?
             # For simplicity and speed: Use QuestionCompletion to prevent double dips on the SAME day/problem. 
             # BUT, since we want to award specifically for it being the "Daily Problem", let's check if the generic "Daily Problem" reward was given today?
             # No, the prompt says "award bonus points for the same".
             # Let's just give 85 GC if they haven't solved it *via this flow* yet.
             # Actually, simpler: Check if they have a completion for this question ID. If NOT, give them standard + bonus? 
             # Or just give specific Daily Problem reward (85 GC).
             
             already_rewarded_daily = db.query(QuestionCompletion).filter(
                QuestionCompletion.user_id == user.id,
                QuestionCompletion.question_id == daily_id
            ).first()

             if not already_rewarded_daily:
                print(f"User {user.id} completed DAILY problem {daily_slug}. Granting 30 GC Bonus.")
                stats.gamcoins += 30
                stats.total_xp += 150 # Bonus XP? Let's give some.

                completion = QuestionCompletion(user_id=user.id, question_id=daily_id)
                db.add(completion)
                rewards_granted = True
    # ---------------------------

    # 2. Handle Streak / Streak Maintenance logic
    dsa_solved = is_leetcode_solved_today(username=user.leetcode_username, session=user.leetcode_session)
    
    mode = stats.difficulty_mode.lower()

    if dsa_solved:
        if stats.last_activity_date == today:
            if rewards_granted:
                db.commit()
            return

        from datetime import timedelta
        print(f"DSA solved today. Updating streak stats for user {user.id}")
        
        # Streak increment logic
        if stats.last_activity_date == today - timedelta(days=1):
            stats.current_streak += 1
        else:
            # First time or broke streak
            stats.current_streak = 1
            
        if stats.current_streak > stats.max_streak:
            stats.max_streak = stats.current_streak

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
        # Check for streak freeze
        from models import UserInventory
        freeze = db.query(UserInventory).filter(
            UserInventory.user_id == user.id,
            UserInventory.item_id == "streak-freeze",
            UserInventory.quantity > 0
        ).first()

        if freeze:
            print(f"User {user.id} missed DSA but has a Streak Freeze! Consuming one.")
            freeze.quantity -= 1
            # We don't delete if quantity > 0, SQLAlchemy handles the update
            db.commit()
            return

        # No freeze, reset streak and execute penalty
        stats.current_streak = 0
        db.commit()
        execute_zerodha_penalty(user, db)

def execute_zerodha_penalty(user, db: Session):
    if not user.access_token or not user.zerodha_api_key:
        print(f"User {user.id} has no Zerodha credentials set. Skipping penalty.")
        return

    from kite import get_kite_client
    from security import decrypt_token
    
    kite_client = get_kite_client(decrypt_token(user.zerodha_api_key))
    kite_client.set_access_token(decrypt_token(user.access_token))

    import random
    
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    risk_amount = stats.daily_risk_amount if stats else 50
    
    # List of penny stocks/volatile stocks
    PENNY_STOCKS = ["SUZLON", "IDEA", "YESBANK", "JPPOWER", "UCOBANK"]
    
    chosen_stock = random.choice(PENNY_STOCKS)
    exchange = kite_client.EXCHANGE_NSE
    instrument_token = f"{exchange}:{chosen_stock}"
    
    quantity = 1
    
    try:
        quote = kite_client.quote(instrument_token)
        ltp = quote[instrument_token]["last_price"]
        
        if ltp > 0:
            quantity = int(risk_amount // ltp)
            
        # Ensure at least 1 qty if risk amount is low but non-zero, or just fallback to 1
        if quantity < 1:
            quantity = 1
            
        print(f"Penalty calculation: Stock={chosen_stock}, LTP={ltp}, Risk={risk_amount}, Qty={quantity}")
        
    except Exception as e:
        print(f"Error fetching quote for {chosen_stock}: {e}. Defaulting to Qty=1")
        quantity = 1

    try:
        order_id = kite_client.place_order(
            variety=kite_client.VARIETY_REGULAR,
            tradingsymbol=chosen_stock,
            exchange=exchange,
            transaction_type=kite_client.TRANSACTION_TYPE_BUY,
            quantity=quantity, 
            order_type=kite_client.ORDER_TYPE_MARKET,
            product=kite_client.PRODUCT_CNC,
            validity=kite_client.VALIDITY_DAY,
        )
        print(f"Penalty order placed for user {user.id}. Order ID: {order_id}")
        if user.email and getattr(user, "email_notifications", 1):
            try:
                resend.Emails.send(build_penalty_email(user.email))
            except Exception as mail_err:
                print(f"Failed to send penalty email to {user.email}: {mail_err}")
    except InputException as e:
        if "Markets are closed right now." in str(e):
            try:
                order_id = kite_client.place_order(
                    variety=kite_client.VARIETY_AMO,
                    tradingsymbol=chosen_stock,
                    exchange=exchange,
                    transaction_type=kite_client.TRANSACTION_TYPE_BUY,
                    quantity=quantity,
                    order_type=kite_client.ORDER_TYPE_MARKET,
                    product=kite_client.PRODUCT_CNC,
                    validity=kite_client.VALIDITY_DAY,
                )
                print(f"Penalty AMO order placed for user {user.id}. Order ID: {order_id}")
                if user.email and getattr(user, "email_notifications", 1):
                    try:
                        resend.Emails.send(build_penalty_email(user.email))
                    except Exception as mail_err:
                        print(f"Failed to send penalty email to {user.email}: {mail_err}")
            except Exception as ex:
                print(f"Failed to place penalty AMO order for user {user.id}: {ex}")
    except Exception as e:
        print(f"Failed to place penalty order for user {user.id}: {e}")

def daily_reset(db: Session):
    print("Performing daily reset...")
    db.query(UserStat).update({UserStat.powerups_used_today: 0})
    db.commit()

def send_nudge_reminders(db: Session):
    print("Running pre-penalty nudges...")
    users = db.query(User).all()
    for user in users:
        try:
            # Check if they solved today
            if not is_leetcode_solved_today(username=user.leetcode_username, session=user.leetcode_session):
                if user.email and getattr(user, "email_notifications", 1):
                    print(f"Nudging user {user.id} ({user.email})")
                    resend.Emails.send(build_nudge_email(user.email))
                else:
                    print(f"User {user.id} has no email configured, skipping nudge.")
        except Exception as e:
            print(f"Error nudging user {user.id}: {e}")


def schedule_daily_check(db):
    def job_wrapper():
        india_tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(india_tz)
        current_time = now.strftime("%H:%M")
        
        if current_time == "11:00": # Nudge at 11 AM IST
            send_nudge_reminders(db)
        if current_time == "15:00": # Penalty at 3 PM IST
            check_all_users_dsa(db)
        if current_time == "00:00": # Reset at Midnight
            daily_reset(db)

    schedule.every().minute.do(job_wrapper)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    Thread(target=run_scheduler, daemon=True).start()
