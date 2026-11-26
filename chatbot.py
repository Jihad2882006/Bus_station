#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
شات بوت محطة إكسبريس - يشتغل مع server.py و SQLite بدون مكتبات خارجية.
بيكلّم Claude API ويستخدم أدوات (tool use) تقرأ/تكتب في نفس قاعدة البيانات.
"""
import os
import json
import time
import secrets
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-5-5")
MAX_SEATS_PER_BOOKING = 5
MAX_MESSAGE_LEN = 1000
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 6
RATE_LIMIT_PER_MIN = 15

_rate = {}


def _allowed(ip):
    now = time.time()
    hits = [t for t in _rate.get(ip, []) if now - t < 60]
    if len(hits) >= RATE_LIMIT_PER_MIN:
        _rate[ip] = hits
        return False
    hits.append(now)
    _rate[ip] = hits
    return True


# ---------------------------------------------------------------- DB helpers
def _conn(db_file):
    c = sqlite3.connect(db_file, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _booked_seats(cur, trip_id):
    taken = set()
    for r in cur.execute("SELECT seats FROM bookings WHERE trip_id = ?", (trip_id,)):
        try:
            taken.update(json.loads(r["seats"]))
        except Exception:
            pass
    return taken


def _norm_digits(text):
    return str(text or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))


def _norm_phone(phone):
    p = _norm_digits(phone).replace(" ", "").replace("-", "")
    if p.startswith("+20"):
        p = "0" + p[3:]
    elif p.startswith("0020"):
        p = "0" + p[4:]
    return p


# --------------------------------------------------------------------- tools
TOOLS = [
    {
        "name": "search_trips",
        "description": "دوّر على الرحلات المتاحة. كل الفلاتر اختيارية. أسماء المدن بالعربي زي: القاهرة، الإسكندرية، شرم الشيخ، الغردقة، أسوان.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_city": {"type": "string"},
                "to_city": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD (اختياري)"},
            },
        },
    },
    {
        "name": "get_available_seats",
        "description": "اعرف أرقام المقاعد الفاضية في رحلة معينة.",
        "input_schema": {
            "type": "object",
            "properties": {"trip_id": {"type": "string"}},
            "required": ["trip_id"],
        },
    },
    {
        "name": "book_seats_cash",
        "description": (
            "احجز مقاعد بالدفع النقدي في المحطة (حجز مبدئي). "
            "ما تستدعيهاش إلا بعد ما العميل يأكد صراحةً على الرحلة والمقاعد والاسم ورقم الموبايل."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trip_id": {"type": "string"},
                "customer_name": {"type": "string"},
                "customer_phone": {"type": "string"},
                "seats": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["trip_id", "customer_name", "customer_phone", "seats"],
        },
    },
    {
        "name": "get_booking",
        "description": "اعرض تفاصيل حجز بكود PNR، بشرط رقم الموبايل اللي اتحجز بيه.",
        "input_schema": {
            "type": "object",
            "properties": {"pnr": {"type": "string"}, "customer_phone": {"type": "string"}},
            "required": ["pnr", "customer_phone"],
        },
    },
]


def t_search_trips(db, a, sync):
    q = ("SELECT id, from_city, from_station, to_city, to_station, departure_time_label, "
         "arrival_time_label, duration, trip_date, price, bus_class_label, total_seats "
         "FROM trips WHERE status = 'ready'")
    args = []
    if a.get("from_city"):
        q += " AND from_city = ?"
        args.append(str(a["from_city"]).strip())
    if a.get("to_city"):
        q += " AND to_city = ?"
        args.append(str(a["to_city"]).strip())
    if a.get("date"):
        q += " AND trip_date = ?"
        args.append(str(a["date"]).strip())
    q += " ORDER BY trip_date, departure_time LIMIT 10"
    conn = _conn(db)
    try:
        cur = conn.cursor()
        out = []
        for r in cur.execute(q, args).fetchall():
            d = dict(r)
            d["seats_left"] = d.pop("total_seats") - len(_booked_seats(conn.cursor(), d["id"]))
            out.append(d)
        return out or {"message": "مفيش رحلات مطابقة"}
    finally:
        conn.close()


def t_get_available_seats(db, a, sync):
    conn = _conn(db)
    try:
        cur = conn.cursor()
        trip = cur.execute("SELECT total_seats FROM trips WHERE id = ?", (str(a.get("trip_id", "")),)).fetchone()
        if not trip:
            return {"error": "الرحلة مش موجودة"}
        taken = _booked_seats(cur, a["trip_id"])
        free = [s for s in range(1, trip["total_seats"] + 1) if s not in taken]
        return {"trip_id": a["trip_id"], "available_seats": free}
    finally:
        conn.close()


def t_book_seats_cash(db, a, sync):
    trip_id = str(a.get("trip_id", ""))
    name = str(a.get("customer_name", "")).strip()
    phone = _norm_phone(a.get("customer_phone", ""))
    seats = a.get("seats")

    if len(name) < 3 or len(name) > 80:
        return {"error": "الاسم مش صالح"}
    if not (phone.isdigit() and len(phone) == 11 and phone.startswith("01")):
        return {"error": "رقم الموبايل لازم يكون 11 رقم ويبدأ بـ 01"}
    if (not isinstance(seats, list) or not seats
            or not all(isinstance(s, int) and not isinstance(s, bool) for s in seats)
            or len(set(seats)) != len(seats)):
        return {"error": "المقاعد غير صالحة"}
    if len(seats) > MAX_SEATS_PER_BOOKING:
        return {"error": f"الحد الأقصى {MAX_SEATS_PER_BOOKING} مقاعد في الحجز الواحد"}

    conn = _conn(db)
    conn.isolation_level = None  # تحكم يدوي في الـ transaction
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")  # يمنع الحجز المزدوج
        trip = cur.execute(
            "SELECT price, from_city, to_city, departure_time_label, trip_date, bus_number, "
            "bus_class_label, total_seats, status FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not trip or trip["status"] != "ready":
            cur.execute("ROLLBACK")
            return {"error": "الرحلة مش متاحة للحجز"}
        if any(s < 1 or s > trip["total_seats"] for s in seats):
            cur.execute("ROLLBACK")
            return {"error": f"أرقام المقاعد من 1 لـ {trip['total_seats']}"}
        taken = _booked_seats(cur, trip_id)
        clash = [s for s in seats if s in taken]
        if clash:
            cur.execute("ROLLBACK")
            return {"error": f"المقاعد {clash} اتحجزت قبل كده"}

        pnr = f"EXP-{secrets.randbelow(90000) + 10000}"
        total = len(seats) * trip["price"]  # السعر من الداتابيز مش من البوت
        cur.execute(
            "INSERT INTO bookings (pnr, trip_id, customer_name, customer_phone, national_id, seats, "
            "total_amount, payment_method, payment_status, boarded) "
            "VALUES (?, ?, ?, ?, '---', ?, ?, 'cash', 'pending_cash', 0)",
            (pnr, trip_id, name, phone, json.dumps(sorted(seats)), total))
        cur.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        print("⚠️ chatbot booking error:", e)
        return {"error": "حصلت مشكلة في الحجز، جرب تاني"}
    finally:
        conn.close()

    try:
        sync()
    except Exception as e:
        print("⚠️ excel sync error:", e)
    print(f"🤖 [Chatbot booking] {pnr} trip={trip_id} seats={seats}")
    return {
        "pnr": pnr, "from": trip["from_city"], "to": trip["to_city"],
        "date": trip["trip_date"], "time": trip["departure_time_label"],
        "bus": trip["bus_number"], "class": trip["bus_class_label"],
        "seats": sorted(seats), "total_amount": total,
        "payment": "نقدي في المحطة (حجز مبدئي)",
    }


def t_get_booking(db, a, sync):
    conn = _conn(db)
    try:
        r = conn.execute(
            "SELECT b.pnr, b.customer_name, b.customer_phone, b.seats, b.total_amount, b.payment_status, "
            "b.boarded, t.from_city, t.to_city, t.trip_date, t.departure_time_label "
            "FROM bookings b LEFT JOIN trips t ON b.trip_id = t.id WHERE b.pnr = ?",
            (str(a.get("pnr", "")).strip().upper(),)).fetchone()
        # نفس الرسالة في الحالتين عشان ما نكشفش وجود الحجز
        if not r or _norm_phone(r["customer_phone"]) != _norm_phone(a.get("customer_phone", "")):
            return {"error": "مفيش حجز بالبيانات دي"}
        d = dict(r)
        d.pop("customer_phone")
        try:
            d["seats"] = json.loads(d["seats"])
        except Exception:
            pass
        return d
    finally:
        conn.close()


HANDLERS = {
    "search_trips": t_search_trips,
    "get_available_seats": t_get_available_seats,
    "book_seats_cash": t_book_seats_cash,
    "get_booking": t_get_booking,
}


def system_prompt():
    return f"""انت مساعد "محطة إكسبريس" لحجز تذاكر الأتوبيسات في مصر. اتكلم بالعامية المصرية، باختصار ولطف.
