import React, { useState, useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import { askQuestion } from "./api";

function App() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;

    setError("");
    setLoading(true);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);

    try {
      const answer = await askQuestion(q);
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (err) {
      console.error(err);
      setError("Failed to reach backend. Is it running on port 8000?");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Sorry, something went wrong while contacting the backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0f172a",
        color: "white",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 720,
          height: "80vh",
          backgroundColor: "#020617",
          borderRadius: 16,
          boxShadow: "0 20px 45px rgba(15,23,42,0.8)",
          display: "flex",
          flexDirection: "column",
          padding: 16,
          boxSizing: "border-box",
        }}
      >
        <header
          style={{
            padding: "4px 8px 12px",
            borderBottom: "1px solid rgba(148,163,184,0.4)",
            marginBottom: 8,
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: 20,
              fontWeight: 600,
            }}
          >
            Onboarding Q&A
          </h1>
          <p
            style={{
              margin: "4px 0 0",
              fontSize: 12,
              color: "#9ca3af",
            }}
          >
            Ask onboarding and access-related questions (Confluence, Jira,
            GitHub, Vault, etc.).
          </p>
        </header>

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "4px 4px 8px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          {messages.length === 0 && (
            <div
              style={{
                marginTop: 12,
                fontSize: 13,
                color: "#9ca3af",
              }}
            >
              Try questions like:
              <br />
              - How do I get Confluence access?
              <br />
              - How do I get Jira access?
              <br />
              - How do I get GitHub access?
            </div>
          )}

          {messages.map((m, idx) => (
            <ChatMessage key={idx} role={m.role} text={m.text} />
          ))}
          {loading && (
            <div
              style={{
                alignSelf: "flex-start",
                backgroundColor: "#f3f4f6",
                color: "#111827",
                padding: "8px 12px",
                borderRadius: 12,
                fontSize: 14,
              }}
            >
              Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            marginTop: 8,
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            type="text"
            placeholder="Type your question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: 999,
              border: "1px solid rgba(148,163,184,0.5)",
              backgroundColor: "#020617",
              color: "white",
              fontSize: 14,
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              padding: "10px 16px",
              borderRadius: 999,
              border: "none",
              background:
                "linear-gradient(135deg, #22c55e 0%, #16a34a 40%, #0ea5e9 100%)",
              color: "white",
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "default" : "pointer",
              opacity: loading || !input.trim() ? 0.6 : 1,
              transition: "transform 0.08s ease, box-shadow 0.08s ease",
              boxShadow: loading
                ? "none"
                : "0 8px 20px rgba(34,197,94,0.45)",
            }}
          >
            {loading ? "Thinking..." : "Ask"}
          </button>
        </form>

        {error && (
          <div
            style={{
              marginTop: 6,
              fontSize: 12,
              color: "#fecaca",
            }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;


