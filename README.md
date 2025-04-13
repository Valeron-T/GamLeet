# 🎲 GamLeet — Punish Your Procrastination with Market Chaos

**GamLeet** is a self-hosted FastAPI app that *automates shame* by linking your Leetcode grind to your financial well-being.

If you skip your daily DSA problem, **GamLeet punishes you** by executing a buy order for a random (usually terrible) stock using Zerodha's Kite Connect API. Want to suffer for your sins in real time? Now you can — with receipts.

---

## 💡 Why?

You're not lazy — you're *accountability-challenged*.

- Tired of skipping Leetcode and pretending you'll "do it later"?
- Need a reason stronger than "career growth" to actually practice?
- Love pain and poor financial decisions?

**This app weaponizes your brokerage account** to enforce discipline.

---

## 🧠 Features

- ⏱️ Daily DSA tracking with Leetcode integration (WIP)
- 💸 Automatic stock purchase if you miss your daily goal
- 📧 Sarcastic shame email notifications for extra guilt
- 📦 Easily self-hostable with Docker and FastAPI
- 🔐 Kite Connect integration (Zerodha account required)

---

## 🛠️ Tech Stack

- Python + FastAPI
- SQLAlchemy + MySQL
- Zerodha Kite Connect API
- Resend for emails (with ✨ maximum sarcasm)

---

## ⚙️ Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/your-username/GamLeet.git
   cd GamLeet
    ```

2. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up environment variables (`.env`)**
    ```
    ENCRYPTION_KEY=""
    LEETCODE_USERNAME='johndoe'
    RESEND_API_KEY="re_*********************************"
    SQLALCHEMY_DATABASE_URL="mysql+pymysql://username:password@host:port/dbname"
    ZERODHA_API_KEY=''
    ZERODHA_API_SECRET=''
    ZERODHA_ID='ABC123'
    ```

4. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🧪 Example Flow

- You skip Leetcode.

- At 3pm IST, Gameleet checks your streak.

- You failed.

- It executes a random order on your Zerodha account.

- You receive a sarcastic email shaming your laziness.

- You cry. Then code tomorrow. Hopefully.

---

##  🛡️ Disclaimers
- This is designed for personal use and educational purposes.

- Know what you're doing before connecting your brokerage account.

- Market orders can and will hurt you. Gameleet doesn't care.

---

##  🙃 Motivation-as-a-Service
- If shame, sarcasm, and stock losses won’t get you to code... maybe nothing will.

---

##  🪦 Star this repo if you want to be publicly accountable
- Fork it if you want to drag your friends into this spiral too. (Why suffer alone?)

### Built by @valerontoscano
### Punishment delivered by Gameleet™

