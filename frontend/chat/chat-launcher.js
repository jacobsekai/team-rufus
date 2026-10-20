// Adds an "Ask about T Levels" button to the page that opens the Team Rufus
// chat agent in Amazon Quick in a new tab.
//
// Include on every page, after config.js:
//   <script src="/chat/config.js"></script>
//   <script src="/chat/chat-launcher.js" defer></script>
//
// Why a link and not an embedded chat window: Amazon's internal Quick only
// allows embedding on Amazon-owned domains with a completed AppSec review,
// which this prototype's cloudfront.net address does not have.

// Returns the agent link if it is safe to use, otherwise null.
function chatAgentUrl(config) {
    if (!config || typeof config.agentUrl !== "string" || config.agentUrl === "") {
        return null;
    }
    let url;
    try {
        url = new URL(config.agentUrl);
    } catch (error) {
        return null;
    }
    // Only open Amazon Quick, never an arbitrary site, even if the config is
    // edited by mistake.
    const host = url.hostname;
    if (url.protocol !== "https:" || !(host === "aws.amazon.com" || host.endsWith(".aws.amazon.com"))) {
        return null;
    }
    return url.href;
}

function addChatLauncher(doc, config) {
    const href = chatAgentUrl(config);
    if (!href || doc.getElementById("rufus-chat-launcher")) {
        return null;
    }
    const link = doc.createElement("a");
    link.id = "rufus-chat-launcher";
    link.href = href;
    link.target = "_blank";
    // The new tab gets no access to this page, and Quick is not told which
    // page the visitor came from.
    link.rel = "noopener noreferrer";
    link.textContent = "Ask about T Levels";
    link.setAttribute("aria-label", "Ask about T Levels (opens the Amazon Quick chat assistant in a new tab)");
    // Minimal styling so the button works on unstyled pages; the frontend
    // team can override it with #rufus-chat-launcher in their stylesheet.
    link.style.cssText = [
        "position:fixed", "right:24px", "bottom:24px", "z-index:1000",
        "padding:14px 20px", "border-radius:999px", "background:#FF9900",
        "color:#0F1111", "font:600 16px/1.2 sans-serif", "text-decoration:none",
        "box-shadow:0 2px 8px rgba(0,0,0,0.25)",
    ].join(";");
    doc.body.appendChild(link);
    return link;
}

if (typeof module !== "undefined") {
    module.exports = { chatAgentUrl: chatAgentUrl, addChatLauncher: addChatLauncher };
} else {
    addChatLauncher(document, window.RUFUS_CHAT);
}
