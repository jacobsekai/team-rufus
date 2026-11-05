// T Levels chat panel, opened from a round Rufus (corgi) icon button in the
// bottom-right corner (accessible name "Ask about T Levels"). Add to every
// page with:
//   <script src="/chat/chat-widget.js" defer></script>
//
// Sends questions to POST /api/chat. The conversation lives only in this
// page's memory: it is gone when the page is closed or reloaded.

const CHAT_LIMITS = { maxMessages: 20, maxTotalChars: 12000, maxQuestionChars: 1000 };

const CHAT_WELCOME = "Hi! I can answer questions about T Levels, placements at Amazon, and this website. " +
    "Please don't share personal details like your name or email here.";

const CHAT_SUGGESTIONS = [
    "What is a T Level?",
    "How does the Amazon placement application work?",
    "How many UCAS points is a Distinction worth?",
    "Do I need an account to download the checklists?",
];

// Keep the most recent messages that fit the server's limits. The result
// always starts with a user message, as the API requires.
function trimHistory(history, limits) {
    const kept = [];
    let total = 0;
    for (let i = history.length - 1; i >= 0; i -= 1) {
        const size = history[i].content.length;
        if (kept.length >= limits.maxMessages || total + size > limits.maxTotalChars) break;
        kept.unshift(history[i]);
        total += size;
    }
    while (kept.length && kept[0].role !== "user") kept.shift();
    return kept;
}

async function chatSha256Hex(text) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest)).map(function (b) {
        return b.toString(16).padStart(2, "0");
    }).join("");
}

async function askChat(messages) {
    const body = JSON.stringify({ messages: messages });
    const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            // CloudFront signs requests to the Lambda backend and needs the
            // body's SHA-256 hash to do so.
            "x-amz-content-sha256": await chatSha256Hex(body),
        },
        body: body,
    });
    if (response.status === 403) {
        return { status: "error", reply: "Your Midway sign-in has expired. Reload the page and try again." };
    }
    let data = null;
    try { data = await response.json(); } catch (e) {}
    if (!response.ok || !data || typeof data.reply !== "string") {
        return { status: "error", reply: "The assistant isn't available right now. Please try again later." };
    }
    return data;
}

