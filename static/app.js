const $ = id => document.getElementById(id);
const esc = s => String(s ?? "");
function msg(id, text, error=false){ const e=$(id); e.textContent=text; e.className="message"+(error?" error":""); }
function el(tag, cls, text){ const e=document.createElement(tag); if(cls)e.className=cls; if(text!==undefined)e.textContent=text; return e; }
function switchTab(name){
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active",b.dataset.tab===name));
  document.querySelectorAll(".tab-panel").forEach(p=>p.classList.toggle("active",p.id===name));
  if(name==="history") loadHistory();
}
document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click",()=>switchTab(b.dataset.tab)));

function renderOne(data){
  const card=el("article","panel result-card");
  const head=el("div","section-head");
  const title=el("h2","",data.title||"Kết quả phân tích");
  const status=el("span","status",data.status?`HTTP ${data.status}`:"Văn bản");
  head.append(title,status); card.append(head);
  const url=el("p","url",data.final_url||data.input_url||""); card.append(url);
  const stats=el("div","mini-stats");
  [["Redirect",data.redirects?.length||0],["Mã tìm thấy",data.codes?.length||0],["Liên kết",data.links?.length||0]].forEach(([k,v])=>{const x=el("div","mini-stat");x.append(el("small","",k),el("b","",v));stats.append(x);});
  card.append(stats);
  if(data.description)card.append(el("p","muted",data.description));
  if(data.codes?.length){card.append(el("h3","","Mã phát hiện"));const codes=el("div","code-list");data.codes.forEach(c=>codes.append(el("span","code-pill",c)));card.append(codes);}
  if(data.redirects?.length){card.append(el("h3","","Chuỗi chuyển hướng"));data.redirects.forEach((r,i)=>card.append(el("p","redirect",`${i+1}. HTTP ${r.status}: ${r.url} → ${r.destination}`)));}
  if(data.links?.length){card.append(el("h3","","Liên kết trên trang"));const list=el("div","link-list");data.links.forEach(l=>{const a=el("a","",l.url);a.href=l.url;a.target="_blank";a.rel="noopener noreferrer";const row=el("div","link-row");row.append(el("b","",l.label),a);list.append(row);});card.append(list);}
  if(data.text_preview){const details=el("details","");details.append(el("summary","","Xem trước văn bản"));details.append(el("pre","preview",data.text_preview));card.append(details);}
  return card;
}
async function analyzeUrls(){
  const urls=$("urls").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if(!urls.length)return msg("autoMessage","Hãy nhập ít nhất một URL.",true);
  if(urls.length>10)return msg("autoMessage","Chỉ hỗ trợ tối đa 10 URL mỗi lần.",true);
  const btn=$("analyzeBtn");btn.disabled=true;btn.textContent="Đang phân tích...";
  $("results").replaceChildren();msg("autoMessage","Đang kiểm tra các URL...");
  try{
    const r=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({urls})});
    const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||"Có lỗi xảy ra.");
    d.results.forEach(item=>{if(item.ok)$("results").append(renderOne(item));else{const c=el("article","panel error-card");c.append(el("h3","","Không phân tích được"),el("p","url",item.input_url),el("p","error-text",item.error));$("results").append(c);}});
    msg("autoMessage",`Hoàn tất: ${d.results.filter(x=>x.ok).length}/${d.results.length} URL thành công.`);
  }catch(e){msg("autoMessage",e.message,true);}finally{btn.disabled=false;btn.textContent="Phân tích URL";}
}
$("analyzeBtn").addEventListener("click",analyzeUrls);
$("openTab").addEventListener("click",()=>{const u=$("manualUrl").value.trim();if(!u)return msg("manualMessage","Hãy nhập URL trước.",true);try{const p=new URL(u.includes("://")?u:"https://"+u);if(!["http:","https:"].includes(p.protocol))throw Error();window.open(p.href,"_blank","noopener,noreferrer");msg("manualMessage","Đã yêu cầu mở trang ở tab mới. Hãy tự thao tác và sao chép nội dung công khai.");}catch{msg("manualMessage","URL không hợp lệ.",true);}});
$("analyzeTextBtn").addEventListener("click",async()=>{
  const text=$("manualText").value.trim();if(!text)return msg("manualMessage","Hãy dán nội dung cần phân tích.",true);
  const b=$("analyzeTextBtn");b.disabled=true;msg("manualMessage","Đang phân tích nội dung...");
  try{const r=await fetch("/api/analyze-text",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text,source_url:$("sourceUrl").value.trim()})});const d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||"Không thể phân tích.");$("manualResult").replaceChildren(renderOne(d));msg("manualMessage","Đã phân tích và lưu lịch sử.");}
  catch(e){msg("manualMessage",e.message,true);}finally{b.disabled=false;}
});
async function loadHistory(){
  const q=encodeURIComponent($("historySearch").value.trim());
  try{const r=await fetch(`/api/history?q=${q}&limit=100`);const d=await r.json();const box=$("historyList");box.replaceChildren();
    if(!d.items.length)box.append(el("p","muted","Chưa có lịch sử phù hợp."));
    d.items.forEach(item=>{const row=el("div","history-item");const info=el("div","history-info");info.append(el("b","",item.title||item.input_value),el("small","",`${new Date(item.created_at).toLocaleString("vi-VN")} · ${item.kind==="url"?"URL":"Văn bản"} · ${item.codes.join(", ")||"Không thấy mã"}`));if(item.final_url)info.append(el("a","",item.final_url));const del=el("button","danger small","Xóa");del.addEventListener("click",()=>deleteItem(item.id));row.append(info,del);box.append(row);});
  }catch{msg("historyMessage","Không tải được lịch sử.",true);}
}
async function deleteItem(id){if(!confirm("Xóa mục lịch sử này?"))return;await fetch(`/api/history/${id}`,{method:"DELETE"});loadHistory();}
$("searchHistory").addEventListener("click",loadHistory);
$("historySearch").addEventListener("keydown",e=>{if(e.key==="Enter")loadHistory();});
$("clearHistory").addEventListener("click",async()=>{if(!confirm("Xóa toàn bộ lịch sử?"))return;await fetch("/api/history",{method:"DELETE"});loadHistory();msg("historyMessage","Đã xóa lịch sử.");});
