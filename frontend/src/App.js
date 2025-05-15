import React, { useState, useEffect, useRef } from "react";

const BACKEND_WS_URL = process.env.REACT_APP_BACKEND_WS_URL || "ws://localhost:8000/ws/chat";
const BACKEND_API_URL = process.env.REACT_APP_BACKEND_API_URL || "http://localhost:8000";

function App() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [roomId, setRoomId] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    ws.current = new window.WebSocket(BACKEND_WS_URL);
    ws.current.onopen = () => setConnected(true);
    ws.current.onclose = () => setConnected(false);
    ws.current.onmessage = (event) => {
      // Optionally handle incoming messages if backend supports push
    };
    return () => ws.current && ws.current.close();
  }, []);

  // Poll messages if roomId exists
  useEffect(() => {
    let interval;
    if (roomId) {
      interval = setInterval(async () => {
        const res = await fetch(`${BACKEND_API_URL}/chat/${roomId}/messages`);
        const data = await res.json();
        setMessages(data.messages.map(m => m.split(":").slice(1).join(":")));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [roomId]);

  // Get roomId from backend after matching (simulate for now)
  useEffect(() => {
    if (connected) {
      // Simulate waiting for backend to assign roomId
      setTimeout(async () => {
        // This would be handled by backend push in a real app
        // For now, poll Redis or ask backend for user_room
        // Here we fake a roomId for demo
        setRoomId("demo-room-id");
      }, 2000);
    }
  }, [connected]);

  const sendMessage = () => {
    if (input && ws.current && connected) {
      ws.current.send(input);
      setInput("");
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "40px auto", padding: 20, border: "1px solid #ccc", borderRadius: 8, background: "#fff" }}>
      <h2 style={{ textAlign: "center" }}>Anonymous Chat</h2>
      {!connected && <div>Chatga ulanish...</div>}
      {connected && (
        <>
          <div style={{ minHeight: 200, maxHeight: 300, overflowY: "auto", border: "1px solid #eee", marginBottom: 10, padding: 10 }}>
            {messages.length === 0 && <div>Hozircha xabar yo'q...</div>}
            {messages.map((msg, idx) => (
              <div key={idx} style={{ padding: "4px 0" }}>{msg}</div>
            ))}
          </div>
          <div style={{ display: "flex" }}>
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              style={{ flex: 1, marginRight: 8 }}
              placeholder="Xabar yozing..."
              onKeyDown={e => e.key === "Enter" && sendMessage()}
            />
            <button onClick={sendMessage} disabled={!input}>Yuborish</button>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