// Rufus's head, the same artwork as the logo peek (scripts/rufus-peek.js),
// copied here so the chat button works on pages without that script.
// Decorative: the button's aria-label gives it its name.
const RUFUS_ICON_SVG =
    '<svg viewBox="-345 -1040 690 800" width="46" height="46" aria-hidden="true" focusable="false" ' +
    'xmlns="http://www.w3.org/2000/svg"><g class="rufus-chat-head">' +
    // Ears
    '<g class="rufus-chat-ear rufus-chat-ear-left">' +
    '<path d="M-262,-590 C-312,-760 -306,-910 -250,-1010 C-176,-958 -104,-866 -66,-752 Z" fill="#F0A42C"/>' +
    '<path d="M-230,-640 C-262,-762 -258,-866 -230,-940 C-184,-898 -142,-834 -116,-760 Z" fill="#FCD9B0"/>' +
    '</g><g class="rufus-chat-ear rufus-chat-ear-right">' +
    '<path d="M262,-590 C312,-760 306,-910 250,-1010 C176,-958 104,-866 66,-752 Z" fill="#F0A42C"/>' +
    '<path d="M230,-640 C262,-762 258,-866 230,-940 C184,-898 142,-834 116,-760 Z" fill="#FCD9B0"/>' +
    '</g>' +
    // Head and cream blaze
    '<path d="M0,-815 C182,-815 296,-702 300,-548 C304,-420 238,-318 0,-298 C-238,-318 -304,-420 -300,-548 C-296,-702 -182,-815 0,-815 Z" fill="#F5B335"/>' +
    '<path d="M0,-770 C30,-770 42,-694 54,-604 C156,-590 270,-514 272,-424 C266,-338 152,-300 0,-298 C-152,-300 -266,-338 -272,-424 C-270,-514 -156,-590 -54,-604 C-42,-694 -30,-770 0,-770 Z" fill="#FBE3C0"/>' +
    '<ellipse cx="-122" cy="-632" rx="24" ry="15" fill="#FBE3C0"/>' +
    '<ellipse cx="122" cy="-632" rx="24" ry="15" fill="#FBE3C0"/>' +
    // Eyes
    '<circle cx="-120" cy="-548" r="40" fill="#2B1A12"/><circle cx="-132" cy="-562" r="12" fill="#FFFFFF"/>' +
    '<circle cx="120" cy="-548" r="40" fill="#2B1A12"/><circle cx="108" cy="-562" r="12" fill="#FFFFFF"/>' +
    // Blush
    '<ellipse cx="-200" cy="-440" rx="40" ry="22" fill="#FF8F7A" opacity="0.45"/>' +
    '<ellipse cx="200" cy="-440" rx="40" ry="22" fill="#FF8F7A" opacity="0.45"/>' +
    // Muzzle, mouth and tongue
    '<ellipse cx="0" cy="-408" rx="128" ry="88" fill="#FFF3E2"/>' +
    '<path d="M-84,-396 C-66,-338 -34,-312 0,-312 C34,-312 66,-338 84,-396 C54,-380 26,-386 0,-402 C-26,-386 -54,-380 -84,-396 Z" fill="#6B2B23"/>' +
    '<path d="M-40,-352 C-44,-296 -22,-262 0,-262 C22,-262 44,-296 40,-352 C20,-340 -20,-340 -40,-352 Z" fill="#FF7486"/>' +
    '<path d="M0,-342 L0,-296" stroke="#E0506A" stroke-width="8" stroke-linecap="round"/>' +
    '<path d="M-96,-404 C-70,-384 -30,-384 0,-404 C30,-384 70,-384 96,-404" fill="none" stroke="#3A2018" stroke-width="11" stroke-linecap="round"/>' +
    '<path d="M0,-428 L0,-402" stroke="#3A2018" stroke-width="11" stroke-linecap="round"/>' +
    // Nose
    '<path d="M-60,-472 C-60,-514 60,-514 60,-472 C60,-440 22,-420 0,-420 C-22,-420 -60,-440 -60,-472 Z" fill="#1E1410"/>' +
    '<ellipse cx="-20" cy="-490" rx="17" ry="9" fill="#FFFFFF" opacity="0.7"/>' +
    '</g></svg>';

const CHAT_BUTTON_LABEL = "Ask about T Levels";

