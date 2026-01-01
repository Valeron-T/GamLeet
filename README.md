# 🎲 GamLeet — Automated Accountability via Financial Pain

**GamLeet** is a self-hosted FastAPI application that automates discipline by linking your LeetCode consistency to your Zerodha brokerage account.

**The Loop is Simple:**
1. **Code**: Solve 3 daily problems (Easy/Medium/Hard).
2. **Streak**: Maintain your streak to earn `GamCoins` & XP.
3. **Fail**: Skip a day? GamLeet executes a **market buy order** for a random, volatile stock. 
4. **Suffer**: Watch your portfolio confusingly accumulate random assets.

---

## 💡 Why?

Willpower is finite. Loss aversion is biological.
GamLeet weaponizes your greed against your laziness.

---

## 🧠 Core Features

- **⏱️ Daily Tracking**: automatically pulls your daily submission stats from LeetCode.
- **💸 Automated Penalties**: Integrated with **Zerodha Kite Connect** to execute real trades on failure.
- **🛡️ Power-up System**: Buy `Streak Freezes` and `Penalty Shields` using in-app currency earned from consistency.
- **🚶 First-Time Walkthrough**: Backend support for tracking user onboarding status.
- **📧 Shame Notifications**: Emails via Resend to let you know exactly what you bought and why.
- **🔒 Secure Session Management**: Custom session-based auth with secure cookies.

---

## 🛠️ Tech Stack

- **Framework**: Python (FastAPI)
- **Database**: MySQL (via SQLAlchemy)
- **Caching**: Redis (for session & stat caching)
- **Broker Integration**: Zerodha Kite Connect API
- **Email**: Resend API

---

## ⚙️ Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/valeron-t/gamleet.git
   cd GamLeet
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables (`.env`)**
   ```env
   # Database & Redis
   SQLALCHEMY_DATABASE_URL="mysql+pymysql://user:pass@host/db"
   REDIS_CONN_STRING="redis://user:pass@host:port"

   # Zerodha Credentials
   ZERODHA_API_KEY="your_api_key"
   ZERODHA_API_SECRET="your_api_secret"
   ZERODHA_ID="your_user_id"

   # Security
   ENCRYPTION_KEY="generated_key"
   GOOGLE_CLIENT_ID="your_google_client_id"
   ENVIRONMENT="development" # or production

   # Notifications
   RESEND_API_KEY="re_..."
   ```

4. **Run the Server**
   ```bash
   uvicorn main:app --reload
   ```

---

## 🔄 The Logic

- **Scheduler**: Runs daily at 3:30 PM IST (market close).
- **Check**: Did `user.problems_solved` increase by 3 today?
- **Result**:
    - **Yes**: Increment Streak, Award GamCoins, Grant XP.
    - **No**: Check for `Streak Freeze`. 
        - If available: Consume Freeze, maintain streak.
        - If none: **Reset Streak**, check for `Penalty Shield`.
            - If Shield available: Consume Shield, skip penalty.
            - If no Shield: **EXECUTE MARKET ORDER**.

---

## ⚠️ Disclaimer

**This software performs REAL FINANCIAL TRANSACTIONS.** 
It is designed to lose you money if you are lazy. Use at your own risk. The developers are not responsible for your financial ruin, though we might find it amusing.

---

### Built by @valerontoscano
