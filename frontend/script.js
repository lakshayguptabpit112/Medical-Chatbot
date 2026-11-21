let history = [];

//ALL CHATS ARE STORED IN THIS
let chats = [];

//ALL CHATS LOADING ARE IN THIS SET 
const loadingChats = new Set();


// CHat ID WE ARE WATCHING RN IF NO CHAT THEN IT WOULD BE WELCOME TAB THANKS TO UPDATE UI STATE
let currentChatId = null;


//Aborts Generation Request 
let currentController = null;

// --- UPGRADED DRAFT SYSTEM (Text + Attachments) ---
const chatDrafts = {}; 


// THIS IS SOME RANDOM DOM THINGY JO YAHA BAAD MEI THEEK KARUNGA
const container = document.querySelector(".chat-history");
const hamburgerBtn = document.getElementById("hamburger-btn");
const sidebar = document.querySelector(".sidebar");
const welcomeScreen = document.getElementById("welcome-screen");
const chatHistory = document.getElementById("chat-history");
const sendBtn = document.querySelector("#send-btn");
const stopBtn = document.querySelector("#stop-btn");
const chatInput = document.querySelector("#chat-input");
const wordCounter = document.getElementById("word-counter");
const loginOverlay = document.getElementById("login-overlay");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");

const loginView = document.getElementById("login-view");
const registerView = document.getElementById("register-view");

const chatLoading = document.getElementById("chat-loading");


// --- Attachment Elements & State ---
const attachBtn = document.getElementById("attach-btn");
const imageInput = document.getElementById("image-input");
const imagePreviewContainer = document.getElementById("image-preview-container");
const imagePreviewImg = document.getElementById("image-preview-img");
const pdfPreviewIcon = document.getElementById("pdf-preview-icon");
const previewFilename = document.getElementById("preview-filename");
const previewFilesize = document.getElementById("preview-filesize");
const removeImageBtn = document.getElementById("remove-image-btn");

let selectedAttachmentFile = null;      // Holds the raw File object for FormData upload
let selectedAttachmentDataUrl = null;   // Holds the base64 or blob URL for instant preview

// --- Voice Overview (TTS) State ---
let activeAudio = null;
let activeAudioUrl = null;
let activePlayingBtn = null;
let activeMessageContainer = null;
let activeAudioMsgId = null;
let activeAudioState = "idle"; // 'idle' | 'translating' | 'buffering' | 'playing' | 'paused'
const translationPollers = new Map(); // messageId -> intervalId


// 1. Select the element
const profileNameElement = document.querySelector('.sidebar-profile-name');



const showRegisterButton =
    document.getElementById("show-register");

const showLoginButton =
    document.getElementById("show-login");

const registerForm =
    document.getElementById("register-form");

const registerError =
    document.getElementById("register-error");

const registerSuccess =
    document.getElementById("register-success");



function showChatLoading() {
    chatLoading.hidden = false;
    chatInput.disabled = true;
}

function hideChatLoading() {
    chatLoading.hidden = true;
    chatInput.disabled = false;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

sendBtn.onclick = sendMessage;

// Click paperclip -> trigger hidden file picker
if (attachBtn) {
    attachBtn.onclick = () => imageInput.click();
}
// File selected from file picker
if (imageInput) {
    imageInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) handleSelectedFile(file);
    };
}
// Click [X] -> clear attachment
if (removeImageBtn) {
    removeImageBtn.onclick = clearAttachment;
}

//LoadEverything AT REFRESH

function startApp() {
    closeSidebarOnMobile();
    initializeApp();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startApp);
} else {
    startApp();
}

//helping Functions:

// Function to handle the Reuse Prompt button!
function copyToInput(text) {
    // Block if the chat is currently generating!
    if (loadingChats.has(currentChatId)) return;

    chatInput.value = text;

    chatInput.focus(); // Automatically put the user's cursor in the box!
    
    // Trigger the auto-resize logic so the box expands to fit the paragraph
    
    chatInput.dispatchEvent(new Event('input')); 
}



function copyPromptFromMsg(btn) {
    const msgBubble = btn.closest(".message") || btn.closest(".chat-message");
    if (!msgBubble) return;
    const textElem = msgBubble.querySelector(".msg-text") || msgBubble.querySelector(".message-content");
    if (!textElem) return;
    const rawText = textElem.innerText || textElem.textContent || "";
    copyToInput(rawText);
}


function OnVoted(btn){

    const cardEl = btn.closest(".clarification-card");
    if (cardEl) {
        cardEl.querySelectorAll("button").forEach(b => b.disabled = true);
    }
    const msgIdx = parseInt(btn.getAttribute("data-msg-idx"), 10);
    const qIdx = parseInt(btn.getAttribute("data-q-idx"), 10);
    const opt = btn.getAttribute("data-opt") || "";
    handleClarificationAnswer(msgIdx, qIdx, opt);
}
window.onClarificationChipClick = OnVoted;

function handleClarificationAnswer(msgIndex, qIndex, selectedOption) {
    const msg = history[msgIndex];
    if (!msg || !msg.clarification || !msg.clarification.questions || !msg.clarification.questions[qIndex]) return;
    
    if (!msg.clarification.userAnswers) {
        msg.clarification.userAnswers = [];
    }   
    const currentQ = msg.clarification.questions[qIndex];

    if (currentQ) {
        msg.clarification.userAnswers.push({ 
            question: currentQ.question, 
            selected_option: selectedOption 
        });
    }
    const totalQ = msg.clarification.questions.length;
    const cardEl = document.getElementById(`clarification-card-${msgIndex}`);
    
    // Check: Are there more questions?
    if (qIndex + 1 < totalQ) {
        // More questions remaining -> slide to next question!
        if (cardEl) cardEl.classList.add("clarification-fading-out");
        setTimeout(() => {
            msg.clarification.currentIndex = qIndex + 1;
            msg.clarification._stepIn = true;
            UpdateChatHistory();
        }, 180);
    } else {
        finishClarification(msgIndex);
    }
}

function skipSingleClarification(msgIndex, qIndex) {    
    const msg = history[msgIndex];
    if (!msg || !msg.clarification || !msg.clarification.questions || !msg.clarification.questions[qIndex]) return;

    const totalQ = msg.clarification.questions.length;
    const cardEl = document.getElementById(`clarification-card-${msgIndex}`);
    
    if (qIndex + 1 < totalQ) {
        if (cardEl) cardEl.classList.add("clarification-fading-out");
        setTimeout(() => {
            msg.clarification.currentIndex = qIndex + 1;
            msg.clarification._stepIn = true;
            UpdateChatHistory();
        }, 180);
    } else {
        finishClarification(msgIndex);
    }
}

function hasmeaningfulAnswers(answers) {
    // If no answers exist, return false
    if (!answers || answers.length === 0) return false;
    for (let i = 0; i < answers.length; i++) {
        const text = answers[i].selected_option;
        
        // Safety check: skip if blank
        if (!text) continue;
        const option = text.toLowerCase();
        // Check if the answer is one of the vague non-answers:
        const isVague = option.includes("not sure") ||
                        option.includes("skip") ||
                        option.includes("don't know") ||
                        option.includes("none of these");
        // If it is NOT vague, we found a real medical answer!
        if (!isVague) {
            return true;
        }
    }
    return false;
}
function skipAllClarifications(msgIndex) {
    const msg = history[msgIndex];
    if (!msg || !msg.clarification) return;
    revealFinalConsultation(msgIndex, msg.content);
}
function getLoadingOnQuestionCard() {
    return `
        <div class="clarification-refining-box">
            <div class="clarification-refining-spinner"></div>
            <div class="clarification-refining-text">
                <span class="refine-title">Refining clinical consultation...</span>
                <span class="refine-sub">Cross-referencing confirmed details with medical literature.</span>
            </div>
        </div>
    `;
}

