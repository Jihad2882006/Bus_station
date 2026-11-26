/* ويدجت الشات البوت - ملف واحد مستقل، بيحقن CSS و HTML بنفسه.
   لو الواجهة على دومين مختلف عن السيرفر: window.BUS_API_BASE = "https://your-server.com" قبل تحميل الملف. */
(function () {
  const API = (window.BUS_API_BASE || "") + "/api/chat";
  const history = [];

  const css = `
  #bsc-btn{position:fixed;bottom:20px;left:20px;z-index:9999;width:58px;height:58px;border-radius:50%;border:0;background:#0f766e;color:#fff;font-size:26px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.3)}
  #bsc-box{position:fixed;bottom:90px;left:20px;z-index:9999;width:min(370px,calc(100vw - 24px));height:min(520px,calc(100dvh - 120px));display:none;flex-direction:column;background:#fff;color:#111;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.3);font-family:system-ui,"Segoe UI",Tahoma,sans-serif;direction:rtl}
  #bsc-box.open{display:flex}
  #bsc-head{background:#0f766e;color:#fff;padding:12px 14px;font-weight:700;display:flex;justify-content:space-between;align-items:center}
  #bsc-head button{background:none;border:0;color:#fff;font-size:20px;cursor:pointer}
  #bsc-log{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;background:#f3f4f6}
  .bsc-m{max-width:85%;padding:9px 13px;border-radius:14px;line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere;font-size:15px}
  .bsc-u{align-self:flex-start;background:#0f766e;color:#fff}
  .bsc-b{align-self:flex-end;background:#fff;border:1px solid #d1d5db}
  #bsc-f{display:flex;gap:6px;padding:8px;border-top:1px solid #e5e7eb;background:#fff}
  #bsc-f input{flex:1;min-width:0;padding:10px;border:1px solid #d1d5db;border-radius:10px;font-size:16px}
  #bsc-f button{padding:0 14px;border:0;border-radius:10px;background:#0f766e;color:#fff;font-size:15px;cursor:pointer}
  #bsc-f button:disabled{opacity:.5}`;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  const btn = document.createElement("button");
  btn.id = "bsc-btn"; btn.setAttribute("aria-label", "المساعد"); btn.textContent = "💬";
  const box = document.createElement("div");
  box.id = "bsc-box";
  box.innerHTML =
    '<div id="bsc-head"><span>🚌 مساعد المحطة</span><button type="button" aria-label="إغلاق">✕</button></div>' +
    '<div id="bsc-log"></div>' +
    '<form id="bsc-f"><input placeholder="اكتب رسالتك..." autocomplete="off" maxlength="1000"><button>إرسال</button></form>';
  document.body.append(btn, box);

  const log = box.querySelector("#bsc-log");
  const form = box.querySelector("#bsc-f");
  const input = form.querySelector("input");
  const send = form.querySelector("button");

  function add(text, cls) {
    const d = document.createElement("div");
    d.className = "bsc-m " + cls;
    d.textContent = text; // textContent: حماية من XSS
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  add("أهلاً بيك في محطة إكسبريس 👋 أقدر أدوّر لك على رحلات وأحجزلك. رايح فين؟", "bsc-b");

  btn.onclick = () => { box.classList.toggle("open"); if (box.classList.contains("open")) input.focus(); };
  box.querySelector("#bsc-head button").onclick = () => box.classList.remove("open");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = ""; send.disabled = true;
    add(text, "bsc-u");
    history.push({ role: "user", content: text });
    const wait = add("...", "bsc-b");
    try {
      const r = await fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history.slice(-20) }),
      });
      const data = await r.json();
      const reply = data.text || data.error || "حصلت مشكلة، جرب تاني.";
      wait.textContent = reply;
      if (data.text) history.push({ role: "assistant", content: data.text });
      else history.pop();
    } catch (err) {
      wait.textContent = "في مشكلة في الاتصال، جرب تاني.";
      history.pop();
    }
    send.disabled = false; input.focus();
    log.scrollTop = log.scrollHeight;
  });
})();
