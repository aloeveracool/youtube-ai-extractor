let currentVideoInfo = null;
let activePollingTimer = null;
let currentSummaryText = "";

document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  checkApiSettings();
  loadHistory();
  setupEventListeners();
});

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  const toastMsg = document.getElementById("toastMsg");
  const toastIcon = document.getElementById("toastIcon");

  toastMsg.textContent = message;
  toastIcon.setAttribute("data-lucide", isError ? "alert-circle" : "check-circle");
  toastIcon.className = `w-4 h-4 ${isError ? "text-rose-400" : "text-emerald-400"}`;
  if (window.lucide) lucide.createIcons();

  toast.classList.remove("translate-y-20", "opacity-0");
  setTimeout(() => {
    toast.classList.add("translate-y-20", "opacity-0");
  }, 3500);
}

function setupEventListeners() {
  // Analyze Video Button
  document.getElementById("btnFetchInfo").addEventListener("click", fetchVideoInfo);
  document.getElementById("urlInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") fetchVideoInfo();
  });

  // Demo Links
  document.querySelectorAll(".demo-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("urlInput").value = btn.dataset.url;
      fetchVideoInfo();
    });
  });

  // Download MP3
  document.getElementById("btnDownloadMp3").addEventListener("click", () => {
    if (!currentVideoInfo) return;
    startDownload("mp3", "320");
  });

  // Download MP4
  document.getElementById("btnDownloadMp4").addEventListener("click", () => {
    if (!currentVideoInfo) return;
    const quality = document.getElementById("videoQualitySelect").value;
    startDownload("mp4", quality);
  });

  // AI Summarize
  document.getElementById("btnSummarize").addEventListener("click", requestSummary);

  // Copy Summary
  document.getElementById("btnCopySummary").addEventListener("click", () => {
    if (!currentSummaryText) return;
    navigator.clipboard.writeText(currentSummaryText).then(() => {
      showToast("요약 내용이 클립보드에 복사되었습니다!");
    });
  });

  // Open Downloads Folder
  document.getElementById("btnOpenFolder").addEventListener("click", async () => {
    try {
      const res = await fetch("/api/open-downloads", { method: "POST" });
      const data = await res.json();
      if (data.success) {
        showToast("다운로드 폴더가 열렸습니다.");
      } else {
        showToast("폴더 열기 실패: " + data.error, true);
      }
    } catch (e) {
      showToast("오류가 발생했습니다.", true);
    }
  });

  // Refresh History
  document.getElementById("btnRefreshHistory").addEventListener("click", loadHistory);

  // Settings Modal
  const settingsModal = document.getElementById("settingsModal");
  document.getElementById("btnOpenSettings").addEventListener("click", () => {
    settingsModal.classList.remove("hidden");
  });
  document.getElementById("btnCloseSettings").addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });
  document.getElementById("btnCancelSettings").addEventListener("click", () => {
    settingsModal.classList.add("hidden");
  });
  document.getElementById("btnSaveSettings").addEventListener("click", saveApiSettings);

  // Player Modal
  const playerModal = document.getElementById("playerModal");
  document.getElementById("btnClosePlayer").addEventListener("click", () => {
    playerModal.classList.add("hidden");
    document.getElementById("playerContainer").innerHTML = "";
  });
}

// Fetch Video Information
async function fetchVideoInfo() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) {
    showToast("유튜브 URL을 입력해 주세요.", true);
    return;
  }

  const loadingBox = document.getElementById("loadingBox");
  const videoCard = document.getElementById("videoCard");
  const summarySection = document.getElementById("summarySection");

  loadingBox.classList.remove("hidden");
  videoCard.classList.add("hidden");
  summarySection.classList.add("hidden");

  try {
    const res = await fetch("/api/video-info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (!data.success) {
      showToast(data.error || "영상 정보를 가져오지 못했습니다.", true);
      loadingBox.classList.add("hidden");
      return;
    }

    currentVideoInfo = data.data;
    renderVideoCard(data.data);
    showToast("영상 정보 분석 완료!");
  } catch (err) {
    showToast("서버와 통신 중 오류가 발생했습니다.", true);
  } finally {
    loadingBox.classList.add("hidden");
  }
}

