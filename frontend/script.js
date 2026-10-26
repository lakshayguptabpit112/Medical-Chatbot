








let history = [];

//ALL CHATS ARE STORED IN THIS
let chats = [];

//ALL CHATS LOADING ARE IN THIS SET 
const loadingChats = new Set();


// CHat ID WE ARE WATCHING RN IF NO CHAT THEN IT WOULD BE WELCOME TAB THANKS TO UPDATE UI STATE
let currentChatId = null;


//Aborts Generation Request 
let currentController = null;


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



function showChatLoading() { chatLoading.hidden = false; }
function hideChatLoading() { chatLoading.hidden = true; }

sendBtn.onclick = sendMessage;



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

// Helper to get time in HH:MM AM/PM format
function getCurrentTime() {
    const now = new Date();
    const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return now.toLocaleString('en-US', options).replace(' at ', ', ');
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


function HandleChatInputState(DisableChat){

    if(DisableChat){

        chatInput.disabled = true;
        // Hide Send, Show Stop
        sendBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
    } else {
        chatInput.disabled = false;
        // Show Send, Hide Stop
        sendBtn.style.display = "inline-block";
        stopBtn.style.display = "none";
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
            // Once all characters are typed, stop the timer!
            clearInterval(timer);
        }
    }, speed);
}

//main Functions

function saveDraft(chatId, text) {
    if (text.trim() !== "") {
        sessionStorage.setItem(`draft_${chatId}`, text);
    } else {
        sessionStorage.removeItem(`draft_${chatId}`);
    }
}
function loadDraft(chatId) {
    const draft = sessionStorage.getItem(`draft_${chatId}`);
    if (draft) {
        copyToInput(draft);
        sessionStorage.removeItem(`draft_${chatId}`);
    } else {
        copyToInput("");
    }
}




function openSidebarOnMobile() {
    if (window.innerWidth <= 768) {
        sidebar.classList.add("open");
        const backdrop = document.getElementById("sidebar-backdrop");
        if (backdrop) backdrop.classList.add("active");
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
        }
    } else {
        sidebar.classList.toggle("collapsed");
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

        if (!response.ok) {
            throw new Error("Could not load chats");
        }

        loginOverlay.hidden = true;

        showChatLoading()
        await UpdateUserInfo();
        await loadAllChats();
        hideChatLoading()
  

    } catch (error) {
        loginOverlay.hidden = false;    
    }
}


async function UpdateUserInfo() {
    const response = await fetch("/users/me");
    const userData = await response.json();

    // 2. Change the name
    profileNameElement.textContent = userData.username;

    // 3. Update avatar with Google photo if available
    const avatarImg = document.querySelector(".sidebar-profile-avatar img");
    if (avatarImg && userData.picture_url) {
        avatarImg.src = userData.picture_url;
    }
}

