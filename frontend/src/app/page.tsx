import { Trophy, Users, Zap } from "lucide-react";

import { OnboardingCTAs } from "@/components/onboarding/OnboardingCTAs";

const FEATURES = [
  { icon: Users, title: "Ligas privadas", body: "Solo tú y tus amigos. Chat, ranking e historial propios." },
  { icon: Zap, title: "Cuotas reales", body: "El mismo mercado que usan las casas de apuestas, sin dinero real." },
  { icon: Trophy, title: "Empieza cada semana", body: "Presupuesto nuevo cada jornada. Un mal resultado nunca te elimina." },
];

export default function LandingPage() {
  return (
    <main className="relative flex min-h-screen flex-col items-center overflow-hidden px-6 py-16 sm:py-24">
      <div
        className="pointer-events-none absolute inset-x-0 -top-40 h-[560px] bg-aurora blur-3xl"
        aria-hidden
      />

      <div className="relative z-10 flex w-full max-w-2xl flex-col items-center text-center">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface/60 px-4 py-1.5 text-xs font-medium text-muted animate-fade-up">
          <span className="h-1.5 w-1.5 rounded-full bg-accent" /> Temporada 1 ya disponible
        </span>

        <h1
          className="text-balance text-4xl font-bold tracking-tight sm:text-6xl animate-fade-up"
          style={{ animationDelay: "60ms" }}
        >
          Compite contra tus amigos con{" "}
          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            cuotas reales
          </span>
        </h1>

        <p
          className="mt-5 max-w-lg text-balance text-lg text-muted animate-fade-up"
          style={{ animationDelay: "120ms" }}
        >
          Crea una liga privada, reparte un presupuesto virtual cada jornada y descubre quién de tu grupo
          predice mejor. Sin dinero real. Sin excusas.
        </p>

        <div className="mt-10 animate-fade-up" style={{ animationDelay: "180ms" }}>
          <OnboardingCTAs />
        </div>

        <p className="mt-6 text-xs text-muted animate-fade-up" style={{ animationDelay: "220ms" }}>
          Menos de un minuto para empezar a jugar.
        </p>
      </div>

      <div className="relative z-10 mt-20 grid w-full max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-2xl border border-border bg-surface/50 p-5 text-left">
            <Icon className="mb-3 h-5 w-5 text-primary" />
            <p className="font-medium">{title}</p>
            <p className="mt-1 text-sm text-muted">{body}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
