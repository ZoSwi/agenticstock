import { Suspense } from "react";

import { ChatClient } from "@/app/chat/chat-client";
import { Shell } from "@/components/Shell";
import { Card } from "@/components/ui/Card";

export default function ChatPage() {
  return (
    <Shell>
      <Suspense
        fallback={
          <Card>
            <div className="text-sm text-black/60 dark:text-white/60">Loading chat...</div>
          </Card>
        }
      >
        <ChatClient />
      </Suspense>
    </Shell>
  );
}