async function loadAllChats(){
    const response = await fetch("/chats"); 
    const fetchedChats = await response.json(); 

    chats = fetchedChats;
    
    if (chats.length === 0) {
        setCurrentChat(null);
        updateUIState();
    }

    if (currentChatId === null && chats.length > 0) {
        
        // 1. Ask the browser what chat we were looking at before we refreshed!
        const savedId = localStorage.getItem("savedChatId");
        
        // 2. Double check that this chat wasn't deleted in another tab!
        let chatExists = false;
        if (savedId) {
            for (let i = 0; i < chats.length; i++) {
                if (chats[i].id == savedId) { // Use == because localStorage saves numbers as Strings!
                    chatExists = true;
                    break;
                }
            }
        }
        
        // 3. If it is safe, load it! Otherwise, fallback to the top chat!
        let targetId;
        if (chatExists) {
            targetId = parseInt(savedId);
        } else {
            targetId = chats[0].id;
        }
        
        // Instead of doing it manually, just use our switchChat function!
        switchChat(targetId);
    } else {
        // If currentChatId is NOT null, it means we are just reloading the sidebar
        // so we just need to redraw the buttons.
        UpdateChats();
    }
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

      // Draw the button! Notice the onclick="switchChat(id)" magic trick
      ChatsContainer.innerHTML += `
          <div class="chat-item ${activeClass}" onclick="switchChat(${chat.id})">
              <i class="fa-regular fa-message"></i>
              <span class="chat-title">${chat.title}</span>
              
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
    if (avatarImg) avatarImg.src = "https://cdn-icons-png.flaticon.com/512/3304/3304567.png";
    
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
    
    // 3. If we just deleted the chat we were actively looking at, reset the ID!
    if (currentChatId === chatId) {
        setCurrentChat(null);
    }
    
    // 4. Reload the sidebar (if it was the last chat, Python will auto-create a new one!)
    loadAllChats();
}

function createNewChat() {
    closeSidebarOnMobile();
    setCurrentChat(null);
    history = [];
    UpdateChatHistory(); // Will clear the container
    updateUIState();
}

function switchChat(newChatId) {
    closeSidebarOnMobile();
    if (currentChatId === newChatId) return; 
    
    // Save the user's currently typed text before we switch away!
    if (currentChatId !== null) {
        const currentInput = document.querySelector("#chat-input").value;
        saveDraft(currentChatId, currentInput);
    }
    
    setCurrentChat(newChatId);

    updateUIState();
    
    history = [];
    UpdateChatHistory();

    loadDraft(newChatId);

    UpdateChats(); // Redraw sidebar to show the active grey highlight, no need to fetch db!
    loadRealHistory(); 
}

function UpdateChatHistory(){
    
    // Clear the container first
    container.innerHTML = "";

    // Loop through the array and inject the timestamp span
    for (let i = 0; i < history.length; i++) {
        
        let sourceHtml = "";
        
                if (history[i].role === "ai" && history[i].sources && history[i].sources.length > 0) {
            
            let realSources = history[i].sources;

            let itemsHtml = "";
            for (let j = 0; j < realSources.length; j++) {
                itemsHtml += `
                    <div class="source-item">
                        <span class="source-page">${realSources[j].page}</span>
                        <span>${realSources[j].text}</span>
                    </div>
                `;
            }
            
            sourceHtml = `
                <div class="sources-container">
                    <div class="source-header" onclick="this.nextElementSibling.classList.toggle('open')">
                        <i class="fa-solid fa-book"></i> View Sources (${realSources.length})
                    </div>
                    <div class="source-content">
                        ${itemsHtml}
                    </div>
                </div>
            `;
        }

        // Give a pop animation ONLY to the very last message in the chat
        let popClass = (i === history.length - 1) ? "animate-pop" : "";
        
        // Create the Action buttons for the footer!
        let actionBtns = "";
        if (history[i].role === "user") {
            let safeContent = encodeURIComponent(history[i].content);
            actionBtns = `
                <button class="msg-action-btn" onclick="copyToInput(decodeURIComponent('${safeContent}'))" title="Reuse Prompt">
                    <i class="fa-solid fa-arrow-rotate-left"></i>
                </button>
            `;
        }
        
        // Error messages get a warning icon prefix
        let msgContent = history[i].content;
        if (history[i].role === "error") {
            msgContent = `<i class="fa-solid fa-triangle-exclamation"></i> ${history[i].content}`;
        }

        // Inject the message, sources, and our new clean footer!
        container.innerHTML += `
        <div class="message ${history[i].role}-message ${popClass}">
            <span class="msg-text">${msgContent}</span>
            ${sourceHtml}
            <div class="msg-footer">
                <div class="msg-actions">${actionBtns}</div>
                <div class="timestamp">${history[i].time}</div>
            </div>
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
});

showLoginButton.addEventListener("click", () => {
    registerView.hidden = true;
    loginView.hidden = false;
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

function addMessageToHistory(role, content, sources = null) {
    history.push({ role, content, time: getCurrentTime(), sources });
    UpdateChatHistory();
}

function addMessageIfViewing(chatId, role, content, sources = null) {
    if (currentChatId === chatId) {
        addMessageToHistory(role, content, sources);
    }
}

function setChatLoading(chatId, isLoading) {
    if (isLoading) {
        loadingChats.add(chatId);
    } else {
        loadingChats.delete(chatId);
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

    // Load the new chat into the sidebar before continuing.
    await loadAllChats();
    updateUIState();
}

async function requestBotReply(message, chatId) {
    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message, chat_id: chatId }),
        signal: currentController.signal
    });
    return response.json();
}

function pollForNewChatTitle(chatId) {
    let attempts = 0;
    const titleChecker = setInterval(async () => {
        attempts++;
        if (attempts > 10) {
            clearInterval(titleChecker);
            return;
        }

        const response = await fetch("/chats");
        const freshChats = await response.json();
        const updatedChat = freshChats.find(chat => chat.id === chatId);

        if (updatedChat && !updatedChat.title.includes("...")) {
            chats = freshChats;
            UpdateChats();
            clearInterval(titleChecker);
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
    
    // 3. Unlock the UI and reload history from DB to get the error message
    setChatLoading(currentChatId, false);
    await loadRealHistory();
}


async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (userMessage === "" || userMessage.length > 500) return;

    clearChatInput();
    await ensureCurrentChat(userMessage);
    addMessageToHistory("user", userMessage);

    const chatWeSentTo = currentChatId;
    setChatLoading(chatWeSentTo, true);
    currentController = new AbortController();

    try {
        const data = await requestBotReply(userMessage, chatWeSentTo);
        if (data.cancelled) return;

        if (data.error) {
            addMessageIfViewing(chatWeSentTo, "error", data.message);
            return;
        }

        const aiMessage = data.response ?? "There was an unexpected server error. Please refresh the page and try again.";
        addMessageIfViewing(chatWeSentTo, "ai", aiMessage, data.sources);

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
    }
}
// --- Google Sign-In Initialization & Callback ---
async function initGoogleAuth() {
    try {
        const res = await fetch("/auth/google/client-id");
        const { client_id } = await res.json();
        
        if (!client_id || !window.google) return;

        google.accounts.id.initialize({
            client_id: client_id,
            callback: handleGoogleCredentialResponse
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