function renderVideoCard(info) {
  const videoCard = document.getElementById("videoCard");
  document.getElementById("videoThumb").src = info.thumbnail;
  document.getElementById("videoDurationBadge").textContent = info.duration_str;
  document.getElementById("channelName").textContent = info.channel;
  document.getElementById("viewCount").textContent = `조회수 ${(info.view_count || 0).toLocaleString()}회`;
  document.getElementById("videoTitle").textContent = info.title;

  // Render resolutions
  const select = document.getElementById("videoQualitySelect");
  select.innerHTML = "";
  info.available_resolutions.forEach((res) => {
    const opt = document.createElement("option");
    opt.value = res.includes("최고") ? "best" : res;
    opt.textContent = res;
    select.appendChild(opt);
  });

  videoCard.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

// Download Process
async function startDownload(mediaType, quality) {
  const url = currentVideoInfo.original_url;
  const progressCard = document.getElementById("progressCard");
  const progressBar = document.getElementById("progressBar");
  const progressMessage = document.getElementById("progressMessage");
  const progressSpeed = document.getElementById("progressSpeed");
  const progressEta = document.getElementById("progressEta");
  const progressPercent = document.getElementById("progressPercent");

  progressCard.classList.remove("hidden");
  progressBar.style.width = "0%";
  progressMessage.querySelector("span").textContent = `${mediaType.toUpperCase()} 다운로드 요청 중...`;
  progressSpeed.textContent = "연결 중...";
  progressEta.textContent = "";
  progressPercent.textContent = "0%";

  try {
    const res = await fetch("/api/download-start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, media_type: mediaType, quality }),
    });
    const data = await res.json();
    if (!data.success) {
      showToast("다운로드 시작 실패", true);
      progressCard.classList.add("hidden");
      return;
    }

    const jobId = data.job_id;
    pollDownloadProgress(jobId);
  } catch (e) {
    showToast("다운로드 요청 오류 발생", true);
    progressCard.classList.add("hidden");
  }
}

