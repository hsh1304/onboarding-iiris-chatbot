import React from "react";

function renderWithLinks(text) {
  const urlRegex = /(https?:\/\/[^\s)]+)/gi;
  const parts = text.split(urlRegex);

  return parts.map((part, idx) => {
    if (urlRegex.test(part)) {
      // Reset lastIndex so subsequent tests work correctly
      urlRegex.lastIndex = 0;
      return (
        <a
          key={idx}
          href={part}
          target="_blank"
          rel="noreferrer"
          style={{
            color: "#0ea5e9",
            textDecoration: "underline",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          {part}
        </a>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

export default function ChatMessage({ role, text }) {
  const isUser = role === "user";

  return (
    <div
      style={{
        alignSelf: isUser ? "flex-end" : "flex-start",
        backgroundColor: isUser ? "#2563eb" : "#f3f4f6",
        color: isUser ? "white" : "#111827",
        padding: "8px 12px",
        borderRadius: 12,
        maxWidth: "75%",
        marginBottom: 8,
        whiteSpace: "pre-wrap",
        fontSize: 14,
      }}
    >
      {renderWithLinks(text)}
    </div>
  );
}