function addChatWidget(doc) {
    if (doc.getElementById("rufus-chat-button")) return;

    const style = doc.createElement("style");
    // Minimal styling so the panel works on any page; the frontend team can
    // restyle everything under #rufus-chat-panel and #rufus-chat-button.
    style.textContent = [
        // Round Rufus icon button: navy disc with an orange ring.
        "#rufus-chat-button{position:fixed;right:24px;bottom:24px;z-index:1000;width:60px;height:60px;padding:0;",
        "display:flex;align-items:center;justify-content:center;border:3px solid #FF9900;border-radius:50%;",
        "background:#232F3E;color:#0F1111;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);",
        "transition:transform .2s ease,box-shadow .2s ease}",
        "#rufus-chat-button svg{display:block;width:46px;height:46px;margin-top:2px;pointer-events:none}",
        ".rufus-chat-head{transform-box:fill-box;transform-origin:50% 90%}",
        ".rufus-chat-ear-left{transform-box:fill-box;transform-origin:80% 100%}",
        ".rufus-chat-ear-right{transform-box:fill-box;transform-origin:20% 100%}",
        "#rufus-chat-button:is(:hover,:focus-visible){transform:translateY(-3px);box-shadow:0 8px 18px rgba(0,0,0,.35)}",
        // White ring fills the outline gap so the dark focus outline also shows on navy sections.
        "#rufus-chat-button:focus-visible{box-shadow:0 0 0 2px #fff,0 8px 18px rgba(0,0,0,.35)}",
        "#rufus-chat-button:is(:hover,:focus-visible) .rufus-chat-head{animation:rufus-chat-wiggle .6s ease-in-out}",
        "#rufus-chat-button:is(:hover,:focus-visible) .rufus-chat-ear-left{animation:rufus-chat-ear-l .6s ease-in-out}",
        "#rufus-chat-button:is(:hover,:focus-visible) .rufus-chat-ear-right{animation:rufus-chat-ear-r .6s ease-in-out}",
        "@keyframes rufus-chat-wiggle{0%,100%{transform:rotate(0)}25%{transform:rotate(-8deg)}60%{transform:rotate(6deg)}}",
        "@keyframes rufus-chat-ear-l{0%,100%{transform:rotate(0)}40%{transform:rotate(-10deg)}}",
        "@keyframes rufus-chat-ear-r{0%,100%{transform:rotate(0)}55%{transform:rotate(10deg)}}",
        "@media (prefers-reduced-motion:reduce){#rufus-chat-button{transition:none}",
        "#rufus-chat-button:is(:hover,:focus-visible){transform:none}",
        "#rufus-chat-button:is(:hover,:focus-visible) :is(.rufus-chat-head,.rufus-chat-ear){animation:none}}",
        "#rufus-chat-panel{position:fixed;right:24px;bottom:88px;z-index:1000;width:min(380px,calc(100vw - 48px));",
        "height:min(560px,calc(100vh - 120px));display:flex;flex-direction:column;background:#fff;color:#0F1111;",
        "border:1px solid #D5D9D9;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.25);font:1rem/1.45 sans-serif}",
        "#rufus-chat-panel[hidden]{display:none}",
        "#rufus-chat-panel header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;",
        "background:#232F3E;color:#fff;border-radius:12px 12px 0 0}",
        "#rufus-chat-panel header h2{margin:0;font-size:1.0625rem}",
        "#rufus-chat-panel header button{background:none;border:0;color:#fff;font-size:0.9375rem;cursor:pointer;text-decoration:underline}",
        "#rufus-chat-log{flex:1;overflow-y:auto;padding:12px 16px}",
        "#rufus-chat-log p{margin:0 0 10px;padding:8px 12px;border-radius:10px;white-space:pre-wrap}",
        "#rufus-chat-log .rufus-user{background:#FEF5E7;margin-left:32px}",
        "#rufus-chat-log .rufus-assistant{background:#F0F2F2;margin-right:32px}",
        "#rufus-chat-log .rufus-note{background:none;color:#565959;font-size:0.875rem;padding:0}",
        "#rufus-chat-suggestions{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 8px}",
        "#rufus-chat-suggestions button{border:1px solid #888C8C;background:#fff;border-radius:999px;padding:6px 10px;",
        "font-size:0.875rem;cursor:pointer}",
        "#rufus-chat-form{display:flex;gap:8px;padding:12px 16px;border-top:1px solid #D5D9D9}",
        "#rufus-chat-form textarea{flex:1;resize:none;font:inherit;padding:8px;border:1px solid #888C8C;border-radius:8px}",
        "#rufus-chat-form button{background:#FF9900;border:0;border-radius:8px;padding:0 16px;font:600 1rem sans-serif;cursor:pointer}",
        "#rufus-chat-panel button:focus-visible,#rufus-chat-button:focus-visible,#rufus-chat-form textarea:focus-visible",
        "{outline:3px solid #0F1111;outline-offset:2px}",
        ".rufus-visually-hidden{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}",
    ].join("");
    doc.head.appendChild(style);

    const button = doc.createElement("button");
    button.id = "rufus-chat-button";
    button.type = "button";
    button.innerHTML = RUFUS_ICON_SVG;  // fixed markup defined above, no user data
    button.setAttribute("aria-label", CHAT_BUTTON_LABEL);
    button.title = CHAT_BUTTON_LABEL;
    button.setAttribute("aria-controls", "rufus-chat-panel");
    button.setAttribute("aria-expanded", "false");

    const panel = doc.createElement("section");
    panel.id = "rufus-chat-panel";
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-labelledby", "rufus-chat-title");

    const header = doc.createElement("header");
    const title = doc.createElement("h2");
    title.id = "rufus-chat-title";
    title.textContent = "T Levels helper";
    const actions = doc.createElement("div");
    const newChat = doc.createElement("button");
    newChat.type = "button";
    newChat.textContent = "New chat";
    const close = doc.createElement("button");
    close.type = "button";
    close.textContent = "Close";
    actions.append(newChat, doc.createTextNode(" "), close);
    header.append(title, actions);

    const log = doc.createElement("div");
    log.id = "rufus-chat-log";
    log.setAttribute("role", "log");
    log.setAttribute("aria-live", "polite");

    const suggestions = doc.createElement("div");
    suggestions.id = "rufus-chat-suggestions";

    const form = doc.createElement("form");
    form.id = "rufus-chat-form";
    const label = doc.createElement("label");
    label.className = "rufus-visually-hidden";
    label.setAttribute("for", "rufus-chat-input");
    label.textContent = "Your question";
    const input = doc.createElement("textarea");
    input.id = "rufus-chat-input";
    input.rows = 2;
    input.maxLength = CHAT_LIMITS.maxQuestionChars;
    input.placeholder = "Ask a question";
    const send = doc.createElement("button");
    send.type = "submit";
    send.textContent = "Send";
    form.append(label, input, send);

    panel.append(header, log, suggestions, form);
    doc.body.append(panel, button);

    let history = [];
    let busy = false;

    function addMessage(className, text) {
        const p = doc.createElement("p");
        p.className = className;
        p.textContent = text;  // never innerHTML: replies are shown as text
        log.appendChild(p);
        log.scrollTop = log.scrollHeight;
        return p;
    }

    function reset() {
        history = [];
        log.replaceChildren();
        addMessage("rufus-assistant", CHAT_WELCOME);
        addMessage("rufus-note", "Answers can be wrong. Check important details on TLevels.gov.uk.");
        suggestions.replaceChildren();
        CHAT_SUGGESTIONS.forEach(function (text) {
            const chip = doc.createElement("button");
            chip.type = "button";
            chip.textContent = text;
            chip.addEventListener("click", function () { ask(text); });
            suggestions.appendChild(chip);
        });
    }

    async function ask(question) {
        question = question.trim();
        if (!question || busy) return;
        busy = true;
        send.disabled = true;
        suggestions.replaceChildren();
        addMessage("rufus-user", question);
        input.value = "";
        const waiting = addMessage("rufus-note", "Thinking...");

        const outgoing = trimHistory(history.concat([{ role: "user", content: question }]), CHAT_LIMITS);
        let result;
        try {
            result = await askChat(outgoing);
        } catch (error) {
            result = { status: "error", reply: "Something went wrong. Check your connection and try again." };
        }
        waiting.remove();
        addMessage("rufus-assistant", result.reply);
        // Only normal answers join the history, so a blocked question is
        // never sent again with later messages.
        if (result.status === "answered") {
            history.push({ role: "user", content: question }, { role: "assistant", content: result.reply });
        }
        busy = false;
        send.disabled = false;
        input.focus();
    }

    function open() {
        panel.hidden = false;
        button.setAttribute("aria-expanded", "true");
        if (!log.childElementCount) reset();
        input.focus();
    }

    function shut() {
        panel.hidden = true;
        button.setAttribute("aria-expanded", "false");
        button.focus();
    }

    button.addEventListener("click", function () { panel.hidden ? open() : shut(); });
    close.addEventListener("click", shut);
    newChat.addEventListener("click", function () { reset(); input.focus(); });
    panel.addEventListener("keydown", function (event) { if (event.key === "Escape") shut(); });
    form.addEventListener("submit", function (event) { event.preventDefault(); ask(input.value); });
    input.addEventListener("keydown", function (event) {
        // Enter sends; Shift+Enter adds a new line.
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); ask(input.value); }
    });
}

if (typeof module !== "undefined") {
    module.exports = { trimHistory: trimHistory, CHAT_LIMITS: CHAT_LIMITS };
} else {
    addChatWidget(document);
}