function pollDownloadProgress(jobId) {
  if (activePollingTimer) clearInterval(activePollingTimer);

  activePollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/download-progress/${jobId}`);
      const data = await res.json();
      if (!data.success) return;

      const job = data.data;
      const progressBar = document.getElementById("progressBar");
      const progressMessage = document.getElementById("progressMessage");
      const progressSpeed = document.getElementById("progressSpeed");
      const progressEta = document.getElementById("progressEta");
      const progressPercent = document.getElementById("progressPercent");

      progressBar.style.width = `${job.percent || 0}%`;
      progressPercent.textContent = `${job.percent || 0}%`;
      if (job.message) progressMessage.querySelector("span").textContent = job.message;
      if (job.speed) progressSpeed.textContent = job.speed;
      if (job.eta) progressEta.textContent = `남은 시간: ${job.eta}`;

      if (job.status === "completed") {
        clearInterval(activePollingTimer);
        showToast(`🎉 ${job.filename} 다운로드 완료!`);
        setTimeout(() => {
          document.getElementById("progressCard").classList.add("hidden");
        }, 3000);
        loadHistory();
      } else if (job.status === "error") {
        clearInterval(activePollingTimer);
        showToast(job.message || "다운로드 중 오류가 발생했습니다.", true);
      }
    } catch (e) {
      console.error(e);
    }
  }, 600);
}

// Request AI Summary
async function requestSummary() {
  if (!currentVideoInfo) return;

  const summarySection = document.getElementById("summarySection");
  const summaryContent = document.getElementById("summaryContent");
  const fullScriptBox = document.getElementById("fullScriptBox");
  const summaryBadge = document.getElementById("summaryBadge");
  const summaryMeta = document.getElementById("summaryMeta");

  summarySection.classList.remove("hidden");
  summaryContent.innerHTML = `
    <div class="py-8 text-center space-y-3">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent"></div>
      <p class="text-sm text-purple-300 font-medium">자막 스크립트를 추출하고 AI가 3줄 요약 및 타임스탬프를 분석하는 중입니다...</p>
    </div>
  `;

  try {
    const res = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentVideoInfo.original_url,
        video_title: currentVideoInfo.title,
      }),
    });
    const data = await res.json();

    if (!data.success) {
      summaryContent.innerHTML = `
        <div class="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          ❌ 요약 생성 실패: ${data.error || "자막을 가져올 수 없거나 요약에 실패했습니다."}
        </div>
      `;
      return;
    }

    fullScriptBox.textContent = data.full_script || "(추출된 전문 없음)";
    summaryMeta.textContent = `언어: ${data.language} (${data.is_generated ? "자동생성 자막" : "공식 자막"}) · ${data.segment_count}개 구간 분석`;

    if (data.type === "gemini") {
      summaryBadge.textContent = "Gemini 3.8 Flash";
      summaryBadge.className = "text-xs px-2.5 py-0.5 rounded-full bg-[#69DCB9]/20 text-[#69DCB9] border border-[#69DCB9]/30 font-semibold";
      currentSummaryText = data.markdown;
      summaryContent.innerHTML = marked.parse(data.markdown);
    } else {
      summaryBadge.textContent = "ALOIA 스마트 분석";
      summaryBadge.className = "text-xs px-2.5 py-0.5 rounded-full bg-[#2D785F]/30 text-[#69DCB9] border border-[#69DCB9]/30 font-semibold";
      
      const fb = data.data;
      let textToCopy = `📌 [Aloia 핵심 3줄 요약]\n` + fb.summary_3lines.join("\n") + `\n\n⏱️ [타임라인 주요 구간]\n`;
      fb.timeline.forEach(t => textToCopy += `[${t.timestamp}] ${t.topic}\n`);
      currentSummaryText = textToCopy;

      let html = `
        <div class="space-y-6">
          <!-- 3줄 요약 카드 -->
          <div class="p-5 rounded-xl bg-[#070b0e] border border-[#69DCB9]/40 space-y-3 shadow-lg shadow-[#69DCB9]/5">
            <h4 class="text-sm font-bold text-[#69DCB9] flex items-center space-x-2">
              <span>📌 Aloia 핵심 3줄 요약</span>
            </h4>
            <div class="space-y-2 text-sm text-slate-100 font-medium">
              ${fb.summary_3lines.map(line => `<div class="p-3 rounded-lg bg-[#0c1318] border border-[#1b2d28] leading-relaxed">${line}</div>`).join('')}
            </div>
          </div>

          <!-- 타임라인 챕터 -->
          <div class="space-y-3">
            <h4 class="text-sm font-bold text-white">⏱️ 타임라인별 주요 구간 정리</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              ${fb.timeline.map(item => `
                <div class="p-3 rounded-lg bg-[#070b0e] border border-[#1b2d28] flex items-start space-x-3 hover:border-[#69DCB9]/30 transition">
                  <span class="text-xs font-mono font-bold text-[#69DCB9] bg-[#2D785F]/20 px-2 py-1 rounded border border-[#69DCB9]/20">${item.timestamp}</span>
                  <span class="text-xs text-slate-300 leading-5">${item.topic}</span>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- 키워드 -->
          <div class="flex items-center space-x-2 pt-2">
            <span class="text-xs text-slate-400">핵심 키워드:</span>
            <div class="flex flex-wrap gap-1.5">
              ${fb.keywords.map(kw => `<span class="text-xs px-2.5 py-1 rounded-full bg-[#0c1816] border border-[#2D785F]/60 text-[#69DCB9] font-medium">#${kw}</span>`).join('')}
            </div>
          </div>

          <!-- 안내 배너 -->
          <div class="p-3.5 rounded-lg bg-[#070b0e] border border-[#2D785F]/40 text-xs text-[#69DCB9] flex items-center space-x-2">
            <i data-lucide="info" class="w-4 h-4 flex-shrink-0"></i>
            <span>${fb.note}</span>
          </div>
        </div>
      `;
      summaryContent.innerHTML = html;
    }

    if (window.lucide) lucide.createIcons();
    showToast("Aloia AI 영상 요약이 완료되었습니다!");
  } catch (e) {
    summaryContent.innerHTML = `<div class="text-rose-400 text-xs">요약 요청 중 오류가 발생했습니다.</div>`;
  }
}

// Download History
async function loadHistory() {
  const container = document.getElementById("historyList");
  try {
    const res = await fetch("/api/history");
    const data = await res.json();

    if (!data.success || !data.files.length) {
      container.innerHTML = `
        <div class="text-center py-6 text-slate-500 text-xs">
          아직 다운로드된 파일이 없습니다. 상단에서 음원이나 영상을 다운로드해 보세요!
        </div>
      `;
      return;
    }

    container.innerHTML = "";
    data.files.forEach((file) => {
      const isAudio = file.ext === "mp3" || file.ext === "m4a";
      const icon = isAudio ? "music" : "video";
      const iconColor = isAudio ? "text-[#69DCB9] bg-[#2D785F]/20" : "text-emerald-400 bg-emerald-900/20";

      const item = document.createElement("div");
      item.className = "p-3 rounded-xl bg-[#070b0e] border border-[#1b2d28] hover:border-[#69DCB9]/40 transition flex items-center justify-between";
      item.innerHTML = `
        <div class="flex items-center space-x-3 overflow-hidden mr-3">
          <div class="w-9 h-9 rounded-lg flex-shrink-0 flex items-center justify-center border border-[#1b2d28] ${iconColor}">
            <i data-lucide="${icon}" class="w-4 h-4"></i>
          </div>
          <div class="truncate">
            <p class="text-xs font-semibold text-slate-200 truncate">${file.name}</p>
            <p class="text-[11px] text-[#69DCB9]/80 uppercase font-mono">${file.ext} · ${file.size_mb} MB</p>
          </div>
        </div>

        <div class="flex items-center space-x-1.5 flex-shrink-0">
          <button class="btn-play px-2.5 py-1.5 rounded-lg bg-[#0c1318] hover:bg-[#111b22] text-[#69DCB9] hover:text-white text-xs flex items-center space-x-1 transition border border-[#1b2d28] hover:border-[#69DCB9]" data-name="${file.name}" data-ext="${file.ext}">
            <i data-lucide="play" class="w-3.5 h-3.5 text-[#69DCB9]"></i>
            <span>재생</span>
          </button>
          <a href="/api/stream/${encodeURIComponent(file.name)}" download class="p-1.5 rounded-lg bg-[#0c1318] hover:bg-[#111b22] text-slate-300 hover:text-[#69DCB9] transition border border-[#1b2d28]" title="다운로드">
            <i data-lucide="download" class="w-3.5 h-3.5"></i>
          </a>
          <button class="btn-delete p-1.5 rounded-lg bg-[#0c1318] hover:bg-rose-950/40 hover:text-rose-400 text-slate-500 transition border border-[#1b2d28]" data-name="${file.name}" title="삭제">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
      container.appendChild(item);
    });

    // Attach play & delete handlers
    container.querySelectorAll(".btn-play").forEach((btn) => {
      btn.addEventListener("click", () => playMedia(btn.dataset.name, btn.dataset.ext));
    });

    container.querySelectorAll(".btn-delete").forEach((btn) => {
      btn.addEventListener("click", () => deleteMedia(btn.dataset.name));
    });

    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error(e);
  }
}

