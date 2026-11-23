const $ = (id) => document.getElementById(id);
let latestCodes = [];
let latestFinalUrl = "";

function setMessage(text, error = false) {
  $("message").textContent = text;
  $("message").style.color = error ? "#ffb9a8" : "#9df0c4";
}

function makeText(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text;
  return el;
}

function renderResult(data) {
  $("results").classList.remove("hidden");
  $("status").textContent = data.status;
  $("redirectCount").textContent = data.redirects.length;
  $("codeCount").textContent = data.codes.length;
  $("pageTitle").textContent = data.title;
  $("description").textContent = data.description || "Không có mô tả.";
  $("finalUrl").textContent = data.final_url;
  latestCodes = data.codes;
  latestFinalUrl = data.final_url;

  const redirects = $("redirectList");
  redirects.replaceChildren();
  if (!data.redirects.length) redirects.textContent = "Không có chuyển hướng.";
  data.redirects.forEach((r, i) => {
    const item = makeText("div", "redirect-item", `${i + 1}. HTTP ${r.status}\n${r.url}\n→ ${r.destination}`);
    redirects.appendChild(item);
  });

  const codes = $("codes");
  codes.replaceChildren();
  if (!data.codes.length) codes.textContent = "Không tìm thấy mã có nhãn phù hợp.";
  data.codes.forEach(code => codes.appendChild(makeText("span", "code-pill", code)));

  const links = $("links");
  links.replaceChildren();
  if (!data.links.length) links.textContent = "Không có liên kết.";
  data.links.forEach(link => {
    const wrap = makeText("div", "link-item", link.label);
    const a = document.createElement("a");
    a.href = link.url;
    a.textContent = link.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    wrap.appendChild(a);
    links.appendChild(wrap);
  });
  $("preview").textContent = data.text_preview || "(Không có văn bản)";
}

async function analyze() {
  const url = $("urlInput").value.trim();
  if (!url) return setMessage("Bạn chưa nhập đường link.", true);

  $("analyzeBtn").disabled = true;
  $("analyzeBtn").textContent = "Đang phân tích...";
  setMessage("Đang tải và phân tích trang...");
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({url})
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Không thể phân tích URL.");
    renderResult(data);
    setMessage("Phân tích hoàn tất.");
  } catch (err) {
    setMessage(err.message || "Có lỗi xảy ra.", true);
  } finally {
    $("analyzeBtn").disabled = false;
    $("analyzeBtn").textContent = "Phân tích";
  }
}

$("analyzeBtn").addEventListener("click", analyze);
$("urlInput").addEventListener("keydown", e => { if (e.key === "Enter") analyze(); });
$("copyFinal").addEventListener("click", async () => {
  if (latestFinalUrl) await navigator.clipboard.writeText(latestFinalUrl);
});
$("copyCodes").addEventListener("click", async () => {
  if (latestCodes.length) await navigator.clipboard.writeText(latestCodes.join("\n"));
});
