import random
import string
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import redditwarp.SYNC as redditwarp

# ============================================================
#  CONFIGURATION
# ============================================================

CREDENTIALS_FILE = "credentials.json"
DOC_ID           = "1GKT_uqdXpQRsC7ZgFXSWgf1jpDGXVpBp8oTupjoIPvU"

SUBREDDITS    = ["askreddit", "tifu", "AmItheAsshole"]
POSTS_PER_SUB = 2    # Fetch 2 from each (6 total → top 5 kept)
TOTAL_POSTS   = 5    # Final number of posts to save

# ============================================================
#  STEP 1 — Fetch top posts using redditwarp (no API key needed)
# ============================================================

def fetch_reddit_posts():
    all_posts = []

    # Randomized user-agent to avoid Reddit blocking
    random_suffix  = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    user_agent_str = f"mac:reddit_video_bot_{random_suffix}:v3.2.0 (educational-use)"

    client = redditwarp.Client()
    client.http.user_agent = user_agent_str

    for sub in SUBREDDITS:
        try:
            print(f"🔍 Fetching r/{sub}...")
            posts = client.p.subreddit.pull.top(sub, amount=POSTS_PER_SUB, time="day")

            for post in posts:
                if post.nsfw:
                    continue
                all_posts.append({
                    "title"     : post.title,
                    "url" : post.permalink if post.permalink.startswith("http") else f"https://reddit.com{post.permalink}",
                    "upvotes"   : post.score,
                    "comments"  : post.comment_count,
                    "subreddit" : sub
                })
            print(f"✅ Fetched from r/{sub}")

        except Exception as e:
            print(f"❌ Failed r/{sub} — {e}")

    return sorted(all_posts, key=lambda x: x["upvotes"], reverse=True)[:TOTAL_POSTS]

# ============================================================
#  STEP 2 — Format content for Google Doc
# ============================================================

def format_content(posts):
    date  = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    lines = []
    lines.append(f"Top Reddit Posts — {date}\n")
    lines.append("=" * 60 + "\n\n")

    for i, post in enumerate(posts, 1):
        lines.append(f"{i}. {post['title']}\n")
        lines.append(f"   Upvotes  : {post['upvotes']}\n")
        lines.append(f"   Comments : {post['comments']}\n")
        lines.append(f"   Subreddit: r/{post['subreddit']}\n")
        lines.append(f"   Link     : {post['url']}\n")
        lines.append("\n")

    return "".join(lines)

# ============================================================
#  STEP 3 — Write to Google Doc
# ============================================================

def write_to_google_doc(content):
    scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive"
    ]
    creds   = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=scopes
    )
    service = build("docs", "v1", credentials=creds)

    doc         = service.documents().get(documentId=DOC_ID).execute()
    doc_content = doc.get("body").get("content")
    end_index   = doc_content[-1]["endIndex"] - 1

    requests_body = []

    # Clear old content
    if end_index > 1:
        requests_body.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex"  : end_index
                }
            }
        })

    # Write new content
    requests_body.append({
        "insertText": {
            "location": {"index": 1},
            "text"    : content
        }
    })

    service.documents().batchUpdate(
        documentId=DOC_ID,
        body={"requests": requests_body}
    ).execute()

    print(f"✅ Google Doc updated!")
    print(f"🔗 https://docs.google.com/document/d/{DOC_ID}/edit")

# ============================================================
#  MAIN
# ============================================================

if __name__ == "__main__":
    print("\n🚀 Starting Reddit Fetcher...\n")

    print("📡 Fetching posts from Reddit...")
    posts = fetch_reddit_posts()

    if not posts:
        print("❌ No posts found.")
    else:
        print(f"\n📝 Top {len(posts)} posts found. Writing to Google Doc...\n")
        content = format_content(posts)
        write_to_google_doc(content)
        print("\n✅ Done!\n")