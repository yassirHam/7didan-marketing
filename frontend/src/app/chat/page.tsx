import type { Metadata } from "next";
import { Suspense } from "react";
import { ChatApp } from "@/components/chat/ChatApp";

export const metadata: Metadata = { title: "Assistant" };

export default function ChatPage() {
  // useSearchParams (the ?q= starter question) is read on the client, inside this boundary.
  return (
    <Suspense fallback={<div className="h-dvh bg-mist" />}>
      <ChatApp />
    </Suspense>
  );
}
