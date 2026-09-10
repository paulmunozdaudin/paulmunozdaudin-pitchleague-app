"use client";

import { motion } from "framer-motion";
import { ArrowRight, KeyRound, Trophy } from "lucide-react";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

import { Card } from "@/components/ui/card";

export function OnboardingCTAs() {
  const { status } = useSession();
  const router = useRouter();

  function go(target: "create" | "join") {
    const callbackUrl = `/onboarding/${target}`;
    if (status === "authenticated") {
      router.push(callbackUrl);
    } else {
      signIn(undefined, { callbackUrl });
    }
  }

  return (
    <div className="grid w-full max-w-xl grid-cols-1 gap-4 sm:grid-cols-2">
      <motion.div whileHover={{ y: -4 }} whileTap={{ scale: 0.98 }}>
        <Card
          onClick={() => go("create")}
          className="card-glow group flex h-full cursor-pointer flex-col gap-3 p-6 transition-colors hover:border-primary/50"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/15 text-primary">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">Crear liga</p>
            <p className="text-sm text-muted">Invita a tus amigos con un código en segundos.</p>
          </div>
          <ArrowRight className="mt-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-1 group-hover:text-primary" />
        </Card>
      </motion.div>

      <motion.div whileHover={{ y: -4 }} whileTap={{ scale: 0.98 }}>
        <Card
          onClick={() => go("join")}
          className="group flex h-full cursor-pointer flex-col gap-3 p-6 transition-colors hover:border-accent/50"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent/15 text-accent">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">Unirme con código</p>
            <p className="text-sm text-muted">¿Un amigo ya tiene una liga? Entra con su código.</p>
          </div>
          <ArrowRight className="mt-auto h-4 w-4 text-muted transition-transform group-hover:translate-x-1 group-hover:text-accent" />
        </Card>
      </motion.div>
    </div>
  );
}
