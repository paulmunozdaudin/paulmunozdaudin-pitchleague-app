"use client";

import { signIn } from "next-auth/react";

import { Button } from "@/components/ui/button";

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4">
      <path
        fill="currentColor"
        d="M21.8 12.23c0-.71-.06-1.4-.18-2.05H12v3.88h5.5a4.7 4.7 0 0 1-2.04 3.09v2.56h3.3c1.93-1.78 3.04-4.4 3.04-7.48Z"
      />
      <path
        fill="currentColor"
        d="M12 22c2.76 0 5.08-.92 6.77-2.49l-3.3-2.56c-.92.62-2.09.98-3.47.98-2.67 0-4.93-1.8-5.74-4.23H2.86v2.65A10 10 0 0 0 12 22Z"
      />
      <path fill="currentColor" d="M6.26 13.7a5.99 5.99 0 0 1 0-3.8V7.25H2.86a10 10 0 0 0 0 9.1l3.4-2.65Z" />
      <path
        fill="currentColor"
        d="M12 5.98c1.5 0 2.84.52 3.9 1.53l2.92-2.92C16.98 2.98 14.7 2 12 2a10 10 0 0 0-9.14 5.25l3.4 2.65C7.07 7.77 9.33 5.98 12 5.98Z"
      />
    </svg>
  );
}

function DiscordIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
      <path d="M20.3 5.3A17.6 17.6 0 0 0 15.8 4c-.2.4-.5.9-.6 1.3a16.3 16.3 0 0 0-4.4 0c-.2-.4-.4-.9-.6-1.3-1.6.3-3.1.8-4.5 1.4C2.9 9 2.2 12.6 2.5 16.2a17.6 17.6 0 0 0 5.3 2.7c.4-.6.8-1.2 1.1-1.9-.6-.2-1.2-.5-1.7-.9l.4-.3c3.3 1.5 6.8 1.5 10 0l.4.3c-.6.4-1.2.7-1.8.9.3.7.7 1.3 1.1 1.9a17.5 17.5 0 0 0 5.3-2.7c.4-4.2-.7-7.7-2.3-10.9ZM9.7 14c-1 0-1.8-.9-1.8-2s.8-2 1.8-2c1 0 1.8.9 1.8 2s-.8 2-1.8 2Zm6.6 0c-1 0-1.8-.9-1.8-2s.8-2 1.8-2c1 0 1.8.9 1.8 2s-.8 2-1.8 2Z" />
    </svg>
  );
}

export function AuthButtons({ callbackUrl = "/leagues" }: { callbackUrl?: string }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Button size="lg" variant="secondary" className="flex-1" onClick={() => signIn("google", { callbackUrl })}>
        <GoogleIcon /> Continuar con Google
      </Button>
      <Button size="lg" variant="secondary" className="flex-1" onClick={() => signIn("discord", { callbackUrl })}>
        <DiscordIcon /> Continuar con Discord
      </Button>
    </div>
  );
}
