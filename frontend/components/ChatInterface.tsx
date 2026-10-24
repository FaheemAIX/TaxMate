"use client";

import { useState, useRef, useEffect } from "react";
import TaxReceiptCard from "./TaxReceiptCard";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  role: "user" | "ai";
  content: string;
  sources?: { index: number; source: string; content: string }[];
  calculation?: any;
};

type Session = {
  id: string;
  title: string;
};

export default function ChatInterface() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [chats, setChats] = useState<Record<string, Message[]>>({});
  
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize a session ID silently on load, but wait before displaying in sidebar
  useEffect(() => {
    setActiveSessionId(crypto.randomUUID());
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chats, activeSessionId]);

  const startNewSession = () => {
    setActiveSessionId(crypto.randomUUID());
    setInput("");
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeSessionId || isLoading) return;

    const userMessage = input;
    setInput("");

    const isNewSession = !sessions.some((s) => s.id === activeSessionId);
    if (isNewSession) {
      setSessions((prev) => [
        {
          id: activeSessionId,
          title: userMessage.slice(0, 30) + (userMessage.length > 30 ? "..." : ""),
        },
        ...prev,
      ]);
    }

    // 1. Append User message
    setChats((prev) => ({
      ...prev,
      [activeSessionId]: [...(prev[activeSessionId] || []), { role: "user", content: userMessage }],
    }));

    // 2. Append empty placeholder AI message
    setChats((prev) => ({
      ...prev,
      [activeSessionId]: [
        ...prev[activeSessionId],
        { role: "ai", content: "", sources: [], calculation: null },
      ],
    }));

    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: activeSessionId, query: userMessage }),
      });

      if (!response.ok || !response.body) throw new Error("API stream error");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";

          for (const part of parts) {
            if (part.startsWith("data: ")) {
              try {
                const data = JSON.parse(part.substring(6));

                setChats((prev) => {
                  const currentChat = prev[activeSessionId];
                  if (!currentChat || currentChat.length === 0) return prev;
                  const lastIdx = currentChat.length - 1;
                  const updatedChat = [...currentChat];

                  if (data.type === "metadata") {
                    updatedChat[lastIdx] = {
                      ...updatedChat[lastIdx],
                      calculation: data.calculation,
                      sources: data.sources,
                    };
                  } else if (data.type === "chunk") {
                    updatedChat[lastIdx] = {
                      ...updatedChat[lastIdx],
                      content: updatedChat[lastIdx].content + data.content,
                    };
                  }

                  return { ...prev, [activeSessionId]: updatedChat };
                });
              } catch (err) {
                console.error("Error parsing stream chunk:", err, part);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      setChats((prev) => {
        const currentChat = prev[activeSessionId];
        if (!currentChat || currentChat.length === 0) return prev;
        const lastIdx = currentChat.length - 1;
        const updatedChat = [...currentChat];
        updatedChat[lastIdx] = { ...updatedChat[lastIdx], content: "Error connecting to stream." };
        return { ...prev, [activeSessionId]: updatedChat };
      });
    } finally {
      setIsLoading(false);
    }
  };

  const activeMessages = chats[activeSessionId] || [];

  return (
    <div className="flex h-full w-full bg-white relative">
      
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0">
        <div className="p-4">
          <button 
            onClick={startNewSession}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          {sessions.length > 0 && (
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2 mt-4">
              Recent Sessions
            </p>
          )}
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setActiveSessionId(session.id)}
              className={`w-full text-left px-3 py-3 rounded-lg text-sm truncate transition-colors cursor-pointer ${
                activeSessionId === session.id ? "bg-slate-800 text-white" : "hover:bg-slate-800/50"
              }`}
            >
              {session.title}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <header className="sticky top-0 z-10 flex items-center px-6 py-4 bg-white/80 backdrop-blur-md border-b border-gray-100">
          <h1 className="text-xl font-bold text-gray-800">
            TaxMate <span className="text-blue-600">AI</span>
          </h1>
        </header>

        <div className="flex-1 overflow-y-auto pb-32">
          {activeMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-800 px-4">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                <span className="text-3xl">🏛️</span>
              </div>
              <h2 className="text-2xl md:text-3xl font-semibold mb-2">How can I help with your taxes?</h2>
              <p className="text-gray-500">Ask about FBR rules or calculate your liability.</p>
            </div>
          ) : (
            <div className="w-full flex flex-col">
              {activeMessages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`w-full ${msg.role === "user" ? "bg-white" : "bg-gray-50"} border-b border-gray-100`}
                >
                  <div className="max-w-3xl mx-auto p-6 flex gap-4 md:gap-6">
                    {/* Role Avatar */}
                    <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center font-bold text-white text-sm ${msg.role === "user" ? "bg-gray-800" : "bg-blue-600"}`}>
                      {msg.role === "user" ? "U" : "AI"}
                    </div>

                    <div className="flex-1 overflow-hidden">
                      {/* 1. Tax Receipt Card renders on TOP */}
                      {msg.calculation && (
                        <div className="mb-4">
                          <TaxReceiptCard data={msg.calculation} />
                        </div>
                      )}

                      {/* 2. Markdown text without redundant whitespace wrappers */}
                      <div className="prose prose-blue max-w-none text-gray-800 prose-p:my-1.5 prose-headings:my-2 prose-li:my-0.5 leading-relaxed">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            a: ({ node, href, title, children, ...props }) => {
                              if (href === "#") {
                                return (
                                  <sup 
                                    className="inline-flex items-center justify-center min-w-[16px] h-4 ml-1 px-1 text-[10px] font-bold text-white bg-blue-500 rounded hover:bg-blue-600 cursor-help transition-colors align-super"
                                    title={title || "View Source"}
                                  >
                                    {children}
                                  </sup>
                                );
                              }
                              return (
                                <a href={href} title={title} className="text-blue-600 underline" {...props}>
                                  {children}
                                </a>
                              );
                            }
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>

                      {/* 3. Bottom Sources Section */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-gray-200">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Sources</p>
                          <div className="flex flex-wrap gap-2">
                            {msg.sources.map((src, sIdx) => (
                              <span 
                                key={sIdx} 
                                className="inline-block bg-white text-gray-600 text-xs px-2 py-1 rounded border border-gray-200 shadow-xs"
                                title={src.content}
                              >
                                [{src.index}] {src.source}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="w-full bg-gray-50 border-b border-gray-100">
                  <div className="max-w-3xl mx-auto p-6 flex gap-4 md:gap-6">
                    <div className="w-8 h-8 rounded-full bg-blue-600 shrink-0 flex items-center justify-center text-white text-sm font-bold">
                      AI
                    </div>
                    <div className="flex items-center space-x-2 h-8">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="absolute bottom-0 w-full bg-linear-to-t from-white via-white to-transparent pt-6 pb-6 px-4">
          <div className="max-w-3xl mx-auto">
            <form 
              onSubmit={sendMessage} 
              className="relative flex items-center shadow-lg border border-gray-300 rounded-2xl bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent overflow-hidden"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message TaxMate..."
                className="w-full py-4 pl-4 pr-16 outline-none text-gray-800 bg-transparent"
                disabled={isLoading}
              />
              <button 
                type="submit" 
                disabled={isLoading || !input.trim()} 
                className="absolute right-2 p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 transition-colors cursor-pointer disabled:cursor-not-allowed"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
                </svg>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}