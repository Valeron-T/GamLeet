import schedule
import time
from threading import Thread
from helpers.leetcode import is_leetcode_solved_today
from helpers.mails import build_penalty_email
from kite import kite_connect, generate_session
from kiteconnect.exceptions import InputException
from sqlalchemy.orm import Session
from models import Users
from datetime import datetime
import pytz
import os
from cryptography.fernet import Fernet

import resend

# Generate a key and store it securely (do this once and reuse the key)
encryption_key = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(encryption_key)
resend.api_key = os.getenv("RESEND_API_KEY")


def check_dsa_completion(db: Session):
    # Placeholder: Replace with actual logic to check if DSA problem was solved
    dsa_solved = is_leetcode_solved_today()  # Set to True if problem was solved

    if not kite_connect.access_token:
        user = (
            db.query(Users).filter(Users.zerodha_id == os.getenv("ZERODHA_ID")).first()
        )
        decrypted_access_token = cipher.decrypt(user.access_token).decode()
        kite_connect.set_access_token(decrypted_access_token)

    if not dsa_solved:
        try:
            order_id = kite_connect.place_order(
                variety=kite_connect.VARIETY_REGULAR,
                tradingsymbol="IDEA",  # Replace with actual stock symbol
                exchange=kite_connect.EXCHANGE_NSE,
                transaction_type=kite_connect.TRANSACTION_TYPE_BUY,
                quantity=10,
                order_type=kite_connect.ORDER_TYPE_MARKET,
                product=kite_connect.PRODUCT_CNC,
                validity=kite_connect.VALIDITY_DAY,
            )
            print(f"Penalty order placed. Order ID: {order_id}")

            r = resend.Emails.send(build_penalty_email())

        except InputException as e:
            try:
                if "Markets are closed right now." in str(e):
                    print("Markets are closed. Placing AMO order.")
                    order_id = kite_connect.place_order(
                        variety=kite_connect.VARIETY_AMO,
                        tradingsymbol="IDEA",  # Replace with actual stock symbol
                        exchange=kite_connect.EXCHANGE_NSE,
                        transaction_type=kite_connect.TRANSACTION_TYPE_BUY,
                        quantity=10,
                        order_type=kite_connect.ORDER_TYPE_MARKET,
                        product=kite_connect.PRODUCT_CNC,
                        validity=kite_connect.VALIDITY_DAY,
                    )
                    print(f"Penalty order placed. Order ID: {order_id}")
                    r = resend.Emails.send(build_penalty_email())
            except Exception as e:
                print(f"Failed to place penalty AMO order: {e}")
        except Exception as e:
            print(f"Failed to place penalty order: {e}")


def schedule_daily_check(db):
    def job_wrapper():
        # Ensure the job runs at the correct time in the specified time zone
        india_tz = pytz.timezone("Asia/Kolkata")
        now = datetime.now(india_tz)
        if now.strftime("%H:%M") == "15:00":
            check_dsa_completion(db)

    schedule.every().minute.do(job_wrapper)

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)

    Thread(target=run_scheduler, daemon=True).start()
