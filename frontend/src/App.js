import "./App.css";
import { useEffect, useState, useRef } from "react";

// Helpers to decide dev vs prod and build base URLs
const isLocalhost =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

// HTTP base:
// - In dev: talk via CRA proxy (HTTP_BASE = "")
// - In prod: same origin as the page (nginx proxies /api/* to backend)
const HTTP_BASE = isLocalhost ? "" : window.location.origin;

function App() {
  const [message, setMessage] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [buttonVariant, setButtonVariant] = useState("A"); // MAB variant
  const [isExtensionMode, setIsExtensionMode] = useState(false);
  const messagesEndRef = useRef(null);

  // Storage key for chat messages
  const STORAGE_KEY = "coursekey-chat-messages";
  
  // Detect if running in extension iframe
  useEffect(() => {
    const inIframe = window.self !== window.top;
    setIsExtensionMode(inIframe);

    // Clear messages on page refresh in extension mode
    // Use sessionStorage to detect if this is a new session (page refresh)
    if (inIframe) {
      try {
        const SESSION_KEY = "coursekey-session-id";
        const currentSessionId = Date.now().toString();
        const lastSessionId = sessionStorage.getItem(SESSION_KEY);

        // If session changed (page refresh), clear chat
        if (!lastSessionId || lastSessionId !== currentSessionId) {
          localStorage.removeItem(STORAGE_KEY);
          setMessages([]);
          sessionStorage.setItem(SESSION_KEY, currentSessionId);
          console.log("🔄 Page refreshed - chat history cleared");
        }
      } catch (err) {
        console.error("Error checking session:", err);
      }
    }
  }, []);

  // Load messages from localStorage on mount
  useEffect(() => {
    const loadMessages = () => {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setMessages(parsed);
            console.log(`📥 Loaded ${parsed.length} messages from storage`);
            return true;
          }
        }
      } catch (err) {
        console.error("Error loading messages from storage:", err);
      }
      return false;
    };

    // Load immediately
    loadMessages();

    // Also try loading after delays (for iframe loading scenarios)
    if (isExtensionMode) {
      const timers = [100, 300, 600].map((delay) =>
        setTimeout(loadMessages, delay)
      );
      return () => timers.forEach((t) => clearTimeout(t));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExtensionMode]); // Only run when extension mode changes

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
      } catch (err) {
        console.error("Error saving messages to storage:", err);
      }
    }
  }, [messages]);

  // Listen for messages from parent (content script) to sync state
  useEffect(() => {
    if (!isExtensionMode) return;

    const handleMessage = (event) => {
      // Security: only accept messages from same origin
      // In extension mode, messages come from parent window
      if (!event.data) return;

      if (event.data.type === "coursekey-sync-messages") {
        const syncMessages = event.data.messages;
        if (Array.isArray(syncMessages)) {
          setMessages(syncMessages);
          console.log(`🔄 Synced ${syncMessages.length} messages from parent`);
        }
      }

      // Respond to message requests by sending current messages
      if (event.data.type === "coursekey-request-messages") {
        // Read current messages from localStorage or state
        try {
          const stored = localStorage.getItem(STORAGE_KEY);
          const currentMessages = stored ? JSON.parse(stored) : [];

          if (window.parent && currentMessages.length > 0) {
            window.parent.postMessage(
              {
                type: "coursekey-send-messages",
                messages: currentMessages,
              },
              "*" // In extension context, we need to use wildcard
            );
            console.log(`📤 Sent ${currentMessages.length} messages to parent`);
          }
        } catch (err) {
          console.error("Error reading messages for sync:", err);
        }
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [isExtensionMode]);

  // Call /api/hello endpoint - handle both standalone and extension modes
  useEffect(() => {
    fetch(`${HTTP_BASE}/api/hello`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.message) setMessage(data.message);
      })
      .catch((err) => console.error("Error fetching /api/hello:", err));
  }, []);

  // Multi-Armed Bandit: Get button variant on component mount
  useEffect(() => {
    fetch(`${HTTP_BASE}/api/bandit/variant`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.variant) {
          setButtonVariant(data.variant);
          console.log(`🎯 MAB: Showing button variant ${data.variant}`);
        } else {
          console.log("🎯 MAB: No variant returned, keeping default");
        }
      })
      .catch((err) =>
        console.error("Error fetching /api/bandit/variant:", err)
      );
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    const userMessage = input.trim();
    if (!userMessage) return;

    // 1) Add user message
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

    // 2) Add placeholder AI message with typing indicator
    setMessages((prev) => [
      ...prev,
      { role: "ai", content: "", isStreaming: true },
    ]);

    setIsStreaming(true);
    setInput("");

    // Track conversion (button click) for Multi-Armed Bandit (only if we have a variant)
    if (buttonVariant) {
      fetch(`${HTTP_BASE}/api/bandit/conversion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variant: buttonVariant }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data && data.variant) {
            console.log(
              `✅ MAB: Conversion recorded for variant ${data.variant}`
            );
          } else {
            console.log("✅ MAB: Conversion recorded (no body)");
          }
        })
        .catch((err) =>
          console.error("Error recording /api/bandit/conversion:", err)
        );
    }

    console.log("📤 Sending REST /api/ask with question:", userMessage);

    // 3) Call REST API /api/ask
    fetch(`${HTTP_BASE}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: userMessage }),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log("📨 REST /api/ask response:", data);

        setMessages((prev) => {
          const updated = [...prev];
          if (updated.length === 0) return updated;

          const lastIdx = updated.length - 1;
          const last = updated[lastIdx];

          if (last.role === "ai") {
            updated[lastIdx] = {
              ...last,
              content: data?.answer ?? "",
              isStreaming: false,
            };
          }
          return updated;
        });
      })
      .catch((err) => {
        console.error("❌ Error calling /api/ask:", err);

        setMessages((prev) => {
          const updated = [...prev];
          if (updated.length === 0) {
            updated.push({
              role: "ai",
              content: "Sorry, I ran into an error while trying to answer that.",
              isStreaming: false,
            });
            return updated;
          }

          const lastIdx = updated.length - 1;
          const last = updated[lastIdx];
          if (last.role === "ai") {
            updated[lastIdx] = {
              ...last,
              content:
                "Sorry, I ran into an error while trying to answer that.",
              isStreaming: false,
            };
          }
          return updated;
        });
      })
      .finally(() => {
        setIsStreaming(false);
      });
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = () => {
    // Clear messages from state
    setMessages([]);
    // Clear messages from localStorage
    try {
      localStorage.removeItem(STORAGE_KEY);
      console.log("🗑️ Started new chat - cleared history");
    } catch (err) {
      console.error("Error clearing chat:", err);
    }
  };

  return (
    <div className={`App ${isExtensionMode ? "extension-mode" : ""}`}>
      <div className="chat-container">
        <div className="chat-header">
          <h1>{message || "CourseKey"}</h1>
          {messages.length > 0 && (
            <button
              className="new-chat-button"
              onClick={startNewChat}
              title="Start new chat"
              aria-label="Start new chat"
            >
              New
            </button>
          )}
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>Start a conversation with CourseKey</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-content">
                {msg.content}
                {msg.isStreaming && !msg.content && (
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-container">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            aria-label="Chat input"
          />
          <button
            className={`send-button send-button-variant-${buttonVariant}`}
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
          >
            {isStreaming ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
