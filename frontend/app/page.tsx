import ChatInterface from "@/components/ChatInterface";

export default function Home() {
  return (
    <main className="h-screen w-screen bg-white flex overflow-hidden text-gray-900 font-sans">
      <ChatInterface />
    </main>
  );
}