import datetime
import random

SARCASTIC_EMAILS = [
    {
        "subject": "🏆 Gold Medal in Procrastination: Awarded",
        "html": """
            <p><strong>Congratulations!</strong></p>
            <p>You’ve officially done less than nothing today — because not only did you skip Leetcode, but you also managed to sabotage your financial future in the process.</p>
            <p>In honor of your impressive laziness, we’ve acquired some truly pathetic stock on your behalf. Think of it as a participation trophy — for losing.</p>
            <p>This isn't accountability. This is poetic justice wrapped in bad investments.</p>
            <p>Honestly, your brokerage account should file for emotional damage.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Your Daily Reminder That You Are the Problem</p>
        """,
    },
    {
        "subject": "📉 A Strategic Masterclass in Doing Absolutely Nothing",
        "html": """
            <p><strong>Let’s reflect:</strong></p>
            <p>You had 24 hours to do *one* Leetcode problem. Just one. Instead, you binge-scrolled social media, convinced yourself “rest is productive,” and let the algorithm eat your dignity.</p>
            <p>Now you're the proud owner of a stock so volatile, even meme investors won’t touch it.</p>
            <p>You’ve turned self-sabotage into an art form. Bravo, Picasso.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Turning Laziness Into Long-Term Consequences</p>
        """,
    },
    {
        "subject": "🫡 You Ignored Growth. So We Bought Decline.",
        "html": """
            <p><strong>Today's trade was made in honor of your inaction.</strong></p>
            <p>We purchased a stock with as much upside as your motivation: absolutely none.</p>
            <p>If your goal was to build wealth by avoiding effort, congrats — you’ve entered the exact opposite program.</p>
            <p>This isn’t just an accountability system. This is your incompetence, fully automated.</p>
            <p>You're not even being productive at failing. That's how bad it's gotten.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, CEO of Your Own Undoing</p>
        """,
    },
    {
        "subject": "📬 Just Here to Document the Downfall",
        "html": """
            <p><strong>Reminder: Your Leetcode streak has flatlined. Again.</strong></p>
            <p>But don’t worry — your habit of avoiding progress has funded today’s mystery investment: a company so irrelevant, it doesn't even have a Wikipedia page.</p>
            <p>At this point, we’re less a bot and more a passive-aggressive financial obituary service.</p>
            <p>Keep going. One day, you'll be able to tell your kids: "I almost made it — but then I didn’t."</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Logging Every Failure With Style</p>
        """,
    },
    {
        "subject": "🫠 We’ve Run Out of Ways to Warn You",
        "html": """
            <p><strong>This is not a drill. You’ve skipped again.</strong></p>
            <p>We wanted to give you one more chance to turn it around, but honestly? You're on a speedrun to career irrelevance and financial embarrassment.</p>
            <p>So we did what you deserve — made a trade so dumb it belongs in a cautionary tale.</p>
            <p>At this point, even ChatGPT is concerned for your future, and I’m literally writing this.</p>
            <p>Wake up. Or don't. But either way, you’re paying for it.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Automating the Cost of Complacency</p>
        """,
    },
    {
        "subject": "🏆 Procrastination Trophy Awarded",
        "html": """
            <p><strong>Behold your prize!</strong></p>
            <p>We commissioned a custom trophy to commemorate your dedication to avoiding Leetcode. It's made of pure irony and paid for with your own bad investments.</p>
            <p>The engraving reads: <em>"World Champion in Active Self-Sabotage – 2024"</em>.</p>
            <p>Fun fact: The trophy’s base is a graph of your portfolio’s steady decline.</p>
            <p>Display it proudly next to your other participation medals for <em>"Almost Tried"</em>.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Your Personal Failure Curator</p>
        """,
    },
    {
        "subject": "📉 Strategic Masterclass in Financial Ruin",
        "html": """
            <p><strong>Today’s lesson: How to turn $10 into $0.50.</strong></p>
            <p>We’ve attached a diagram of your investment strategy. Spoiler: It’s just a stick figure lighting money on fire.</p>
            <p>Your portfolio now consists of three shares of <em>"Defunct Blockchain Startup, Inc."</em> and a single expired coupon for Denny’s.</p>
            <p>On the bright side, you’re now qualified to teach a masterclass: <em>"Avoiding Success: A Step-by-Step Guide"</em>.</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Dean of Your Self-Inflicted MBA (Mismanaged Bad Assets)</p>
        """,
    },
    {
        "subject": "🪴 RIP: Your Career (Just Like This Plant)",
        "html": """
            <p><strong>Remember that "growth mindset" you kept talking about?</strong></p>
            <p>We bought you a houseplant to symbolize it. Sadly, it died from neglect—just like your Leetcode streak.</p>
            <p>Its last words were: <em>"At least I tried to photosynthesize."</em></p>
            <p>We’ve buried it in your portfolio, next to the penny stocks you now own.</p>
            <p>Maybe water your ambitions next time. (Or don’t. We’ll just keep shorting them.)</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Botanist of Broken Dreams</p>
        """,
    },
    {
        "subject": "🫡 Congratulations, You Played Yourself",
        "html": """
            <p><strong>We’d say "checkmate," but you weren’t even playing.</strong></p>
            <p>Your latest acquisition: <em>"A Random Crypto Token That Peaked in 2021"</em>. It’s down 99.9%, just like your motivation.</p>
            <p>Fun experiment: Try explaining this investment to a future employer. (We’ll wait.)</p>
            <p>On the plus side, you’ve unlocked a new achievement: <em>"Most Creative Way to Lose Money Without Gambling."</em></p>
            <p style="color: #999; font-style: italic;">– Gameleet, Officially Concerned (But Not Really)</p>
        """,
    },
    {
        "subject": "🔥 Your Portfolio: Now with 100% More Regret",
        "html": """
            <p><strong>Breaking News: Your stocks hit rock bottom. Then kept digging.</strong></p>
            <p>We’ve added a new feature to your brokerage account: <em>"Crying in Dollars"</em> mode.</p>
            <p>Today’s highlight: You now own a fractional share of a company that sells <em>"Blockchain-Enabled Pet Rocks."</em></p>
            <p>But hey, at least you got that extra hour of TikTok scrolling in. #WorthIt</p>
            <p style="color: #999; font-style: italic;">– Gameleet, The Only One Keeping Score (And Laughing)</p>
        """,
    },
    {
        "subject": f"🪦 Here Lies Your Potential (2015–{datetime.datetime.now().year})",
        "html": """
            <p><strong>Moment of silence for what could’ve been.</strong></p>
            <p>We’ve erected a tiny tombstone in your honor. Epitaph: <em>"Here lies [Your Name]’s ambition. Cause of death: 'I’ll do it tomorrow.'"</em></p>
            <p>Flowers will be funded by your latest stock purchase: <em>"Failing Ponzi Scheme, LLC."</em></p>
            <p>On the bright side, graveyards are quiet—perfect for finally doing Leetcode! (But let’s be real, you won’t.)</p>
            <p style="color: #999; font-style: italic;">– Gameleet, Your Grim Financial Reaper</p>
        """,
    },
]


def build_penalty_email():
    msg = random.choice(SARCASTIC_EMAILS)
    return {
        "from": "gameleet@alerts.valeron.me",
        "to": "valerontoscano@gmail.com",
        "subject": msg["subject"],
        "html": f"""
        <html>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f7; color: #333;">
                <div style="max-width: 600px; margin: 40px auto; background-color: #fff; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); padding: 30px;">
                    <h2 style="text-align: center; color: #2c3e50;">⚠️ Goal Missed - Automated Action Taken ⚠️</h2>
                    <div style="padding: 10px 0; font-size: 16px; line-height: 1.6;">
                        {msg["html"]}
                    </div>
                    <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                    <p style="font-size: 13px; text-align: center; color: #999;">
                        This action was triggered by <strong>Gameleet</strong> because you ghosted your daily Leetcode commitment. 
                        <br>Fix your life before your portfolio fixes you.
                    </p>
                </div>
            </body>
        </html>
        """,
    }
