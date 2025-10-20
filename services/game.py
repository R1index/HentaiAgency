from typing import Dict, Any, Tuple
from db.database import db, now_ts

# Tunables
FANS_GAIN_PER_POP = 0.1           # fans/sec from popularity while working
PASSIVE_PER_FAN_PER_SEC = 0.001   # passive money per fan per second
STAM_DOWN_SEC_PER_1 = 10          # -1% per 10s working
STAM_UP_SEC_PER_1 = 5             # +1% per 5s resting

def stamina_tick(stamina: float, is_working: bool, dt: float) -> Tuple[float, bool, float, float]:
    work_seconds = 0.0
    rest_seconds = 0.0
    s = stamina
    w = is_working
    t = dt
    while t > 0:
        if w and s > 0:
            can_spend = s * STAM_DOWN_SEC_PER_1
            if t <= can_spend:
                ds = t / STAM_DOWN_SEC_PER_1
                s = max(0.0, s - ds)
                work_seconds += t
                t = 0
            else:
                s = 0.0
                work_seconds += can_spend
                t -= can_spend
                w = False
        else:
            if s >= 100:
                w = True
                continue
            need = (100 - s) * STAM_UP_SEC_PER_1
            if t <= need:
                ds = t / STAM_UP_SEC_PER_1
                s = min(100.0, s + ds)
                rest_seconds += t
                t = 0
                if s >= 100:
                    w = True
            else:
                s = 100.0
                rest_seconds += need
                t -= need
                w = True
    return round(s, 3), w, work_seconds, rest_seconds

def compute_tick(user_id: int) -> Dict[str, Any]:
    con = db()
    cur = con.cursor()
    cur.execute("SELECT money, last_tick FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return {"dt": 0}

    last = row["last_tick"]
    now = now_ts()
    dt = max(0, now - last)
    if dt == 0:
        con.close()
        return {"dt": 0}

    cur.execute("SELECT id, income, popularity, fans, stamina, is_working FROM user_girls WHERE user_id=?", (user_id,))
    girls = cur.fetchall()

    money_gain = 0.0
    total_fans = 0.0
    updates = []

    for g in girls:
        income = float(g["income"])
        pop = float(g["popularity"])
        fans = float(g["fans"])
        stamina = float(g["stamina"])
        is_working = bool(g["is_working"])

        new_stam, new_working, work_secs, rest_secs = stamina_tick(stamina, is_working, dt)

        if work_secs > 0:
            money_gain += income * work_secs
            fans += pop * FANS_GAIN_PER_POP * work_secs

        updates.append((new_stam, int(new_working), fans, g["id"]))
        total_fans += fans

    passive_gain = total_fans * PASSIVE_PER_FAN_PER_SEC * dt
    money_gain += passive_gain
    new_money = float(row["money"]) + money_gain

    cur.execute("UPDATE users SET money=?, last_tick=? WHERE user_id=?", (new_money, now, user_id))
    for s, w, f, gid in updates:
        cur.execute("UPDATE user_girls SET stamina=?, is_working=?, fans=? WHERE id=?", (s, w, f, gid))
    con.commit()
    con.close()
    return {"dt": dt, "money_gain": money_gain, "passive_gain": passive_gain, "total_fans": total_fans}
