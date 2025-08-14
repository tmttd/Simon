// insuLin_Guide/frontend/src/App.jsx

import React, { useState } from 'react';
import './App.css'; // 기본 CSS도 곧 수정할 예정입니다.

function App() {
  const [messages, setMessages] = useState([]); // 대화 기록을 저장할 배열
  const [input, setInput] = useState(''); // 사용자의 현재 입력 값을 저장

  // 메시지를 보내는 함수
  const sendMessage = async () => {
    if (!input.trim()) return; // 입력이 비어있으면 아무것도 하지 않음

    // 사용자의 메시지를 대화 기록에 추가
    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);

    // 여기서 실제 API를 호출합니다.
    try {
      // Django 백엔드 API 주소 (포트 8000번)
      const response = await fetch('http://localhost:8000/chat/ask/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          thread_id: 'test-thread-react', // 우선 고정된 ID 사용
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // AI의 응답을 대화 기록에 추가
      const aiMessage = { sender: 'ai', text: data.response };
      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error("API 호출 중 오류 발생:", error);
      // 에러 메시지를 화면에 표시
      const errorMessage = { sender: 'ai', text: '죄송합니다. 서버와 통신 중 오류가 발생했습니다.' };
      setMessages(prev => [...prev, errorMessage]);
    }

    setInput(''); // 입력창 비우기
  };

  return (
    <div className="App">
      <div className="chat-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            <p>{msg.text}</p>
          </div>
        ))}
      </div>  
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button onClick={sendMessage}>전송</button>
      </div>
    </div>
  );
}

export default App;