async function finishClarification(msgIndex) {

    const msg = history[msgIndex];
    if(!msg || !msg.clarification) return;
    const answers  = msg.clarification.userAnswers || [];
    const hasMeaningfulAnswers = hasmeaningfulAnswers(answers);
  
    if (!hasMeaningfulAnswers) {
        revealFinalConsultation(msgIndex, msg.content);
        return;
    }
    const cardEl = document.getElementById(`clarification-card-${msgIndex}`);
    if (cardEl) {
    cardEl.querySelectorAll("button").forEach(b => b.disabled = true);
    cardEl.innerHTML = getLoadingOnQuestionCard(); // Clean, 1-liner! ✨  
    }
    // 3. Ask Python to rewrite the advice with the confirmed details
    try {
        const response = await fetch("/message/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message_id: msg.id,
                chat_id: currentChatId,
                clarifications: answers
            })
        });
        const data = await response.json();
        const refined = (data && data.refined_content) ? data.refined_content : msg.content;
        revealFinalConsultation(msgIndex, refined);
    } catch (err) {
        // Fallback: If network glitch, still show the original consultation!
        console.error("Clinical refinement failed:", err);
        revealFinalConsultation(msgIndex, msg.content);
    }
}

function revealFinalConsultation(msgIndex, finalContent = null) {
    const msg = history[msgIndex];
    if (!msg) return;

    // 1. Mark clarification as resolved in memory
    if (msg.clarification) {
        msg.clarification.resolved = true;
        msg.clarification.isRefining = false;
    }
    // If Python returned a newly refined consultation, update msg.content
    if (finalContent) {
        msg.content = finalContent;
    }

    const cardEl = document.getElementById(`clarification-card-${msgIndex}`);
    const textEl = document.getElementById(`msg-text-${msgIndex}`);
    const sourcesEl = document.getElementById(`msg-sources-${msgIndex}`);
    const footerEl = document.getElementById(`msg-footer-${msgIndex}`);

    // 2. Smoothly dissolve and delete the question card
    if (cardEl) {
        cardEl.classList.add("clarification-fading-out");
        setTimeout(() => {
            if (cardEl.parentNode) cardEl.remove();
        }, 300);
    }

    // 3. Crossfade the message text into the full consultation Markdown!
    if (textEl) {
        textEl.classList.add("msg-text-fade-out");
        setTimeout(() => {
            textEl.innerHTML = renderMarkdown(msg.content);
            textEl.classList.remove("msg-text-fade-out");
            textEl.classList.add("answer-reveal-fade");
        }, 200);
    }

    // 4. Reveal sources & footer actions
    if (sourcesEl) {
        sourcesEl.style.display = "flex";
        sourcesEl.classList.add("answer-reveal-fade");
    }
    if (footerEl) {
        footerEl.style.display = "flex";
        footerEl.classList.add("answer-reveal-fade");
    }

    // 5. Scroll chat to bottom so the patient can read the answer
    const chatContainer = document.querySelector(".chat-history");
    if (chatContainer) {
        setTimeout(() => {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }, 250);
    }
}

// Helper: Renders footer
function renderMessageFooter(msgIndex, time, actionBtns, ShowFooter) {

    const hiddenStyle = !ShowFooter ? ' style="display: none;"' : '';
    return `
        <div class="msg-footer" id="msg-footer-${msgIndex}"${hiddenStyle}>
            <div class="msg-actions">${actionBtns}</div>
            <div class="timestamp">${time}</div>
        </div>
    `;
}

// Helper: Renders the clarification question card with OnVoted chips
function renderClarificationCard(msgIndex, clar) {
    if (clar.isRefining) {
        return `
            <div class="clarification-card" id="clarification-card-${msgIndex}">
                ${getLoadingOnQuestionCard()}
            </div>
        `;
    }

    const currentQ = clar.questions[clar.currentIndex || 0];
    const qNum = (clar.currentIndex || 0) + 1;
    const totalQ = clar.questions.length;

    const chipsHtml = (currentQ.options || []).map(opt => `
        <button type="button" class="clarification-chip-btn" data-msg-idx="${msgIndex}" data-q-idx="${clar.currentIndex || 0}" data-opt="${escapeHtml(opt)}" onclick="OnVoted(this)">
            <span class="chip-dot"></span>
            <span>${escapeHtml(opt)}</span>
        </button>
    `).join("");

    const stepInClass = clar._stepIn ? " clarification-step-in" : "";
    clar._stepIn = false;

    return `
    <div class="clarification-card${stepInClass}" id="clarification-card-${msgIndex}">
        <div class="clarification-card-header">
            <span class="clarification-badge">
                <i class="fa-solid fa-stethoscope"></i> Verification needed (${qNum}/${totalQ})
            </span>
            <button type="button" class="clarification-skip-text-btn" onclick="skipAllClarifications(${msgIndex})">
                Skip to consultation <i class="fa-solid fa-chevron-right"></i>
            </button>
        </div>
        <div class="clarification-question-text">${escapeHtml(currentQ.question)}</div>
        <div class="clarification-chips-wrapper">${chipsHtml}</div>
    </div>`;
}

// --- Doctor Voice Overview (TTS & Audio Controller) ---

function getPreferredAudioLang() {
    return localStorage.getItem("voice_overview_lang") || "hi";
}

function setPreferredAudioLang(lang) {
    localStorage.setItem("voice_overview_lang", lang);
    document.querySelectorAll(".voice-lang-badge").forEach(badge => {
        badge.textContent = lang.toUpperCase();
    });
}

function updateRestartButton(control, msgId, show) {
    if (!control) return;
    let restartBtn = control.querySelector(".voice-restart-btn");
    if (show) {
        if (!restartBtn) {
            restartBtn = document.createElement("button");
            restartBtn.className = "msg-action-btn voice-restart-btn";
            restartBtn.title = "Restart from beginning";
            restartBtn.innerHTML = `<i class="fa-solid fa-rotate-left"></i>`;
            restartBtn.onclick = (e) => {
                e.stopPropagation();
                restartAudioOverview(msgId);
            };
            control.appendChild(restartBtn);
        }
    } else {
        if (restartBtn) {
            restartBtn.remove();
        }
    }
}

function stopCurrentAudio(resetState = true) {
    if (activeAudio) {
        activeAudio.pause();
        activeAudio.onended = null;
        activeAudio.onerror = null;
        activeAudio = null;
    }
    if (activeAudioUrl) {
        URL.revokeObjectURL(activeAudioUrl);
        activeAudioUrl = null;
    }
    if (activePlayingBtn) {
        const lang = getPreferredAudioLang();
        const targetMsg = history.find(m => m.id === activeAudioMsgId);
        const hasTranslation = Boolean(targetMsg && targetMsg.translations && (targetMsg.translations[lang] || targetMsg.translations.hi || targetMsg.translations.en));
        
        activePlayingBtn.classList.remove("playing", "paused", "buffering", "translating");
        if (hasTranslation) {
            activePlayingBtn.className = "msg-action-btn voice-play-btn";
            activePlayingBtn.innerHTML = `<i class="fa-solid fa-headphones"></i> <span class="voice-label">Voice Overview</span>`;
        } else {
            activePlayingBtn.className = "msg-action-btn voice-play-btn translating";
            activePlayingBtn.innerHTML = `<i class="fa-solid fa-language fa-fade"></i> <span class="voice-label">Translating...</span>`;
        }
        
        const control = activePlayingBtn.closest(".voice-overview-control");
        if (control) {
            updateRestartButton(control, activeAudioMsgId, false);
        }
        activePlayingBtn = null;
    }
    if (activeMessageContainer) {
        activeMessageContainer.classList.remove("audio-playing");
        activeMessageContainer = null;
    }
    if (resetState) {
        activeAudioMsgId = null;
        activeAudioState = "idle";
    }
}

