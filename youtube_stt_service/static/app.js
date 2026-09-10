// YouTube Audio STT Transcriber Client Script with Multilingual Support
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();

  const form = document.getElementById('transcribe-form');
  const urlInput = document.getElementById('youtube-url');
  const languageSelect = document.getElementById('language-select');
  const startBtn = document.getElementById('start-btn');
  const pasteBtn = document.getElementById('paste-btn');
  const langPills = document.querySelectorAll('.lang-pill');
  const sampleBtns = document.querySelectorAll('.sample-btn');

  const progressSection = document.getElementById('progress-section');
  const currentStatusText = document.getElementById('current-status-text');
  const stepBadge = document.getElementById('step-badge');
  const activeLangBadge = document.getElementById('active-lang-badge');
  const spinnerIcon = document.getElementById('spinner-icon');

  const downloadProgressContainer = document.getElementById('download-progress-container');
  const downloadBar = document.getElementById('download-bar');
  const downloadPercent = document.getElementById('download-percent');
  const downloadSpeed = document.getElementById('download-speed');

  const mediaCard = document.getElementById('media-card');
  const videoThumb = document.getElementById('video-thumb');
  const videoTitle = document.getElementById('video-title');
  const videoChannel = document.getElementById('video-channel');
  const videoDuration = document.getElementById('video-duration');
  const audioSizeBadge = document.getElementById('audio-size-badge');
  const audioPlayer = document.getElementById('audio-player');
  const audioDownloadLink = document.getElementById('audio-download-link');

  const transcriptSection = document.getElementById('transcript-section');
  const transcriptContainer = document.getElementById('transcript-container');
  const transcriptPlaceholder = document.getElementById('transcript-placeholder');
  const speakersCountBadge = document.getElementById('speakers-count-badge');
  const detectedLangPill = document.getElementById('detected-lang-pill');

  const copyBtn = document.getElementById('copy-transcript-btn');
  const exportTxtBtn = document.getElementById('export-txt-btn');
  const exportMdBtn = document.getElementById('export-md-btn');
  const exportSrtBtn = document.getElementById('export-srt-btn');

  let eventSource = null;
  let activeSpeakerBlock = null;
  let currentSpeakerId = null;
  let accumulatedMarkdown = "";
  let accumulatedPlainText = "";
  let accumulatedSrt = "";
  let currentVideoTitle = "YouTube_Transcript";

  // 화자별 색상 테마 정의
  const SPEAKER_COLORS = [
    { border: 'border-indigo-500/40', badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30', label: '화자 1' },
    { border: 'border-emerald-500/40', badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30', label: '화자 2' },
    { border: 'border-amber-500/40', badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30', label: '화자 3' },
    { border: 'border-rose-500/40', badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30', label: '화자 4' },
    { border: 'border-cyan-500/40', badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30', label: '화자 5' },
    { border: 'border-purple-500/40', badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30', label: '화자 6' },
  ];
  const speakerColorMap = new Map();

  function getSpeakerStyle(speakerId) {
    if (!speakerColorMap.has(speakerId)) {
      const idx = speakerColorMap.size % SPEAKER_COLORS.length;
      speakerColorMap.set(speakerId, {
        ...SPEAKER_COLORS[idx],
        label: `화자 ${speakerColorMap.size + 1} (${speakerId})`,
      });
    }
    return speakerColorMap.get(speakerId);
  }

  // 언어 선택 동기화 (드롭다운 <-> 필 버튼)
  function setLanguage(langCode) {
    languageSelect.value = langCode;
    langPills.forEach(pill => {
      if (pill.dataset.lang === langCode) {
        pill.classList.remove('bg-slate-800', 'text-slate-300', 'border-slate-700');
        pill.classList.add('bg-indigo-600', 'text-white', 'border-indigo-500/40');
      } else {
        pill.classList.remove('bg-indigo-600', 'text-white', 'border-indigo-500/40');
        pill.classList.add('bg-slate-800', 'text-slate-300', 'border-slate-700');
      }
    });
  }

  languageSelect.addEventListener('change', () => {
    setLanguage(languageSelect.value);
  });

  langPills.forEach(pill => {
    pill.addEventListener('click', () => {
      setLanguage(pill.dataset.lang);
    });
  });

  // 클립보드 붙여넣기
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
      }
    } catch (e) {
      alert('클립보드 읽기 권한이 허용되지 않았습니다.');
    }
  });

  // 샘플 URL 버튼 클릭
  sampleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      urlInput.value = btn.dataset.url;
      if (btn.dataset.lang) {
        setLanguage(btn.dataset.lang);
      }
    });
  });

  // 스텝 인디케이터 상태 업데이트
  function updateStep(stepIndex, state, descText) {
    const stepEl = document.getElementById(`step-${stepIndex}`);
    if (!stepEl) return;

    const numEl = stepEl.querySelector('.step-num');
    const descEl = stepEl.querySelector('.step-desc');

    if (descText) descEl.textContent = descText;

    stepEl.classList.remove('border-indigo-500', 'bg-indigo-950/40', 'border-emerald-500', 'bg-emerald-950/40');
    numEl.classList.remove('bg-indigo-600', 'text-white', 'bg-emerald-600', 'text-white');

    if (state === 'active') {
      stepEl.classList.add('border-indigo-500', 'bg-indigo-950/40');
      numEl.classList.add('bg-indigo-600', 'text-white');
    } else if (state === 'done') {
      stepEl.classList.add('border-emerald-500/60', 'bg-emerald-950/30');
      numEl.classList.add('bg-emerald-600', 'text-white');
      numEl.innerHTML = '✓';
    }
  }

  // 폼 제출 (전사 시작)
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    startTranscription(url, languageSelect.value);
  });

  function startTranscription(url, lang) {
    if (eventSource) {
      eventSource.close();
    }

    // UI 초기화
    startBtn.disabled = true;
    startBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>진행 중...</span>`;
    lucide.createIcons();

    progressSection.classList.remove('hidden');
    mediaCard.classList.add('hidden');
    transcriptSection.classList.remove('hidden');

    transcriptContainer.innerHTML = '';
    activeSpeakerBlock = null;
    currentSpeakerId = null;
    speakerColorMap.clear();
    accumulatedMarkdown = "";
    accumulatedPlainText = "";
    accumulatedSrt = "";

    downloadProgressContainer.classList.add('hidden');
    downloadBar.style.width = '0%';
    downloadPercent.textContent = '0%';

    const selectedOption = languageSelect.options[languageSelect.selectedIndex];
    activeLangBadge.textContent = `언어: ${selectedOption ? selectedOption.text : lang}`;
    detectedLangPill.textContent = `언어: ${selectedOption ? selectedOption.text : lang}`;

    updateStep(1, 'active', '영상 정보 조회 중...');
    updateStep(2, 'idle', '대기 중');
    updateStep(3, 'idle', '대기 중');
    stepBadge.textContent = '조회 중';
    currentStatusText.textContent = 'YouTube 영상 정보 및 메타데이터를 확인하고 있습니다...';

    // SSE 스트림 연결
    const sseUrl = `/api/stream?url=${encodeURIComponent(url)}&lang=${encodeURIComponent(lang)}`;
    eventSource = new EventSource(sseUrl);

    eventSource.addEventListener('status', (e) => {
      const data = JSON.parse(e.data);
      currentStatusText.textContent = data.message;
      if (data.step === 'info') {
        updateStep(1, 'active', '정보 확인 중...');
        stepBadge.textContent = '영상 확인';
      } else if (data.step === 'downloading') {
        updateStep(1, 'done', '완료');
        updateStep(2, 'active', '다운로드 진행 중...');
        downloadProgressContainer.classList.remove('hidden');
        stepBadge.textContent = '다운로드';
      } else if (data.step === 'transcribing') {
        updateStep(2, 'done', '다운로드 완료');
        updateStep(3, 'active', '음성 전사 진행 중...');
        downloadProgressContainer.classList.add('hidden');
        stepBadge.textContent = 'Gemini 전사 중';
      }
    });

    eventSource.addEventListener('info', (e) => {
      const info = JSON.parse(e.data);
      currentVideoTitle = info.title || "YouTube_Transcript";
      videoTitle.textContent = info.title;
      videoChannel.textContent = info.channel;
      videoDuration.textContent = info.duration_str;
      if (info.thumbnail) {
        videoThumb.src = info.thumbnail;
      }
      if (info.suggested_lang && languageSelect.value === 'auto') {
        detectedLangPill.textContent = `언어 추론: ${info.suggested_lang.toUpperCase()}`;
      }
      mediaCard.classList.remove('hidden');
    });

    eventSource.addEventListener('progress', (e) => {
      const p = JSON.parse(e.data);
      if (p.percent !== undefined) {
        downloadBar.style.width = `${p.percent}%`;
        downloadPercent.textContent = `${p.percent}%`;
        downloadSpeed.textContent = `다운로드 속도: ${p.speed || '다운로드 중...'}`;
      }
    });

    eventSource.addEventListener('downloaded', (e) => {
      const d = JSON.parse(e.data);
      audioSizeBadge.textContent = `${d.file_size_mb} MB (${d.mime_type})`;
      audioPlayer.src = d.audio_url;
      audioDownloadLink.href = d.audio_url;
      audioDownloadLink.setAttribute('download', d.file_name);
      mediaCard.classList.remove('hidden');
      updateStep(2, 'done', `${d.file_size_mb} MB 완료`);
    });

    eventSource.addEventListener('chunk', (e) => {
      const data = JSON.parse(e.data);
      appendTranscriptChunk(data);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      updateStep(3, 'done', '전사 완료');
      stepBadge.textContent = '완료';
      stepBadge.className = 'text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30';
      spinnerIcon.classList.remove('animate-spin');
      spinnerIcon.setAttribute('data-lucide', 'check-circle');
      currentStatusText.textContent = `전사 완료 (총 ${data.total_speakers}명 감지됨)`;
      speakersCountBadge.textContent = `화자: ${data.total_speakers}명`;

      if (data.detected_language) {
        detectedLangPill.textContent = `언어: ${data.detected_language}`;
      }

      accumulatedMarkdown = data.markdown || "";
      accumulatedPlainText = data.plain_text || "";
      accumulatedSrt = data.srt || "";

      lucide.createIcons();
      finishJob();
    });

    eventSource.addEventListener('error', (e) => {
      let errMsg = "전사 파이프라인 처리 중 오류가 발생했습니다.";
      try {
        if (e.data) {
          const errData = JSON.parse(e.data);
          errMsg = errData.message || errMsg;
        }
      } catch (_) {}

      stepBadge.textContent = '오류 발생';
      stepBadge.className = 'text-xs px-2.5 py-1 rounded-full bg-rose-500/20 text-rose-400 font-semibold border border-rose-500/30';
      currentStatusText.textContent = errMsg;
      spinnerIcon.classList.remove('animate-spin');

      finishJob();
    });
  }

  function finishJob() {
    startBtn.disabled = false;
    startBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>전사 시작</span>`;
    lucide.createIcons();
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  // 실시간 텍스트 청크 추가
  function appendTranscriptChunk(chunkData) {
    const speakerId = chunkData.speaker || "spk:0";
    const text = chunkData.text || "";

    if (transcriptPlaceholder) {
      transcriptPlaceholder.remove();
    }

    const style = getSpeakerStyle(speakerId);

    // 화자가 바뀌었거나 첫 블록인 경우 새 카드 생성
    if (!activeSpeakerBlock || currentSpeakerId !== speakerId) {
      currentSpeakerId = speakerId;

      activeSpeakerBlock = document.createElement('div');
      activeSpeakerBlock.className = `p-4 rounded-xl border bg-slate-800/80 ${style.border} space-y-2 transition shadow-sm`;

      const header = document.createElement('div');
      header.className = 'flex items-center justify-between text-xs';

      const badge = document.createElement('span');
      badge.className = `px-2.5 py-0.5 rounded-full font-semibold border ${style.badge}`;
      badge.textContent = style.label;
      header.appendChild(badge);

      activeSpeakerBlock.appendChild(header);

      const contentDiv = document.createElement('div');
      contentDiv.className = 'text-sm text-slate-200 leading-relaxed font-sans transcript-content whitespace-pre-wrap';
      activeSpeakerBlock.appendChild(contentDiv);

      transcriptContainer.appendChild(activeSpeakerBlock);
    }

    const contentDiv = activeSpeakerBlock.querySelector('.transcript-content');
    contentDiv.appendChild(document.createTextNode(text));
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
  }

  // 내보내기 헬퍼
  function downloadBlob(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function getCleanFileName(ext) {
    const safeTitle = currentVideoTitle.replace(/[\\/*?:"<>|]/g, '').substring(0, 40).trim();
    return `${safeTitle || 'transcript'}.${ext}`;
  }

  // 복사 버튼
  copyBtn.addEventListener('click', async () => {
    const text = accumulatedPlainText || transcriptContainer.innerText;
    if (!text) {
      alert('복사할 전사 결과가 없습니다.');
      return;
    }
    await navigator.clipboard.writeText(text);
    const origHtml = copyBtn.innerHTML;
    copyBtn.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i> 복사됨!`;
    lucide.createIcons();
    setTimeout(() => {
      copyBtn.innerHTML = origHtml;
      lucide.createIcons();
    }, 2000);
  });

  // TXT 다운로드
  exportTxtBtn.addEventListener('click', () => {
    const text = accumulatedPlainText || transcriptContainer.innerText;
    if (!text) return alert('전사 결과가 없습니다.');
    downloadBlob(text, getCleanFileName('txt'), 'text/plain;charset=utf-8');
  });

  // Markdown 다운로드
  exportMdBtn.addEventListener('click', () => {
    const text = accumulatedMarkdown || `# ${currentVideoTitle}\n\n` + (accumulatedPlainText || transcriptContainer.innerText);
    if (!text) return alert('전사 결과가 없습니다.');
    downloadBlob(text, getCleanFileName('md'), 'text/markdown;charset=utf-8');
  });

  // SRT 자막 다운로드
  exportSrtBtn.addEventListener('click', () => {
    if (!accumulatedSrt) return alert('자막 데이터가 없거나 전사 중입니다.');
    downloadBlob(accumulatedSrt, getCleanFileName('srt'), 'text/plain;charset=utf-8');
  });

});
