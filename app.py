"""홍제동 요가원 경영 대시보드"""
from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

# 기본 설정
DEFAULT_CONFIG = {
    "rent": 180,
    "instructor_cost": 240,
    "utilities": 25,
    "supplies": 10,
    "marketing": 10,
    "price_3m_3x": 52,  # 3개월 주3회
    "price_3m_2x": 42,  # 3개월 주2회
    "price_1m_3x": 20,  # 1개월 주3회
    "initial_members": 37,
    "key_money": 1000,
    "deposit": 500,
    "interior": 200,
}

DEFAULT_DATA = {
    "config": DEFAULT_CONFIG,
    "months": []  # [{month, new_members, churned_members, total_members, extra_revenue, extra_cost, note}]
}


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return DEFAULT_DATA.copy()


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calc_monthly(config, months):
    """월별 손익 계산"""
    results = []
    initial_investment = config["key_money"] + config["deposit"] + config["interior"]
    cumulative = -initial_investment
    total_members = config["initial_members"]

    for m in months:
        total_members = total_members + m.get("new_members", 0) - m.get("churned_members", 0)
        if total_members < 0:
            total_members = 0

        # 매출: 회원당 평균 월매출 (3개월 52만/3 = 17.3만 기준, 믹스 감안 17만)
        avg_per_member = config["price_3m_3x"] / 3
        revenue = total_members * avg_per_member + m.get("extra_revenue", 0)

        # 비용
        extra_instructor = 30 if total_members >= 40 else (15 if total_members >= 35 else 0)
        cost = (config["rent"] + config["instructor_cost"] + extra_instructor +
                config["utilities"] + config["supplies"] + config["marketing"] +
                m.get("extra_cost", 0))

        profit = revenue - cost
        cumulative += profit

        results.append({
            "month": m.get("month", len(results) + 1),
            "total_members": total_members,
            "new_members": m.get("new_members", 0),
            "churned_members": m.get("churned_members", 0),
            "revenue": round(revenue, 1),
            "cost": round(cost, 1),
            "profit": round(profit, 1),
            "cumulative": round(cumulative, 1),
            "note": m.get("note", ""),
        })

    return results, initial_investment


def calc_simulation(config):
    """12개월 시뮬레이션 (신규 월5명, 이탈률 12%)"""
    results = []
    initial_investment = config["key_money"] + config["deposit"] + config["interior"]
    cumulative = -initial_investment
    total = config["initial_members"]
    churn_rate = 0.12
    monthly_new = 5

    for month in range(1, 13):
        churned = round(total * churn_rate)
        total = total - churned + monthly_new
        avg_per_member = config["price_3m_3x"] / 3
        revenue = total * avg_per_member
        extra_instructor = 30 if total >= 40 else (15 if total >= 35 else 0)
        cost = (config["rent"] + config["instructor_cost"] + extra_instructor +
                config["utilities"] + config["supplies"] + config["marketing"])
        profit = revenue - cost
        cumulative += profit
        results.append({
            "month": month,
            "total_members": total,
            "new": monthly_new,
            "churned": churned,
            "revenue": round(revenue, 1),
            "cost": round(cost, 1),
            "profit": round(profit, 1),
            "cumulative": round(cumulative, 1),
        })
    return results, initial_investment


@app.route("/")
def index():
    data = load_data()
    results, initial_investment = calc_monthly(data["config"], data["months"])
    simulation, _ = calc_simulation(data["config"])

    # BEP 회원 수
    config = data["config"]
    fixed = config["rent"] + config["instructor_cost"] + config["utilities"] + config["supplies"] + config["marketing"]
    avg_per_member = config["price_3m_3x"] / 3
    bep_members = fixed / avg_per_member

    return render_template("dashboard.html",
                           config=config,
                           results=results,
                           simulation=simulation,
                           initial_investment=initial_investment,
                           bep_members=round(bep_members, 1),
                           fixed_cost=fixed)


@app.route("/api/config", methods=["POST"])
def update_config():
    data = load_data()
    new_config = request.json
    for k, v in new_config.items():
        if k in data["config"]:
            data["config"][k] = float(v)
    save_data(data)
    return jsonify({"status": "ok"})


@app.route("/api/month", methods=["POST"])
def add_month():
    data = load_data()
    entry = request.json
    data["months"].append({
        "month": len(data["months"]) + 1,
        "new_members": int(entry.get("new_members", 0)),
        "churned_members": int(entry.get("churned_members", 0)),
        "extra_revenue": float(entry.get("extra_revenue", 0)),
        "extra_cost": float(entry.get("extra_cost", 0)),
        "note": entry.get("note", ""),
    })
    save_data(data)
    return jsonify({"status": "ok"})


@app.route("/api/month/<int:idx>", methods=["DELETE"])
def delete_month(idx):
    data = load_data()
    if 0 <= idx < len(data["months"]):
        data["months"].pop(idx)
        # 재번호
        for i, m in enumerate(data["months"]):
            m["month"] = i + 1
        save_data(data)
    return jsonify({"status": "ok"})


@app.route("/api/reset", methods=["POST"])
def reset_data():
    save_data(DEFAULT_DATA.copy())
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