function playMedia(filename, ext) {
  const modal = document.getElementById("playerModal");
  const title = document.getElementById("playerModalTitle");
  const container = document.getElementById("playerContainer");

  title.textContent = filename;
  const streamUrl = `/api/stream/${encodeURIComponent(filename)}`;

  if (ext === "mp3" || ext === "m4a") {
    container.className = "rounded-xl overflow-hidden bg-slate-950 p-6 flex flex-col items-center justify-center space-y-4";
    container.innerHTML = `
      <div class="w-16 h-16 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center">
        <i data-lucide="music" class="w-8 h-8"></i>
      </div>
      <audio controls autoplay src="${streamUrl}" class="w-full"></audio>
    `;
  } else {
    container.className = "rounded-xl overflow-hidden bg-black aspect-video flex items-center justify-center";
    container.innerHTML = `
      <video controls autoplay src="${streamUrl}" class="w-full h-full object-contain"></video>
    `;
  }

  if (window.lucide) lucide.createIcons();
  modal.classList.remove("hidden");
}

async function deleteMedia(filename) {
  if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) return;
  try {
    const res = await fetch("/api/delete-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    const data = await res.json();
    if (data.success) {
      showToast("파일이 삭제되었습니다.");
      loadHistory();
    } else {
      showToast("삭제 실패: " + data.error, true);
    }
  } catch (e) {
    showToast("오류가 발생했습니다.", true);
  }
}

// API Key Management
async function checkApiSettings() {
  try {
    const res = await fetch("/api/settings");
    const data = await res.json();
    const badge = document.getElementById("apiKeyBadge");
    const statusText = document.getElementById("apiKeyStatusText");
    const input = document.getElementById("apiKeyInput");

    if (data.has_key) {
      badge.className = "w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400";
      statusText.textContent = `등록된 키: ${data.masked_key} (Gemini AI 활성화됨)`;
      statusText.className = "text-[11px] text-emerald-400";
    } else {
      badge.className = "w-2 h-2 rounded-full bg-amber-400";
      statusText.textContent = "키가 설정되지 않음 (스마트 기본 요약 사용 중)";
      statusText.className = "text-[11px] text-slate-400";
    }
  } catch (e) {
    console.error(e);
  }
}

async function saveApiSettings() {
  const key = document.getElementById("apiKeyInput").value.trim();
  if (!key) {
    showToast("API 키를 입력해 주세요.", true);
    return;
  }
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message);
      document.getElementById("settingsModal").classList.add("hidden");
      document.getElementById("apiKeyInput").value = "";
      checkApiSettings();
    }
  } catch (e) {
    showToast("저장 중 오류가 발생했습니다.", true);
  }
}