function restartAudioOverview(msgId) {
    if (activeAudio && activeAudioMsgId === msgId) {
        activeAudio.currentTime = 0;
        activeAudio.play();
        activeAudioState = "playing";
        if (activePlayingBtn) {
            activePlayingBtn.className = "msg-action-btn voice-play-btn playing";
            activePlayingBtn.innerHTML = `<i class="fa-solid fa-pause"></i> <span class="voice-label">Pause</span>`;
        }
    }
}

function ensureTranslationPoller(msgId) {
    if (!msgId || translationPollers.has(msgId)) return;

    let attempts = 0;
    const maxAttempts = 15; // 15 * 1.5s = ~22 seconds max

    const intervalId = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            clearInterval(intervalId);
            translationPollers.delete(msgId);
            return;
        }

        try {
            const res = await fetch(`/message/translations/${msgId}`);
            if (!res.ok) return;
            const data = await res.json();

            if (data.is_ready) {
                clearInterval(intervalId);
                translationPollers.delete(msgId);

                const targetMsg = history.find(m => m.id === msgId);
                if (targetMsg) {
                    targetMsg.translations = data.translations;
                }

                if (activeAudioMsgId === msgId && activeAudioState === "translating") {
                    startStreamingAudio(msgId);
                } else {
                    const control = document.querySelector(`.voice-overview-control[data-msg-id="${msgId}"]`);
                    if (control) {
                        const playBtn = control.querySelector(".voice-play-btn");
                        if (playBtn && activeAudioMsgId !== msgId) {
                            playBtn.className = "msg-action-btn voice-play-btn";
                            playBtn.innerHTML = `<i class="fa-solid fa-headphones"></i> <span class="voice-label">Voice Overview</span>`;
                        }
                    }
                }
            }
        } catch (e) {
            console.warn(`Translation poller notice for msg ${msgId}:`, e);
        }
    }, 1500);

    translationPollers.set(msgId, intervalId);
}

