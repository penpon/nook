import json

target_ids = [3550664184, 3550647685, 3550612711]

try:
    with open("reviews_api_100.json", "r") as f:
        reviews = json.load(f)

    with open("review_summary.txt", "w") as out:
        for r in reviews:
            if r["id"] in target_ids:
                out.write(f"ID: {r['id']}\n")
                out.write(f"User: {r['user']['login']}\n")
                out.write(f"State: {r['state']}\n")
                out.write(f"Body: {r['body']}\n")
                out.write("-" * 20 + "\n")
except Exception as e:
    with open("review_summary.txt", "w") as out:
        out.write(f"Error: {e}")
