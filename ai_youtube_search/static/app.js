// CINE-AI : Universal Omnilingual YouTube Search Engine Logic
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  // DOM Elements
  const searchForm = document.getElementById('search-form');
  const urlInput = document.getElementById('url-input');
  const searchBtn = document.getElementById('search-btn');
  const pasteBtn = document.getElementById('paste-btn');
  const sampleChips = document.querySelectorAll('.sample-chip');

  const playerPlaceholder = document.getElementById('player-placeholder');
  const statusOverlay = document.getElementById('status-overlay');
  const statusOverlayText = document.getElementById('status-overlay-text');
  const cachedIndicator = document.getElementById('cached-indicator');
  const cachedIndicatorText = document.getElementById('cached-indicator-text');

  const playToggleBtn = document.getElementById('btn-play-toggle');
  const playIcon = document.getElementById('play-icon');
  const playText = document.getElementById('play-text');
  const backwardBtn = document.getElementById('btn-backward');
  const forwardBtn = document.getElementById('btn-forward');
  const currentTimeDisplay = document.getElementById('current-time-display');
  const totalDurationDisplay = document.getElementById('total-duration-display');

  // Volume
  const volumeSlider = document.getElementById('volume-slider');
  const volumeValueText = document.getElementById('volume-value-text');
  const muteBtn = document.getElementById('mute-btn');
  const volumeIcon = document.getElementById('volume-icon');

  // Metadata Card
  const metaTitle = document.getElementById('meta-title');
  const metaChannel = document.getElementById('meta-channel');
  const metaDuration = document.getElementById('meta-duration');
  const metaLangBadge = document.getElementById('meta-lang-badge');
  const metaCsvStatus = document.getElementById('meta-csv-status');
  const audioDlBtn = document.getElementById('audio-dl-btn');

  const progressContainer = document.getElementById('progress-container');
  const progressDesc = document.getElementById('progress-desc');
  const progressPercent = document.getElementById('progress-percent');
  const progressBarInner = document.getElementById('progress-bar-inner');

  // Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // QA
  const qaForm = document.getElementById('qa-form');
  const qaInput = document.getElementById('qa-input');
  const qaSubmitBtn = document.getElementById('qa-submit-btn');
  const qaChatBox = document.getElementById('qa-chat-box');
  const quickChips = document.querySelectorAll('.quick-chip');

  // Transcript
  const transcriptList = document.getElementById('transcript-list');
  const filterTranscriptInput = document.getElementById('filter-transcript-input');
  const speakerCountTag = document.getElementById('speaker-count-tag');

  // Chapters & History
  const generateChaptersBtn = document.getElementById('generate-chapters-btn');
  const chaptersList = document.getElementById('chapters-list');
  const refreshHistoryBtn = document.getElementById('refresh-history-btn');
  const historyList = document.getElementById('history-list');

  // State
  let ytPlayer = null;
  let isPlayerReady = false;
  let timeUpdaterInterval = null;
  let currentVideoTitle = "YouTube 영상";
  let fullTranscriptContext = "";
  let eventSource = null;

  // 1. YouTube IFrame Player
  window.onYouTubeIframeAPIReady = function() {
    console.log("YouTube IFrame API Ready");
  };

  function initOrLoadPlayer(videoId) {
    playerPlaceholder.classList.add('hidden');
    if (ytPlayer && ytPlayer.loadVideoById) {
      ytPlayer.loadVideoById(videoId);
      ytPlayer.playVideo();
    } else {
      ytPlayer = new YT.Player('youtube-player', {
        videoId: videoId,
        playerVars: { autoplay: 1, controls: 1, modestbranding: 1, rel: 0 },
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange,
        }
      });
    }
  }

  function onPlayerReady() {
    isPlayerReady = true;
    const vol = parseInt(volumeSlider.value, 10);
    ytPlayer.setVolume(vol);
    updateVolumeUI(vol, ytPlayer.isMuted());
    startTimeUpdater();
  }

  function onPlayerStateChange(event) {
    const isPlaying = event.data === YT.PlayerState.PLAYING;
    playText.textContent = isPlaying ? "일시정지" : "재생";
    playIcon.setAttribute('data-lucide', isPlaying ? 'pause' : 'play');
    lucide.createIcons();
  }

  function startTimeUpdater() {
    if (timeUpdaterInterval) clearInterval(timeUpdaterInterval);
    timeUpdaterInterval = setInterval(() => {
      if (ytPlayer && ytPlayer.getCurrentTime && isPlayerReady) {
        currentTimeDisplay.textContent = formatSeconds(ytPlayer.getCurrentTime() || 0);
        totalDurationDisplay.textContent = formatSeconds(ytPlayer.getDuration() || 0);
      }
    }, 500);
  }

  function formatSeconds(sec) {
    const s = Math.floor(sec);
    const hrs = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    return hrs > 0
      ? `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
      : `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  function parseTimeToSeconds(timeStr) {
    const parts = timeStr.trim().split(':').map(Number);
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    return parseFloat(timeStr) || 0;
  }

  // 2. Playback & Volume Control
  playToggleBtn.addEventListener('click', () => {
    if (!ytPlayer || !ytPlayer.getPlayerState) return;
    ytPlayer.getPlayerState() === YT.PlayerState.PLAYING ? ytPlayer.pauseVideo() : ytPlayer.playVideo();
  });

  backwardBtn.addEventListener('click', () => {
    if (ytPlayer && ytPlayer.getCurrentTime) jumpAndPlay(Math.max(0, ytPlayer.getCurrentTime() - 10));
  });

  forwardBtn.addEventListener('click', () => {
    if (ytPlayer && ytPlayer.getCurrentTime) jumpAndPlay(ytPlayer.getCurrentTime() + 10);
  });

  function updateVolumeUI(volume, isMuted) {
    volumeSlider.value = isMuted ? 0 : volume;
    volumeValueText.textContent = `${isMuted ? 0 : volume}%`;
    const iconName = isMuted || volume === 0 ? 'volume-x' : volume < 50 ? 'volume-1' : 'volume-2';
    volumeIcon.setAttribute('data-lucide', iconName);
    lucide.createIcons();
  }

  volumeSlider.addEventListener('input', (e) => {
    const vol = parseInt(e.target.value, 10);
    if (ytPlayer && ytPlayer.setVolume) {
      if (ytPlayer.isMuted()) ytPlayer.unMute();
      ytPlayer.setVolume(vol);
      updateVolumeUI(vol, false);
    }
  });

  muteBtn.addEventListener('click', () => {
    if (!ytPlayer || !ytPlayer.isMuted) return;
    if (ytPlayer.isMuted()) {
      ytPlayer.unMute();
      updateVolumeUI(ytPlayer.getVolume() || 100, false);
    } else {
      ytPlayer.mute();
      updateVolumeUI(0, true);
    }
  });

  // Global Seek & Play
  window.jumpAndPlay = function(seconds) {
    if (ytPlayer && ytPlayer.seekTo) {
      ytPlayer.seekTo(seconds, true);
      ytPlayer.playVideo();
      showToast(`타임스탬프 [${formatSeconds(seconds)}] 이동 및 자동 재생`);
    }
  };

  function showToast(msg) {
    statusOverlayText.textContent = msg;
    statusOverlay.classList.remove('hidden');
    setTimeout(() => statusOverlay.classList.add('hidden'), 2200);
  }

  // 3. Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      tabBtns.forEach(b => {
        b.className = 'tab-btn flex-1 py-2.5 px-3 rounded-xl text-xs font-medium transition flex items-center justify-center gap-1.5 text-slate-400 hover:text-white hover:bg-white/5';
      });
      btn.className = 'tab-btn active flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20';

      tabPanes.forEach(pane => {
        pane.classList.toggle('hidden', pane.id !== `tab-pane-${target}`);
      });

      if (target === 'history') loadHistoryList();
    });
  });

  // 4. URL Validation & Search Execution
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) urlInput.value = text.trim();
    } catch (_) {
      alert("클립보드 접근 권한이 필요합니다.");
    }
  });

  sampleChips.forEach(chip => {
    chip.addEventListener('click', () => {
      urlInput.value = chip.dataset.url;
      searchForm.dispatchEvent(new Event('submit'));
    });
  });

  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;
    startSearchAndOmnilingualTranscription(url);
  });

  function startSearchAndOmnilingualTranscription(url) {
    if (eventSource) eventSource.close();

    // UI Reset
    searchBtn.disabled = true;
    searchBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>분석 중...</span>`;
    lucide.createIcons();

    cachedIndicator.classList.add('hidden');
    metaCsvStatus.classList.add('hidden');
    progressContainer.classList.remove('hidden');
    progressBarInner.style.width = '10%';
    progressPercent.textContent = '10%';
    progressDesc.textContent = 'CSV 캐시 확인 및 영상 정보 수신 중...';

    // Switch to transcript tab immediately so user sees live output
    const transcriptTabBtn = document.querySelector('[data-tab=transcript]');
    if (transcriptTabBtn) transcriptTabBtn.click();

    transcriptList.innerHTML = `
      <div id="transcript-loader" class="p-8 text-center text-slate-400 space-y-3">
        <i data-lucide="loader-2" class="w-8 h-8 animate-spin text-amber-400 mx-auto"></i>
        <div class="text-xs font-medium text-slate-300">오디오 다운로드 및 Gemini 3.5 다국어 음성 분석 중...</div>
        <div class="text-[11px] text-slate-500">실시간으로 감지된 언어와 타임스탬프가 여기에 한 줄씩 표시됩니다.</div>
      </div>
    `;
    lucide.createIcons();

    qaChatBox.innerHTML = '';
    fullTranscriptContext = "";
    qaInput.disabled = true;
    qaSubmitBtn.disabled = true;
    generateChaptersBtn.disabled = true;
    metaLangBadge.textContent = "감지 언어: 분석 중...";

    // Connect SSE Stream
    const sseUrl = `/api/stream?url=${encodeURIComponent(url)}`;
    eventSource = new EventSource(sseUrl);

    eventSource.addEventListener('status', (e) => {
      const data = JSON.parse(e.data);
      progressDesc.textContent = data.message;
      if (data.cached) {
        cachedIndicator.classList.remove('hidden');
        cachedIndicatorText.textContent = data.message;
        metaCsvStatus.classList.remove('hidden');
        metaCsvStatus.textContent = "💾 CSV 캐시 로드";
      }
    });

    eventSource.addEventListener('info', (e) => {
      const info = JSON.parse(e.data);
      currentVideoTitle = info.title;
      metaTitle.textContent = info.title;
      metaChannel.textContent = info.channel;
      metaDuration.textContent = `재생 시간: ${info.duration_str}`;
      if (info.detected_languages) {
        const langStr = Array.isArray(info.detected_languages) ? info.detected_languages.join(', ') : info.detected_languages;
        metaLangBadge.textContent = `감지 언어: ${langStr}`;
      }
      initOrLoadPlayer(info.video_id);
    });

    eventSource.addEventListener('progress', (e) => {
      const p = JSON.parse(e.data);
      if (p.percent !== undefined) {
        const pct = Math.min(50, 10 + p.percent * 0.4);
        progressBarInner.style.width = `${pct}%`;
        progressPercent.textContent = `${Math.round(pct)}%`;
        progressDesc.textContent = `오디오 다운로드 중... (${p.speed || ''})`;
      }
    });

    eventSource.addEventListener('downloaded', (e) => {
      const d = JSON.parse(e.data);
      audioDlBtn.href = d.audio_url;
      audioDlBtn.setAttribute('download', d.file_name);
      audioDlBtn.classList.remove('hidden');
      progressBarInner.style.width = '55%';
      progressPercent.textContent = '55%';
      progressDesc.textContent = 'Gemini 3.5 Transcribe 전방위 모든 언어 동시 감지 중...';
    });

    eventSource.addEventListener('chunk', (e) => {
      const block = JSON.parse(e.data);
      appendTranscriptBlock(block);
      progressBarInner.style.width = '90%';
      progressPercent.textContent = '90%';
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      progressBarInner.style.width = '100%';
      progressPercent.textContent = '100%';

      const langs = Array.isArray(data.detected_languages) ? data.detected_languages.join(', ') : (data.detected_languages || '다국어');
      metaLangBadge.textContent = `감지 언어: ${langs}`;

      if (data.cached) {
        progressDesc.textContent = `💾 CSV 데이터베이스에서 로드 완료 (언어: ${langs})`;
        cachedIndicator.classList.remove('hidden');
        metaCsvStatus.classList.remove('hidden');
        metaCsvStatus.textContent = "💾 CSV 캐시 로드";
      } else {
        progressDesc.textContent = `모든 언어 분석 및 CSV 저장 완료 (언어: ${langs})`;
        metaCsvStatus.classList.remove('hidden');
        metaCsvStatus.textContent = "💾 CSV 저장 완료";
      }

      speakerCountTag.textContent = `화자: ${data.total_speakers}명`;
      fullTranscriptContext = data.full_transcript || "";

      // Append finish banner at bottom of transcript list
      const endBanner = document.createElement('div');
      endBanner.className = 'p-3 mt-3 rounded-xl bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs';
      endBanner.innerHTML = `
        <span class="text-slate-200">🎬 <strong>전사 완료!</strong> (총 ${data.total_speakers || 1}명 화자 | 언어: ${langs})</span>
        <button type="button" class="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition flex items-center gap-1.5 shadow" onclick="document.querySelector('[data-tab=qa]').click()">
          <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
          <span>이 영상 AI에게 질문하기</span>
        </button>
      `;
      transcriptList.appendChild(endBanner);
      lucide.createIcons();

      // Enable QA and Chapters
      qaInput.disabled = false;
      qaSubmitBtn.disabled = false;
      generateChaptersBtn.disabled = false;

      const sourceNote = data.cached ? "기존 CSV에서 불러왔습니다." : "신규 분석 완료 후 CSV에 영구 보관되었습니다.";
      appendChatMessage('ai', `🎬 **${currentVideoTitle}** 전방위 다국어 분석이 완료되었습니다 (${sourceNote})!\n감지된 언어: **${langs}**\n궁금한 점을 질문하거나 특정 대사의 위치를 검색해보세요.`);

      finishPipeline();
    });

    eventSource.addEventListener('error', (e) => {
      let msg = "오류가 발생했습니다.";
      try {
        if (e.data) msg = JSON.parse(e.data).message || msg;
      } catch (_) {}
      progressDesc.textContent = `오류: ${msg}`;
      finishPipeline();
    });
  }

  function finishPipeline() {
    searchBtn.disabled = false;
    searchBtn.innerHTML = `<i data-lucide="search" class="w-4 h-4"></i><span>영상 검색</span>`;
    lucide.createIcons();
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  // 5. Transcript Rendering (with segment language tag)
  function appendTranscriptBlock(block) {
    const loader = document.getElementById('transcript-loader');
    if (loader) loader.remove();

    const item = document.createElement('div');
    item.className = 'transcript-item p-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 transition flex items-start gap-2.5 group cursor-pointer';

    const langInfo = block.lang || { flag: "🌐", label: "다국어" };

    item.innerHTML = `
      <button type="button" class="timestamp-link flex-shrink-0" onclick="jumpAndPlay(${block.start_sec})">
        ▶ ${block.start_str}
      </button>
      <div class="flex-1 space-y-0.5">
        <div class="flex items-center gap-1.5">
          <span class="text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold bg-white/10 text-slate-300">${block.speaker}</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">${langInfo.flag} ${langInfo.label}</span>
        </div>
        <p class="text-slate-200 leading-relaxed text-xs">${block.text}</p>
      </div>
    `;

    item.addEventListener('click', (e) => {
      if (!e.target.closest('button')) jumpAndPlay(block.start_sec);
    });

    transcriptList.appendChild(item);
    transcriptList.scrollTop = transcriptList.scrollHeight;
  }

  filterTranscriptInput.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    transcriptList.querySelectorAll('.transcript-item').forEach(it => {
      it.style.display = it.innerText.toLowerCase().includes(q) ? 'flex' : 'none';
    });
  });

  // 6. Gemini 3.8 Flash Video Q&A & Search
  qaForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = qaInput.value.trim();
    if (!query) return;
    qaInput.value = '';
    sendQAQuery(query);
  });

  quickChips.forEach(chip => {
    chip.addEventListener('click', () => {
      if (!qaInput.disabled) sendQAQuery(chip.dataset.q);
    });
  });

  async function sendQAQuery(query) {
    // Input validation
    if (!query || query.length > 500) {
      alert("질문은 1자 이상 500자 이하로 입력해주세요.");
      return;
    }

    appendChatMessage('user', query);
    const loadingId = appendLoadingBubble();

    try {
      const resp = await fetch('/api/qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          transcript_context: fullTranscriptContext,
          video_title: currentVideoTitle,
        })
      });

      const res = await resp.json();
      removeLoadingBubble(loadingId);

      if (res.success) {
        appendChatMessage('ai', res.answer);
      } else {
        appendChatMessage('ai', `답변 실패: ${res.detail || '오류'}`);
      }
    } catch (err) {
      removeLoadingBubble(loadingId);
      appendChatMessage('ai', `서버 요청 오류: ${err.message}`);
    }
  }

  function appendChatMessage(sender, text) {
    const isUser = sender === 'user';
    const msgDiv = document.createElement('div');
    msgDiv.className = `p-3.5 rounded-xl border leading-relaxed text-xs space-y-1.5 ${
      isUser ? 'bg-amber-500/10 border-amber-500/20 text-amber-200 ml-6' : 'bg-[#181c2b] border-white/5 text-slate-200 mr-4'
    }`;

    const senderHeader = document.createElement('div');
    senderHeader.className = 'flex items-center gap-1.5 font-bold text-[11px]';
    senderHeader.innerHTML = isUser
      ? `<i data-lucide="user" class="w-3.5 h-3.5 text-amber-400"></i> 사용자 질문`
      : `<i data-lucide="sparkles" class="w-3.5 h-3.5 text-amber-400"></i> Gemini 3.8 Flash`;
    msgDiv.appendChild(senderHeader);

    const bodyDiv = document.createElement('div');
    bodyDiv.className = 'whitespace-pre-wrap';
    bodyDiv.innerHTML = formatAIResponseWithTimestamps(text);
    msgDiv.appendChild(bodyDiv);

    qaChatBox.appendChild(msgDiv);
    lucide.createIcons();
    qaChatBox.scrollTop = qaChatBox.scrollHeight;
  }

  function formatAIResponseWithTimestamps(rawText) {
    let sanitized = rawText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    sanitized = sanitized.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return sanitized.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (match, timeStr) => {
      const sec = parseTimeToSeconds(timeStr);
      return `<button type="button" class="timestamp-link" onclick="jumpAndPlay(${sec})">▶ ${timeStr}</button>`;
    });
  }

  function appendLoadingBubble() {
    const id = `loading-${Date.now()}`;
    const div = document.createElement('div');
    div.id = id;
    div.className = 'p-3 rounded-xl bg-[#181c2b] border border-white/5 text-slate-400 text-xs flex items-center gap-2';
    div.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 text-amber-400 animate-spin"></i><span>Gemini 3.8 Flash가 위치와 맥락을 분석 중입니다...</span>`;
    qaChatBox.appendChild(div);
    lucide.createIcons();
    qaChatBox.scrollTop = qaChatBox.scrollHeight;
    return id;
  }

  function removeLoadingBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // 7. Smart Chapters
  generateChaptersBtn.addEventListener('click', async () => {
    chaptersList.innerHTML = `<div class="p-4 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
      <i data-lucide="loader-2" class="w-4 h-4 animate-spin text-amber-400"></i> 챕터 생성 중...
    </div>`;
    lucide.createIcons();

    try {
      const resp = await fetch('/api/chapters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript_context: fullTranscriptContext,
          video_title: currentVideoTitle,
        })
      });
      const data = await resp.json();
      if (data.success && data.chapters && data.chapters.length > 0) {
        chaptersList.innerHTML = '';
        data.chapters.forEach(chap => {
          const sec = chap.seconds !== undefined ? chap.seconds : parseTimeToSeconds(chap.time);
          const card = document.createElement('div');
          card.className = 'p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 transition flex items-start gap-3 cursor-pointer group';
          card.innerHTML = `
            <button type="button" class="timestamp-link flex-shrink-0" onclick="jumpAndPlay(${sec})">▶ ${chap.time}</button>
            <div class="flex-1 space-y-1">
              <div class="font-bold text-white text-xs group-hover:text-amber-400 transition">${chap.title}</div>
              <p class="text-slate-400 text-[11px] leading-relaxed">${chap.summary || ''}</p>
            </div>
          `;
          card.addEventListener('click', (e) => {
            if (!e.target.closest('button')) jumpAndPlay(sec);
          });
          chaptersList.appendChild(card);
        });
      } else {
        chaptersList.innerHTML = `<div class="p-4 text-center text-slate-400 text-xs">챕터 데이터를 생성할 수 없습니다.</div>`;
      }
    } catch (e) {
      chaptersList.innerHTML = `<div class="p-4 text-center text-rose-400 text-xs">오류: ${e.message}</div>`;
    }
  });

  // 8. CSV History
  async function loadHistoryList() {
    historyList.innerHTML = `<div class="p-4 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
      <i data-lucide="loader-2" class="w-4 h-4 animate-spin text-amber-400"></i> CSV 기록 조회 중...
    </div>`;
    lucide.createIcons();

    try {
      const resp = await fetch('/api/csv/list');
      const data = await resp.json();
      if (data.success && data.records && data.records.length > 0) {
        historyList.innerHTML = '';
        data.records.forEach(rec => {
          const item = document.createElement('div');
          item.className = 'p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 transition flex items-center justify-between gap-3 cursor-pointer group';
          item.innerHTML = `
            <div class="flex-1 space-y-1 min-w-0">
              <div class="font-bold text-white text-xs truncate group-hover:text-amber-400 transition">${rec.title || rec.video_id}</div>
              <div class="flex items-center gap-2 text-[10px] text-slate-400">
                <span>${rec.channel || '채널'}</span>
                <span>•</span>
                <span class="font-mono text-amber-400/80">${rec.duration_str || '00:00'}</span>
                <span>•</span>
                <span class="text-indigo-400">${rec.detected_languages || '다국어'}</span>
              </div>
            </div>
            <button type="button" class="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 font-semibold text-[11px] border border-amber-500/30 group-hover:bg-amber-500 group-hover:text-slate-950 transition flex-shrink-0">
              불러오기
            </button>
          `;
          item.addEventListener('click', () => {
            urlInput.value = rec.url || `https://www.youtube.com/watch?v=${rec.video_id}`;
            searchForm.dispatchEvent(new Event('submit'));
            tabBtns[0].click();
          });
          historyList.appendChild(item);
        });
      } else {
        historyList.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs">저장된 전사 기록이 없습니다.</div>`;
      }
    } catch (e) {
      historyList.innerHTML = `<div class="p-4 text-center text-rose-400 text-xs">오류: ${e.message}</div>`;
    }
  }

  if (refreshHistoryBtn) refreshHistoryBtn.addEventListener('click', loadHistoryList);

  const goToQaBtn = document.getElementById('go-to-qa-btn');
  if (goToQaBtn) {
    goToQaBtn.addEventListener('click', () => {
      const qaBtn = document.querySelector('[data-tab=qa]');
      if (qaBtn) qaBtn.click();
    });
  }

  const goToTranscriptBtn = document.getElementById('go-to-transcript-btn');
  if (goToTranscriptBtn) {
    goToTranscriptBtn.addEventListener('click', () => {
      const transBtn = document.querySelector('[data-tab=transcript]');
      if (transBtn) transBtn.click();
    });
  }

});