async function startStreamingAudio(msgId) {
    const control = document.querySelector(`.voice-overview-control[data-msg-id="${msgId}"]`);
    const btn = control ? control.querySelector(".voice-play-btn") : activePlayingBtn;
    const parentMsg = control ? control.closest(".message") : activeMessageContainer;

    if (!btn) return;

    activeAudioMsgId = msgId;
    activePlayingBtn = btn;
    activeMessageContainer = parentMsg;
    activeAudioState = "buffering";

    if (parentMsg) parentMsg.classList.add("audio-playing");
    btn.className = "msg-action-btn voice-play-btn buffering";
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span class="voice-label">Loading Audio...</span>`;
    updateRestartButton(control, msgId, false);

    const lang = getPreferredAudioLang();
    const rawText = parentMsg ? (parentMsg.querySelector(".msg-text")?.innerText || "") : "";

    try {
        const payload = {
            message_id: msgId,
            text: rawText,
            target_lang: lang
        };

        const response = await fetch("/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const blob = await response.blob();

        if (activeAudioMsgId !== msgId || activeAudioState !== "buffering") {
            return;
        }

        if (activeAudioUrl) {
            URL.revokeObjectURL(activeAudioUrl);
        }
        activeAudioUrl = URL.createObjectURL(blob);
        const audio = new Audio(activeAudioUrl);

        activeAudio = audio;
        activeAudioState = "playing";

        btn.className = "msg-action-btn voice-play-btn playing";
        btn.innerHTML = `<i class="fa-solid fa-pause"></i> <span class="voice-label">Pause</span>`;
        updateRestartButton(control, msgId, true);

        audio.onended = () => {
            stopCurrentAudio();
        };

        audio.onerror = (e) => {
            console.error("Audio playback error:", e);
            stopCurrentAudio();
        };

        await audio.play();
    } catch (err) {
        console.error("Failed to stream audio overview:", err);
        stopCurrentAudio();
    }
}

async function toggleAudioOverview(btn, msgId) {
    const parsedId = (msgId && msgId !== "null" && msgId !== "undefined" && !isNaN(parseInt(msgId))) ? parseInt(msgId) : null;
    const control = btn.closest(".voice-overview-control");
    const parentMsg = btn.closest(".message");

    if (activeAudioMsgId === parsedId && parsedId !== null) {
        if (activeAudioState === "playing" && activeAudio) {
            activeAudio.pause();
            activeAudioState = "paused";
            btn.className = "msg-action-btn voice-play-btn paused";
            btn.innerHTML = `<i class="fa-solid fa-play"></i> <span class="voice-label">Resume</span>`;
            updateRestartButton(control, parsedId, true);
            return;
        } else if (activeAudioState === "paused" && activeAudio) {
            activeAudio.play();
            activeAudioState = "playing";
            btn.className = "msg-action-btn voice-play-btn playing";
            btn.innerHTML = `<i class="fa-solid fa-pause"></i> <span class="voice-label">Pause</span>`;
            updateRestartButton(control, parsedId, true);
            return;
        } else if (activeAudioState === "translating" || activeAudioState === "buffering") {
            stopCurrentAudio();
            return;
        }
    }

    stopCurrentAudio();

    const lang = getPreferredAudioLang();
    const targetMsg = history.find(m => m.id === parsedId);
    const hasTranslation = Boolean(targetMsg && targetMsg.translations && (targetMsg.translations[lang] || targetMsg.translations.hi || targetMsg.translations.en));

    activeAudioMsgId = parsedId;
    activePlayingBtn = btn;
    activeMessageContainer = parentMsg;
    if (parentMsg) parentMsg.classList.add("audio-playing");

    if (hasTranslation) {
        await startStreamingAudio(parsedId);
    } else {
        activeAudioState = "translating";
        btn.className = "msg-action-btn voice-play-btn translating";
        btn.innerHTML = `<i class="fa-solid fa-language fa-fade"></i> <span class="voice-label">Translating...</span>`;
        updateRestartButton(control, parsedId, false);
        ensureTranslationPoller(parsedId);
    }
}

function toggleOverviewLanguage(event, toggleBtn, msgId) {
    event.stopPropagation();
    const currentLang = getPreferredAudioLang();
    const newLang = currentLang === "hi" ? "en" : "hi";
    setPreferredAudioLang(newLang);

    if (activeAudioMsgId === msgId) {
        stopCurrentAudio();
        const control = toggleBtn.closest(".voice-overview-control");
        const playBtn = control ? control.querySelector(".voice-play-btn") : null;
        if (playBtn) {
            toggleAudioOverview(playBtn, msgId);
        }
    }
}

// Helper: Renders Doctor Voice Overview audio button + language switcher for AI message
function renderVoiceControl(msg) {
    const msgId = msg.id;
    const msgTranslations = msg.translations || {};
    const currentLang = getPreferredAudioLang();
    const langBadge = currentLang.toUpperCase();
    const hasTranslation = Boolean(msgTranslations[currentLang] || msgTranslations.hi || msgTranslations.en);

    let btnClass = "msg-action-btn voice-play-btn";
    let btnContent = `<i class="fa-solid fa-headphones"></i> <span class="voice-label">Voice Overview</span>`;
    let showRestart = false;

    if (activeAudioMsgId === msgId) {
        if (activeAudioState === "playing") {
            btnClass += " playing";
            btnContent = `<i class="fa-solid fa-pause"></i> <span class="voice-label">Pause</span>`;
            showRestart = true;
        } else if (activeAudioState === "paused") {
            btnClass += " paused";
            btnContent = `<i class="fa-solid fa-play"></i> <span class="voice-label">Resume</span>`;
            showRestart = true;
        } else if (activeAudioState === "buffering") {
            btnClass += " buffering";
            btnContent = `<i class="fa-solid fa-circle-notch fa-spin"></i> <span class="voice-label">Loading Audio...</span>`;
        } else if (activeAudioState === "translating") {
            btnClass += " translating";
            btnContent = `<i class="fa-solid fa-language fa-fade"></i> <span class="voice-label">Translating...</span>`;
        }
    } else if (!hasTranslation && msgId) {
        btnClass += " translating";
        btnContent = `<i class="fa-solid fa-language fa-fade"></i> <span class="voice-label">Translating...</span>`;
        ensureTranslationPoller(msgId);
    }

    const restartHtml = showRestart
        ? `<button class="msg-action-btn voice-restart-btn" onclick="restartAudioOverview(${msgId})" title="Restart from beginning"><i class="fa-solid fa-rotate-left"></i></button>`
        : "";

    return `
        <div class="voice-overview-control" data-msg-id="${msgId || ''}">
            <button class="${btnClass}" onclick="toggleAudioOverview(this, ${msgId})" title="Listen to Doctor's Voice Overview">
                ${btnContent}
            </button>
            ${restartHtml}
            <button class="msg-action-btn voice-lang-toggle" onclick="toggleOverviewLanguage(event, this, ${msgId})" title="Switch language (Hindi / English)">
                <span class="voice-lang-badge">${langBadge}</span>
            </button>
        </div>
    `;
}


function handleSelectedFile(file) {
    // 10MB limit check
    if (file.size > 10 * 1024 * 1024) {
        alert("File size exceeds 10 MB limit.");
        clearAttachment();
        return;
    }
    selectedAttachmentFile = file;
    if (previewFilename) previewFilename.textContent = file.name;
    if (previewFilesize) previewFilesize.textContent = formatFileSize(file.size);
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (isPdf) {
        if (imagePreviewImg) imagePreviewImg.style.display = "none";
        if (pdfPreviewIcon) pdfPreviewIcon.style.display = "block";
        selectedAttachmentDataUrl = URL.createObjectURL(file);
    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            selectedAttachmentDataUrl = e.target.result;
            if (imagePreviewImg) {
                imagePreviewImg.src = selectedAttachmentDataUrl;
                imagePreviewImg.style.display = "block";
            }
            if (pdfPreviewIcon) pdfPreviewIcon.style.display = "none";
        };
        reader.readAsDataURL(file);
    }
    if (imagePreviewContainer) imagePreviewContainer.style.display = "flex";
    if (attachBtn) attachBtn.classList.add("has-file");
}

// Helper to convert saved base64 back into a real File object
function dataURLtoFile(dataurl, filename, mimeType) {
    if (!dataurl || !dataurl.startsWith("data:")) return null;
    try {
        const arr = dataurl.split(',');
        const mime = mimeType || arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new File([u8arr], filename, { type: mime });
    } catch (e) {
        console.warn("Could not restore file from draft:", e);
        return null;
    }
}

function clearAttachment(revokeUrl = true) {
    if (revokeUrl && selectedAttachmentDataUrl && selectedAttachmentDataUrl.startsWith("blob:")) {
        URL.revokeObjectURL(selectedAttachmentDataUrl);
    }
    selectedAttachmentFile = null;
    selectedAttachmentDataUrl = null;
    if (imageInput) imageInput.value = "";
    if (imagePreviewContainer) imagePreviewContainer.style.display = "none";
    if (imagePreviewImg) {
        imagePreviewImg.src = "";
        imagePreviewImg.style.display = "none";
    }
    if (pdfPreviewIcon) pdfPreviewIcon.style.display = "none";
    if (attachBtn) attachBtn.classList.remove("has-file");
}
// Helper to get time in HH:MM AM/PM format
function getCurrentTime() {
    const now = new Date();
    const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return now.toLocaleString('en-US', options).replace(' at ', ', ');
}
// Helper: format bytes into readable KB or MB
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
}

// Keep the active chat in memory and remember it across page refreshes.
function setCurrentChat(chatId) {
    currentChatId = chatId;

    if (chatId === null) {
        localStorage.removeItem("savedChatId");
    } else {
        localStorage.setItem("savedChatId", chatId);
    }
}

// Makes the Textarea clean for Markdown rendering and prevents XSS attacks. If marked.js or DOMPurify are unavailable, it falls back to simple formatting.
function renderMarkdown(text) {
    if (!text) return ""; // 1. If text is empty or null, return nothing so it doesn't crash.
    
    try {
        // 2. Check: Did marked.js load properly from the internet?
        if (window.marked && typeof window.marked.parse === "function") {
            
            // 3. Translate the Markdown into HTML
            const parsed = window.marked.parse(text);
            
            // 4. Pass it to the Security Guard to clean any dangerous tags
            if (window.DOMPurify && typeof window.DOMPurify.sanitize === "function") {
                return window.DOMPurify.sanitize(parsed);
            }
            return parsed;
        }
    } catch (e) {
        console.warn("Marked.js error:", e);
    }
    
    // 5. THE EMERGENCY BACKUP (Fallback)
    // What if the user is offline, or the CDN internet is down?
    // We use simple string replaces so bold (**) and newlines (\n) still format nicely!
    return text
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        .replace(/\n\n+/g, '<br><br>')
        .replace(/\n/g, '<br>');
}


function HandleChatInputState(DisableChat){
    const inputContainer = document.querySelector(".chat-input-container");
    if(DisableChat){
        chatInput.disabled = true;
        // Hide Send, Show Stop
        sendBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
        if (inputContainer) inputContainer.classList.add("generating");
    } else {
        chatInput.disabled = false;
        // Show Send, Hide Stop
        sendBtn.style.display = "inline-block";
        stopBtn.style.display = "none";
        if (inputContainer) inputContainer.classList.remove("generating");
        chatInput.focus();
    }
}

function SwitchTab(Welcome){

    if(Welcome){
        welcomeScreen.style.display = "flex";
        chatHistory.style.display = "none";
    } else {
        welcomeScreen.style.display = "none";
        chatHistory.style.display = "flex";
    }
}

// A reusable function for the typing animation (ABHI USE NI HORA)
function typeText(element, text, speed = 15) {
    element.innerHTML = ""; // Clear it first
    let i = 0;
    
    // Start an interval that runs every 15 milliseconds
    let timer = setInterval(() => {
        if (i < text.length) {
            // Add the next character
            element.innerHTML += text.charAt(i);
            i++;
            
            // Optional: Auto-scroll to the bottom while typing!
            const chatHistory = document.getElementById("chat-history");
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } else {
            // Once all characters are typed, stop the timer and render rich markdown!
            clearInterval(timer);
            element.innerHTML = renderMarkdown(text);
        }
    }, speed);
}

// --- UPGRADED DRAFT SYSTEM (Text + Attachments) ---

function dataURLtoFile(dataurl, filename, mimeType) {
    if (!dataurl || !dataurl.startsWith("data:")) return null;
    try {
        const arr = dataurl.split(',');
        const mime = mimeType || arr[0].match(/:(.*?);/)[1];
        const bstr = atob(arr[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new File([u8arr], filename, { type: mime });
    } catch (e) {
        console.warn("Could not restore file from draft:", e);
        return null;
    }
}

function saveDraft(chatId) {
    const key = chatId !== null ? String(chatId) : "new";
    const text = chatInput ? chatInput.value : "";
    const file = selectedAttachmentFile;
    const dataUrl = selectedAttachmentDataUrl;

    if (!text.trim() && !file) {
        delete chatDrafts[key];
        localStorage.removeItem(`draft_${key}`);
        return;
    }

    chatDrafts[key] = {
        text: text,
        file: file,
        dataUrl: dataUrl,
        fileName: file ? file.name : null,
        fileSize: file ? file.size : null,
        fileType: file ? file.type : null
    };

    try {
        const persistData = {
            text: text,
            fileName: file ? file.name : null,
            fileSize: file ? file.size : null,
            fileType: file ? file.type : null,
            dataUrl: (dataUrl && dataUrl.startsWith("data:") && dataUrl.length < 4 * 1024 * 1024) ? dataUrl : null
        };
        localStorage.setItem(`draft_${key}`, JSON.stringify(persistData));
    } catch (e) {
        console.warn("LocalStorage draft quota exceeded:", e);
    }
}

function loadDraft(chatId) {
    const key = chatId !== null ? String(chatId) : "new";
    clearChatInput();
    clearAttachment();

    let draft = chatDrafts[key];
    if (!draft) {
        const saved = localStorage.getItem(`draft_${key}`);
        if (saved) {
            try {
                draft = JSON.parse(saved);
                if (draft.dataUrl && draft.fileName) {
                    draft.file = dataURLtoFile(draft.dataUrl, draft.fileName, draft.fileType);
                }
            } catch (e) {
                draft = null;
            }
        }
    }

    if (!draft) return;

    if (draft.text) {
        copyToInput(draft.text);
    }

    if (draft.file || draft.dataUrl) {
        selectedAttachmentFile = draft.file || null;
        selectedAttachmentDataUrl = draft.dataUrl || null;

        if (previewFilename && draft.fileName) previewFilename.textContent = draft.fileName;
        if (previewFilesize && draft.fileSize) previewFilesize.textContent = formatFileSize(draft.fileSize);

        const isPdf = draft.fileType === "application/pdf" || (draft.fileName && draft.fileName.toLowerCase().endsWith(".pdf"));

        if (isPdf) {
            if (imagePreviewImg) imagePreviewImg.style.display = "none";
            if (pdfPreviewIcon) pdfPreviewIcon.style.display = "block";
        } else if (draft.dataUrl) {
            if (imagePreviewImg) {
                imagePreviewImg.src = draft.dataUrl;
                imagePreviewImg.style.display = "block";
            }
            if (pdfPreviewIcon) pdfPreviewIcon.style.display = "none";
        }

        if (imagePreviewContainer) imagePreviewContainer.style.display = "flex";
        if (attachBtn) attachBtn.classList.add("has-file");
    }
}

function clearDraft(chatId) {
    const key = chatId !== null ? String(chatId) : "new";
    delete chatDrafts[key];
    localStorage.removeItem(`draft_${key}`);
}




function openSidebarOnMobile() {
    if (window.innerWidth <= 768) {
        sidebar.classList.add("open");
        const backdrop = document.getElementById("sidebar-backdrop");
        if (backdrop) backdrop.classList.add("active");
        loadAllChats();
    }
}

function closeSidebarOnMobile() {
    if (window.innerWidth <= 768) {
        sidebar.classList.remove("open");
        const backdrop = document.getElementById("sidebar-backdrop");
        if (backdrop) backdrop.classList.remove("active");
    }
}

function toggleSidebar() {
    if (window.innerWidth <= 768) {
        if (sidebar.classList.contains("open")) {
            closeSidebarOnMobile();
        } else {
            openSidebarOnMobile();
            loadAllChats(); // Pull fresh chats when drawer opens
        }
    } else {
        sidebar.classList.toggle("collapsed");
        if (!sidebar.classList.contains("collapsed")) {
            loadAllChats(); // Re-sync on PC when opening
        }
    }
}

// Hamburger Button (Toggle drawer on mobile, collapse on desktop)
hamburgerBtn.addEventListener("click", toggleSidebar);

// Mobile touch swipe gestures (ChatGPT app feel)
let touchStartX = 0;
let touchStartY = 0;

document.addEventListener("touchstart", (e) => {
    if (!e.changedTouches || e.changedTouches.length === 0) return;
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

document.addEventListener("touchend", (e) => {
    if (!e.changedTouches || e.changedTouches.length === 0) return;
    const touchEndX = e.changedTouches[0].screenX;
    const touchEndY = e.changedTouches[0].screenY;
    const diffX = touchEndX - touchStartX;
    const diffY = Math.abs(touchEndY - touchStartY);

    // Ignore mostly-vertical scrolling
    if (diffY > 60 || Math.abs(diffX) < 45) return;

    if (window.innerWidth <= 768) {
        // Swipe right from left edge (first 50px of screen) -> Open sidebar
        if (touchStartX < 50 && diffX > 45) {
            openSidebarOnMobile();
        }
        // Swipe left when sidebar is open -> Close sidebar
        else if (diffX < -45 && sidebar.classList.contains("open")) {
            closeSidebarOnMobile();
        }
    }
}, { passive: true });



function updateUIState() {


    // Check if the chat on our screen is currently in the loading list
    if (loadingChats.has(currentChatId)) {

        HandleChatInputState(Disable=1);

    } else {

        HandleChatInputState(Disable=0);

    }
    
    // Toggle Welcome Screen vs Chat History

    
    if (currentChatId === null) {
        SwitchTab(Welcome = 1);
    } else {
        SwitchTab(Welcome = 0);
    }
}

async function loadRealHistory() {
    // Call your new FastAPI endpoint
    const response = await fetch(`/history/${currentChatId}`); 
    history = await response.json();
    
    // Check if this chat is currently generating (survives refresh!)
    const chatData = chats.find(c => c.id === currentChatId);
    if (chatData && chatData.is_generating) {
        loadingChats.add(currentChatId);
    } else {
        loadingChats.delete(currentChatId);
    }
    
    // Tell the DOM to draw the bubbles

    UpdateChatHistory(); 
    updateUIState();

}
async function initializeApp() {
    try {
        const response = await fetch("/users/me");
        if (response.status === 401) {
            loginOverlay.hidden = false;
            return;
        }
        if (!response.ok) {
            throw new Error("Could not verify session");
        }

        const userData = await response.json();
        loginOverlay.hidden = true;

        showChatLoading();
        UpdateUserInfo(userData);
        await loadAllChats(true);
    } catch (error) {
        console.error("initializeApp error:", error);
        loginOverlay.hidden = false;    
    } finally {
        hideChatLoading();
    }
}


function UpdateUserInfo(userData = null) {
    if (!userData) return;

    // 1. Change the name
    if (profileNameElement && userData.username) {
        profileNameElement.textContent = userData.username;
    }

    // 2. Update avatar: use user picture if available, otherwise fallback to /avatar/me backend proxy
    const avatarImg = document.querySelector(".sidebar-profile-avatar img");
    if (avatarImg) {
        avatarImg.referrerPolicy = "no-referrer";
        avatarImg.setAttribute("referrerpolicy", "no-referrer");
        avatarImg.onerror = function() {
            this.onerror = null;
            this.src = "/avatar/me";
        };
        avatarImg.src = userData.picture_url || "/avatar/me";
    }
}

async function loadAllChats(isInitialBoot = false){
    const response = await fetch("/chats"); 
    const fetchedChats = await response.json(); 

    chats = fetchedChats;
    
    if (chats.length === 0) {
        setCurrentChat(null);
        updateUIState();
        UpdateChats();
        return;
    }

    // Only restore previous chat on initial page boot
    if (isInitialBoot && currentChatId === null && chats.length > 0) {
        const savedId = localStorage.getItem("savedChatId");
        let chatExists = false;
        if (savedId) {
            for (let i = 0; i < chats.length; i++) {
                if (chats[i].id == savedId) {
                    chatExists = true;
                    break;
                }
            }
        }
        
        if (chatExists) {
            switchChat(parseInt(savedId));
            return;
        }
        else{
            createNewChat();
            return;
        }
    }

    UpdateChats();
}
function UpdateChats(){
const ChatsContainer = document.querySelector(".chat-list");
ChatsContainer.innerHTML ="";
ChatsContainer.innerHTML +=`<div class="chat-list-header">Recent Chats</div>`;

  // Loop through the real database chats
  for (let i = 0; i < chats.length; i++) {
      const chat = chats[i];
        
      // If this is the chat we are currently looking at, add the grey highlight box!
      let activeClass = "";
      if (chat.id === currentChatId) {
          activeClass = "active";
      }

      const generatingClass = loadingChats.has(chat.id) ? "generating" : "";

      // Draw the button! Notice the onclick="switchChat(id)" magic trick
      ChatsContainer.innerHTML += `
          <div class="chat-item ${activeClass} ${generatingClass}" data-chat-id="${chat.id}" onclick="switchChat(${chat.id})">
              <i class="fa-regular fa-message"></i>
              <span class="chat-title">${escapeHtml(chat.title)}</span>
              
              <!-- Smooth Overlay Actions Container -->
              <div class="chat-actions">
                  <!-- Rename Icon (Dummy for now) -->
                  <button class="action-btn" onclick="event.stopPropagation()">
                      <i class="fa-solid fa-pen"></i>
                  </button>
                  <!-- Delete Icon -->
                  <button class="action-btn delete-btn" onclick="deleteChat(event, ${chat.id})">
                      <i class="fa-solid fa-trash"></i>
                  </button>
              </div>
          </div>
      `;
  }

}
const logoutButton =
    document.getElementById("logout-button");

logoutButton.addEventListener("click", logout);

async function logout() {

    try{
        const response =await fetch("/logout", {method: "POST"});
    }
    catch (error) {
        console.error("Logout request failed:", error);
    }


    // 2. Clear sensitive data from the UI
    chats = [];
    history = [];
    setCurrentChat(null);
    UpdateChatHistory(); 
    profileNameElement.textContent = "";
    const avatarImg = document.querySelector(".sidebar-profile-avatar img");
    if (avatarImg) avatarImg.src = "/avatar/me";
    
    const ChatsContainer = document.querySelector(".chat-list");
    if (ChatsContainer) ChatsContainer.innerHTML = "";

    // 3. Bring the login overlay back up
    loginOverlay.hidden = false;
}

async function deleteChat(event, chatId) {
    // 1. Stop the click from triggering switchChat!
    event.stopPropagation();
    
    // 2. Tell Python to delete it
    await fetch(`/chats/${chatId}`, { method: "DELETE" });
    
    // 3. Immediately clear draft for deleted chat
    clearDraft(chatId);

    // 4. If we just deleted the active chat, reset input and move to fresh chat
    if (currentChatId === chatId) {
        clearChatInput();
        clearAttachment();
        createNewChat();
    }
    
    // 5. Reload sidebar
    await loadAllChats();
}

function createNewChat() {
    stopCurrentAudio();
    for (const [msgId, intervalId] of translationPollers.entries()) {
        clearInterval(intervalId);
    }
    translationPollers.clear();
    closeSidebarOnMobile();
    saveDraft(currentChatId);
    setCurrentChat(null);
    history = [];
    UpdateChatHistory();
    updateUIState();
    loadDraft(null);
    UpdateChats(); 
}

function switchChat(newChatId) {
    stopCurrentAudio();
    for (const [msgId, intervalId] of translationPollers.entries()) {
        clearInterval(intervalId);
    }
    translationPollers.clear();
    closeSidebarOnMobile();
    if (currentChatId === newChatId) return; 
    
    // Save current chat draft (text + attachment)
    saveDraft(currentChatId);
    
    setCurrentChat(newChatId);
    updateUIState();
    
    history = [];
    UpdateChatHistory();

    loadDraft(newChatId);

    UpdateChats();
    loadRealHistory(); 
}

function UpdateChatHistory(){

    
    
    // Clear the container first
    container.innerHTML = "";

    // Loop through the array and inject the timestamp span
    for (let i = 0; i < history.length; i++) {

        
        
        const isClarificationActive = Boolean(
            history[i].role === "ai" &&
            history[i].clarification &&
            history[i].clarification.needed &&
            !history[i].clarification.resolved &&
            history[i].clarification.questions &&
            history[i].clarification.questions.length > 0
        );

        let sourceHtml = "";
        
        if (history[i].role === "ai" && history[i].sources && history[i].sources.length > 0) {
            let realSources = history[i].sources;

            // Partition sources into:
            // 1) Patient Consultation Records (Uploaded Media)
            // 2) Verified Medical Literature & Guidelines (Textbooks)
            let mediaSources = realSources.filter(s => s.kind === "patient_record" || (s.page && s.page.startsWith("Document ")) || s.thumbnail_url || s.file_url);
            let literatureSources = realSources.filter(s => !(s.kind === "patient_record" || (s.page && s.page.startsWith("Document ")) || s.thumbnail_url || s.file_url));

            let groupsHtml = "";

            if (mediaSources.length > 0) {
                let mediaItemsHtml = "";
                for (let s of mediaSources) {
                    const docTitle = s.title || s.page || "Patient Consultation Record";
                    const fileHref = s.file_url || s.thumbnail_url || "";
                    const hasClick = Boolean(fileHref);
                    const thumb = s.thumbnail_url || (s.file_url && !s.file_url.toLowerCase().endsWith(".pdf") ? s.file_url : null);
                    const isPdf = (s.doc_type && s.doc_type.includes("pdf")) || (s.file_name && s.file_name.toLowerCase().endsWith(".pdf")) || (s.file_url && s.file_url.toLowerCase().endsWith(".pdf"));

                    let thumbHtml = "";
                    if (thumb) {
                        thumbHtml = `
                            <div class="source-thumb-container">
                                <img src="${thumb}" alt="Document Preview" class="source-media-thumb" />
                                ${isPdf ? '<span class="source-pdf-tag">PDF</span>' : ''}
                            </div>
                        `;
                    } else if (isPdf) {
                        thumbHtml = `
                            <div class="source-thumb-container source-pdf-icon-box">
                                <i class="fa-solid fa-file-pdf"></i>
                            </div>
                        `;
                    } else {
                        thumbHtml = `
                            <div class="source-thumb-container source-doc-icon-box">
                                <i class="fa-solid fa-file-waveform"></i>
                            </div>
                        `;
                    }

                    mediaItemsHtml += `
                        <div class="source-item source-item-media ${hasClick ? 'clickable-source' : ''}" ${hasClick ? `onclick="window.open('${fileHref}', '_blank')"` : ''} title="${hasClick ? 'Click to open' : ''}">
                            ${thumbHtml}
                            <div class="source-media-info">
                                <div class="source-media-header">
                                    <span class="source-media-badge"><i class="fa-solid fa-file-medical"></i> ${escapeHtml(s.page || 'Attached File')}</span>
                                    ${hasClick ? '<span class="source-view-hint"><i class="fa-solid fa-arrow-up-right-from-square"></i> Open</span>' : ''}
                                </div>
                                <div class="source-media-title">${escapeHtml(s.file_name || docTitle)}</div>
                            </div>
                        </div>
                    `;
                }

                groupsHtml += `
                    <div class="source-group-section">
                        <div class="source-group-heading">
                            <i class="fa-solid fa-paperclip"></i> Attached Files (${mediaSources.length})
                        </div>
                        <div class="source-group-body">
                            ${mediaItemsHtml}
                        </div>
                    </div>
                `;
            }

            if (literatureSources.length > 0) {
                let litItemsHtml = "";
                for (let s of literatureSources) {
                    litItemsHtml += `
                        <div class="source-item source-item-literature">
                            <span class="source-page"><i class="fa-solid fa-book"></i> ${escapeHtml(s.page || s.title || 'Medical Book')}</span>
                            <span class="source-text">${escapeHtml(s.text || '')}</span>
                        </div>
                    `;
                }

                groupsHtml += `
                    <div class="source-group-section ${mediaSources.length > 0 ? 'source-group-divider' : ''}">
                        <div class="source-group-heading">
                            <i class="fa-solid fa-book-medical"></i> Medical References (${literatureSources.length})
                        </div>
                        <div class="source-group-body">
                            ${litItemsHtml}
                        </div>
                    </div>
                `;
            }

            const totalCount = realSources.length;
            const sourcesHiddenStyle = isClarificationActive ? ' style="display: none;"' : '';
            sourceHtml = `
                <div class="sources-container" id="msg-sources-${i}"${sourcesHiddenStyle}>
                    <div class="source-header" onclick="this.nextElementSibling.classList.toggle('open'); this.querySelector('.source-chevron')?.classList.toggle('rotated')">
                        <span><i class="fa-solid fa-book-open"></i> Sources (${totalCount})</span>
                        <i class="fa-solid fa-chevron-down source-chevron"></i>
                    </div>
                    <div class="source-content">
                        ${groupsHtml}
                    </div>
                </div>
            `;
        }

        // Give a pop animation ONLY to the very last message in the chat
        let popClass = (i === history.length - 1) ? "animate-pop" : "";
        
        // Create the Action buttons for the footer!
        let actionBtns = "";
        if (history[i].role === "user") {
            actionBtns = `
                <button class="msg-action-btn" onclick="copyPromptFromMsg(this)" title="Reuse Prompt">
                    <i class="fa-solid fa-arrow-rotate-left"></i>
                </button>
            `;
        } else if (history[i].role === "ai") {
            actionBtns = renderVoiceControl(history[i]);
        }

        // Format content based on role: AI gets rich markdown, user & error get safe escaped HTML
        let msgContent = "";
        if (history[i].role === "error") {
            msgContent = `<i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(history[i].content)}`;
        } 
        else if (isClarificationActive) {
         // 🩺 Show doctor intro banner instead of the full consultation text
        msgContent = `
        <div class="clarification-intro-banner">
            <i class="fa-solid fa-stethoscope"></i>
            <span>To provide the safest clinical guidance, please help clarify this detail before I finalize your full consultation:</span>
        </div>
        `;
        }   
        else if (history[i].role === "ai") {
            msgContent = renderMarkdown(history[i].content);
        }
        else {
            msgContent = escapeHtml(history[i].content);
        }

        // Attachment HTML for user uploaded images or PDFs
        let attachmentHtml = "";
        const attachUrl = history[i].attachmentUrl || history[i].file_url || history[i].image_url;
        const thumbUrl = history[i].thumbnail_url;
        const attachType = history[i].attachmentType || history[i].file_type || (attachUrl && attachUrl.toLowerCase().endsWith(".pdf") ? "pdf" : "image");
        const attachName = history[i].attachmentName || history[i].file_name || "Attachment";

        if (attachUrl || thumbUrl) {
            const targetUrl = attachUrl || thumbUrl;
            if (attachType === "pdf") {
                const hasPageThumb = thumbUrl && !thumbUrl.toLowerCase().endsWith(".pdf") && !thumbUrl.startsWith("blob:");
                const pdfTitle = escapeHtml(attachName || "Medical Report.pdf");
                attachmentHtml = `
                    <div class="msg-pdf-card" onclick="window.open('${targetUrl}', '_blank')" title="Click to view ${pdfTitle}">
                        ${hasPageThumb ? `
                            <div class="msg-pdf-thumb-wrap">
                                <img src="${thumbUrl}" alt="PDF Page Preview" class="msg-pdf-thumb-img" loading="lazy" />
                                <span class="msg-pdf-badge"><i class="fa-solid fa-file-pdf"></i> PDF</span>
                            </div>
                        ` : `
                            <div class="msg-pdf-icon-badge">
                                <i class="fa-solid fa-file-pdf"></i>
                                <span>PDF</span>
                            </div>
                        `}
                        <div class="msg-pdf-details">
                            <span class="msg-pdf-title" title="${pdfTitle}">${pdfTitle}</span>
                            <span class="msg-pdf-sub"><i class="fa-solid fa-arrow-up-right-from-square"></i> Click to open PDF</span>
                        </div>
                    </div>
                `;
            } else {
                const safeName = escapeHtml(attachName || 'Attached Document');
                attachmentHtml = `
                    <div class="msg-image-attachment" onclick="window.open('${targetUrl}', '_blank')" title="Click to view full image">
                        <img src="${thumbUrl || targetUrl}" alt="${safeName}" loading="lazy" decoding="async" onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'msg-doc-fallback\\'><i class=\\'fa-solid fa-file-medical\\'></i> <span>${safeName}</span></div>';" />
                    </div>
                `;
            }
        }

        const clarificationHtml = isClarificationActive ? renderClarificationCard(i, history[i].clarification) : "";

        // Inject cleanly into message bubble!
        container.innerHTML += `
        <div class="message ${history[i].role}-message ${popClass}" id="msg-bubble-${i}">
            ${attachmentHtml}
            <div class="msg-text" id="msg-text-${i}">${msgContent}</div>
            ${clarificationHtml}
            ${sourceHtml}
            ${renderMessageFooter(i, history[i].time, actionBtns, !isClarificationActive)}
        </div>`;
    }
    
    // Auto-scroll to the bottom when a new message is added
    container.scrollTop = container.scrollHeight;
}






chatInput.addEventListener('keydown', (event) => {
  if (event.code === 'Enter' && !event.shiftKey) {
    event.preventDefault(); 
    sendMessage();
  }
});

loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    loginError.hidden = true;
    loginError.textContent = "";

    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            loginError.textContent = data.detail || "Login failed. Check your username and password.";
            loginError.hidden = false;
            return;
        }

        loginOverlay.hidden = true;
        await initializeApp();
    } catch (error) {
        console.error("Login failed:", error);
        loginError.textContent = "Could not connect to the server. Please try again.";
        loginError.hidden = false;
    }
});

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    registerError.hidden = true;
    registerSuccess.hidden = true;

    const username =
        document.getElementById("register-username").value;

    const email =
        document.getElementById("register-email").value;

    const password =
        document.getElementById("register-password").value;

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                email,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            registerError.textContent =
                data.detail || "Could not create the account.";

            registerError.hidden = false;
            return;
        }

        registerSuccess.textContent = data.message;
        registerSuccess.hidden = false;
        registerForm.reset();

    } catch (error) {
        registerError.textContent =
            "Could not connect to the server.";

        registerError.hidden = false;
    }
});

showRegisterButton.addEventListener("click", () => {
    loginView.hidden = true;
    registerView.hidden = false;
    initGoogleAuth();
});

showLoginButton.addEventListener("click", () => {
    registerView.hidden = true;
    loginView.hidden = false;
    initGoogleAuth();
});


function updateWordCounter() {
    if (!wordCounter) return;
    const chars = chatInput.value.length;
    wordCounter.textContent = `${chars}/500`;
    if (chars > 500) {
        wordCounter.classList.add("limit-exceeded");
        sendBtn.disabled = true;
    } else {
        wordCounter.classList.remove("limit-exceeded");
        sendBtn.disabled = false;
    }
}

// Auto-expand textarea height as the user types
chatInput.addEventListener('input', function() {
  this.style.height = 'auto';
  let newHeight = this.scrollHeight;
  if (newHeight > 120) {
      newHeight = 120;
  }
  this.style.height = newHeight + 'px';
  updateWordCounter();
});

function clearChatInput() {
    chatInput.value = "";
    chatInput.style.height = "auto";
    updateWordCounter();
}

function addMessageToHistory(role, content, sources = null, messageId = null, clarification = null) {
    let cleanClarification = clarification;
    if (cleanClarification && cleanClarification.needed && cleanClarification.questions && cleanClarification.questions.length > 0) {
        cleanClarification.currentIndex = 0;
        cleanClarification.userAnswers = [];
        cleanClarification.resolved = false;
        cleanClarification.isRefining = false;
    }
    history.push({ 
        role, 
        content, 
        time: getCurrentTime(), 
        sources, 
        id: messageId,
        clarification: cleanClarification 
    });
    UpdateChatHistory();
}

function addMessageIfViewing(chatId, role, content, sources = null, messageId = null, clarification = null) {
    if (currentChatId === chatId) {
        addMessageToHistory(role, content, sources, messageId, clarification);
    }
}

function setChatLoading(chatId, isLoading) {
    if (isLoading) {
        loadingChats.add(chatId);
    } else {
        loadingChats.delete(chatId);
    }
    const targetItem = document.querySelector(`.chat-item[data-chat-id="${chatId}"]`);
    if (targetItem) {
        targetItem.classList.toggle("generating", isLoading);
    }
    updateUIState();
}

async function ensureCurrentChat(userMessage) {
    if (currentChatId !== null) return;
    const response = await fetch(
        "/chats/new?user_prompt=" + encodeURIComponent(userMessage),
        { method: "POST" }
    );
    const data = await response.json();
    setCurrentChat(data.id);
    updateUIState();
    await loadAllChats();
}
async function requestBotReply(message, chatId, file = null) {
    if (file) {
        // Send as multipart/form-data
        const formData = new FormData();
        formData.append("message", message || "");
        formData.append("chat_id", chatId);
        formData.append("file", file);

        const response = await fetch("/chat", {
            method: "POST",
            body: formData,
            signal: currentController.signal
        });
        return response.json();
    } else {
        // Normal JSON request
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, chat_id: chatId }),
            signal: currentController.signal
        });
        return response.json();
    }
}

function pollForNewChatTitle(chatId) {
    let attempts = 0;
    const currentChatObj = chats.find(c => c.id === chatId);
    const initialTitle = currentChatObj ? currentChatObj.title : "";
    const titleChecker = setInterval(async () => {
        attempts++;
        if (attempts > 12) {
            clearInterval(titleChecker);
            return;
        }
        try {
            const response = await fetch("/chats");
            if (!response.ok) return;
            const freshChats = await response.json();
            const updatedChat = freshChats.find(chat => chat.id === chatId);
            if (updatedChat && updatedChat.title && updatedChat.title !== initialTitle) {
                chats = freshChats;
                UpdateChats();
                clearInterval(titleChecker);
            }
        } catch (err) {
            // Network glitch during polling, retry on next interval
        }
    }, 2000);
}

// --- THE STOP GENERATING FUNCTION ---
async function stopGenerating() {
    // 1. Abort the fetch connection (kills the browser's wait)
    if (currentController) {
        currentController.abort();
        currentController = null;
    }
    
    // 2. Tell Python to stop and save the cancellation error message
    await fetch(`/chat/stop/${currentChatId}`, { method: "POST" });

    if (currentChatId) {

        const targetChat = chats.find(c => c.id === currentChatId);

        if (targetChat) {
        targetChat.is_generating = false;
        }
    }
    // 3. Unlock the UI and reload history from DB to get the error message
    setChatLoading(currentChatId, false);
    UpdateChats();
    await loadRealHistory();
}


async function sendMessage() {
    const userMessage = chatInput.value.trim();
    const attachedFile = selectedAttachmentFile;
    const attachedDataUrl = selectedAttachmentDataUrl;
    const attachedFileName = selectedAttachmentFile ? selectedAttachmentFile.name : null;
    const attachedFileType = selectedAttachmentFile ? (selectedAttachmentFile.type === "application/pdf" || selectedAttachmentFile.name.toLowerCase().endsWith(".pdf") ? "pdf" : "image") : null;

    // Allow sending if there is text OR an attached file
    if (userMessage === "" && !attachedFile) return;
    if (userMessage.length > 500) return;

    clearChatInput();
    clearAttachment(false); // Clears preview from input box while keeping preview URL for the chat bubble

    clearDraft(null);

    const promptForChatTitle = userMessage || (attachedFileType === "pdf" ? "Medical PDF Analysis" : "Medical Image Consultation");
    await ensureCurrentChat(promptForChatTitle);

    // Push message to local history with attachment metadata
    history.push({
        role: "user",
        content: userMessage,
        time: getCurrentTime(),
        attachmentUrl: attachedDataUrl,
        attachmentName: attachedFileName,
        attachmentType: attachedFileType
    });
    UpdateChatHistory();

    const chatWeSentTo = currentChatId;
    clearDraft(chatWeSentTo);
    setChatLoading(chatWeSentTo, true);
    currentController = new AbortController();

    try {
        const data = await requestBotReply(userMessage, chatWeSentTo, attachedFile);
        if (data.cancelled) return;

        if (data.error) {
            addMessageIfViewing(chatWeSentTo, "error", data.message);
            return;
        }

        // Update sent user message with permanent server storage URL
        if (data.user_attachment && history.length > 0) {
            const userMsg = history.find(m => m.role === "user" && (m.attachmentName === attachedFileName || m.attachmentUrl === attachedDataUrl));
            if (userMsg) {
                userMsg.file_url = data.user_attachment.file_url;
                userMsg.thumbnail_url = data.user_attachment.thumbnail_url;
                userMsg.file_name = data.user_attachment.file_name;
                userMsg.file_type = data.user_attachment.file_type;
                userMsg.attachmentUrl = data.user_attachment.file_url;
            }
        }

        const aiMessage = data.response ?? "There was an unexpected server error.";
        addMessageIfViewing(chatWeSentTo, "ai", aiMessage, data.sources, data.message_id, data.clarification);

        if (currentChatId === chatWeSentTo) {
            pollForNewChatTitle(chatWeSentTo);
        }
    } catch (error) {
        if (error.name !== "AbortError") {
            console.error("Error:", error);
            addMessageIfViewing(chatWeSentTo, "error", "Network error. Please check your connection.");
        }
    } finally {
        currentController = null;
        setChatLoading(chatWeSentTo, false);
        const targetChat = chats.find(c => c.id === chatWeSentTo);
        if (targetChat) {
            targetChat.is_generating = false;
        }
    }
}
// --- Google Sign-In Initialization & Callback ---
async function initGoogleAuth(retries = 25) {
    try {
        const res = await fetch("/auth/google/client-id");
        if (!res.ok) return;
        const { client_id } = await res.json();
        
        if (!client_id) {
            console.warn("[Google Auth]: No client_id configured.");
            return;
        }

        // Retry until Google Identity Services (GSI) script is loaded
        if (!window.google || !window.google.accounts || !window.google.accounts.id) {
            if (retries > 0) {
                setTimeout(() => initGoogleAuth(retries - 1), 150);
            } else {
                console.warn("[Google Auth]: Google GSI script blocked or timed out.");
            }
            return;
        }

        google.accounts.id.initialize({
            client_id: client_id,
            callback: handleGoogleCredentialResponse,
            auto_select: false,
            cancel_on_tap_outside: true
        });

        // Render button in Login view
        const loginBtn = document.getElementById("google-login-btn");
        if (loginBtn) {
            google.accounts.id.renderButton(loginBtn, {
                theme: "filled_black",
                size: "large",
                width: 320,
                shape: "rectangular"
            });
        }

        // Render button in Register view
        const registerBtn = document.getElementById("google-register-btn");
        if (registerBtn) {
            google.accounts.id.renderButton(registerBtn, {
                theme: "filled_black",
                size: "large",
                width: 320,
                shape: "rectangular"
            });
        }
    } catch (e) {
        console.error("Failed to initialize Google Auth:", e);
    }
}

async function handleGoogleCredentialResponse(response) {
    try {
        const res = await fetch("/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ credential: response.credential })
        });

        const data = await res.json();

        if (!res.ok) {
            const loginError = document.getElementById("login-error");
            if (loginError) {
                loginError.textContent = data.detail || "Google login failed.";
                loginError.hidden = false;
            }
            return;
        }

        // Unlock the app!
        loginOverlay.hidden = true;
        await initializeApp();

    } catch (error) {
        console.error("Google authentication error:", error);
    }
}

window.addEventListener("load", initGoogleAuth);