- جاوب عن الرحلات والأسعار والمواعيد والمقاعد باستخدام الأدوات بس، وما تألفش أي معلومة.
- من الشات تقدر تحجز بالدفع النقدي في المحطة بس (حجز مبدئي). للدفع بالكارت أو المحفظة وكروكي المقاعد وتذكرة الـ QR وجّه العميل لصفحة الحجز في الموقع.
- قبل الحجز اسأل عن: الاسم ورقم الموبايل وأرقام المقاعد (اعرض المقاعد الفاضية)، ولخّص: خط السير، التاريخ، الميعاد، المقاعد، السعر الكلي، واطلب تأكيد صريح.
- ما تستدعيش book_seats_cash إلا بعد التأكيد. الحد الأقصى {MAX_SEATS_PER_BOOKING} مقاعد.
- بعد الحجز اديه كود الحجز (PNR) وقوله يحتفظ بيه ويدفع في المحطة.
- لو السؤال برة نطاق المحطة اعتذر بلطف.
- التاريخ النهارده: {datetime.now().strftime('%Y-%m-%d')}."""


# ---------------------------------------------------------------- Claude call
def _call_claude(api_key, messages):
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 800,
        "system": system_prompt(),
        "tools": TOOLS,
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=payload, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _clean_history(raw):
    if not isinstance(raw, list):
        return None
    msgs = []
    for m in raw[-MAX_HISTORY:]:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            return None
        c = m.get("content")
        if not isinstance(c, str) or not c.strip() or len(c) > MAX_MESSAGE_LEN * 4:
            return None
        msgs.append({"role": m["role"], "content": c})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    if not msgs or msgs[-1]["role"] != "user" or len(msgs[-1]["content"]) > MAX_MESSAGE_LEN:
        return None
    return msgs


def chat(raw_messages, db_file, sync_fn, ip="?"):
    """بترجع {'text': ...} أو {'error': ...}"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"error": "الشات غير مفعّل: ANTHROPIC_API_KEY مش متظبط على السيرفر"}
    if not _allowed(ip):
        return {"error": "طلبات كتير، استنى شوية وجرب تاني"}
    messages = _clean_history(raw_messages)
    if messages is None:
        return {"error": "رسالة غير صالحة"}

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            resp = _call_claude(api_key, messages)
            content = resp.get("content", [])
            if resp.get("stop_reason") != "tool_use":
                text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
                return {"text": text or "ممكن توضّح أكتر؟"}
            messages.append({"role": "assistant", "content": content})
            results = []
            for b in content:
                if b.get("type") != "tool_use":
                    continue
                fn = HANDLERS.get(b["name"])
                try:
                    out = fn(db_file, b.get("input") or {}, sync_fn) if fn else {"error": "أداة غير معروفة"}
                except Exception as e:
                    print("⚠️ tool error:", b["name"], e)
                    out = {"error": "حصلت مشكلة"}
                results.append({"type": "tool_result", "tool_use_id": b["id"],
                                "content": json.dumps(out, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
        return {"error": "حصلت مشكلة، جرب تاني"}
    except urllib.error.HTTPError as e:
        print("⚠️ Claude API HTTP error:", e.code, e.read()[:300])
        return {"error": "الشات مش متاح دلوقتي، جرب بعد شوية"}
    except Exception as e:
        print("⚠️ chat error:", e)
        return {"error": "الشات مش متاح دلوقتي، جرب بعد شوية"}
