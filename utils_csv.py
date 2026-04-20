import json
import csv

def json_to_csv():
    rows = []

    with open("results/results.json", "r") as f:
        for line in f:
            data = json.loads(line)

            # ✅ keep only successful runs
            if data.get("status") == "success":
                rows.append(data)

    if not rows:
        print("No valid (successful) data found")
        return

    keys = rows[0].keys()

    with open("results/results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    print("✅ Clean CSV created: results/results.csv")