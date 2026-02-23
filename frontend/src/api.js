export async function askQuestion(question) {
  const resp = await fetch("http://localhost:8001/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Backend error ${resp.status}: ${text}`);
  }

  const data = await resp.json();
  return data.answer || "";
}


