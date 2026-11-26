#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بيعدّل server.py و index.html تلقائياً عشان الشات يشتغل.
الاستخدام (من فولدر المشروع، جنب chatbot.py و chat-widget.js):

    python3 apply_chat_patch.py
    python3 apply_chat_patch.py https://رابط-السيرفر     # لو الواجهة على دومين تاني

بيعمل نسخة احتياطية .bak لكل ملف قبل التعديل، ولو شغّلته مرتين مش هيكرر التعديل.
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
api_base = sys.argv[1].strip().rstrip("/") if len(sys.argv) > 1 else ""


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def fail(msg):
    print("❌", msg)
    print("ما اتعدّلش أي ملف. ابعتلي الرسالة دي وأظبطها.")
    sys.exit(1)


for needed in ("server.py", "index.html", "chatbot.py", "chat-widget.js"):
    if not os.path.exists(os.path.join(HERE, needed)):
        fail(f"الملف {needed} مش موجود في نفس الفولدر")

# ------------------------------------------------------------ server.py
s = read("server.py")
orig_s = s

if "import chatbot" not in s:
    if "from datetime import datetime, timedelta" not in s:
        fail("ما لقيتش سطر 'from datetime import datetime, timedelta' في server.py")
    s = s.replace("from datetime import datetime, timedelta",
                  "from datetime import datetime, timedelta\nimport chatbot", 1)

if "/api/chat" not in s:
    pat = re.compile(
        r"^([ \t]*)elif path == '/api/driver/assign-trip':[ \t]*\n"
        r"[ \t]*self\.handle_driver_assign_trip\(body\)[ \t]*\n", re.M)
    m = pat.search(s)
    if not m:
        fail("ما لقيتش مكان /api/driver/assign-trip في do_POST")
    ind = m.group(1)
    s = s[:m.end()] + f"{ind}elif path == '/api/chat':\n{ind}    self.handle_chat(body)\n" + s[m.end():]

if "def handle_chat" not in s:
    m = re.search(r"^([ \t]*)def handle_register\(self, body\):", s, re.M)
    if not m:
        fail("ما لقيتش def handle_register في server.py")
    ind = m.group(1)
    method = (
        f"{ind}def handle_chat(self, body):\n"
        f"{ind}    result = chatbot.chat(body.get('messages', []), DB_FILE,\n"
        f"{ind}                          sync_excel_files, self.client_address[0])\n"
        f"{ind}    self.send_json(result, 200 if 'text' in result else 400)\n\n"
    )
    s = s[:m.start()] + method + s[m.start():]

if re.search(r"^PORT = 8080\s*$", s, re.M):
    s = re.sub(r"^PORT = 8080\s*$", "PORT = int(os.environ.get('PORT', 8080))", s, count=1, flags=re.M)

# ----------------------------------------------------------- index.html
h = read("index.html")
orig_h = h
if "chat-widget.js" not in h:
    tag = ""
    if api_base:
        tag += f'<script>window.BUS_API_BASE = "{api_base}";</script>\n'
    tag += '<script src="chat-widget.js"></script>\n'
    idx = h.lower().rfind("</body>")
    if idx == -1:
        fail("ما لقيتش </body> في index.html")
    h = h[:idx] + tag + h[idx:]

# ---------------------------------------------------------------- write
for name, new, old in (("server.py", s, orig_s), ("index.html", h, orig_h)):
    if new != old:
        shutil.copyfile(os.path.join(HERE, name), os.path.join(HERE, name + ".bak"))
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(new)
        print(f"✅ اتعدّل {name} (نسخة احتياطية: {name}.bak)")
    else:
        print(f"ℹ️ {name} متعدّل قبل كده، ما اتغيّرش")

print("\nخلاص. دلوقتي ارفع: chatbot.py, chat-widget.js, server.py, index.html")
print("وما ترفعش ملفات .bak")
