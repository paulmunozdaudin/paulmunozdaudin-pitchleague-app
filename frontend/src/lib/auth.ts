import NextAuth from "next-auth";
import type { Provider } from "next-auth/providers";
import Credentials from "next-auth/providers/credentials";
import Discord from "next-auth/providers/discord";
import Google from "next-auth/providers/google";
import { SignJWT } from "jose";

const secret = new TextEncoder().encode(process.env.NEXTAUTH_SECRET ?? "dev-secret-change-me");

// Optional: only wired in if APPLE_CLIENT_ID/SECRET are set — Apple Sign In
// requires a paid Apple Developer account and a generated JWT client
// secret, so it's off by default. See docs/ARCHITECTURE.md#auth.
const providers: Provider[] = [
  Google({ clientId: process.env.GOOGLE_CLIENT_ID, clientSecret: process.env.GOOGLE_CLIENT_SECRET }),
  Discord({ clientId: process.env.DISCORD_CLIENT_ID, clientSecret: process.env.DISCORD_CLIENT_SECRET }),
];

// Temporary, explicitly opt-in demo login — no real identity check, just a
// display name. Only registered when ENABLE_DEMO_LOGIN=true, so it's a
// deliberate deployment choice, never an accidental default. Meant to let
// people try the product before Google/Discord OAuth apps are set up; turn
// it off (unset the env var) once real sign-in is configured. See
// docs/DEPLOYMENT.md#modo-demo.
if (process.env.ENABLE_DEMO_LOGIN === "true") {
  providers.push(
    Credentials({
      id: "demo",
      name: "Invitado",
      credentials: { name: { label: "Nombre", type: "text" } },
      async authorize(credentials) {
        const name = (credentials?.name as string | undefined)?.trim();
        if (!name || name.length < 2) return null;
        const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
        return { id: `demo-${slug}`, name, email: `${slug}@demo.pitchleague.local` };
      },
    })
  );
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  session: { strategy: "jwt" },
  pages: { signIn: "/" },
  callbacks: {
    async jwt({ token, account, user }) {
      if (account) {
        token.provider = account.provider;
        // OAuth providers set providerAccountId; the demo Credentials
        // provider doesn't, so fall back to the id `authorize` returned.
        token.providerAccountId = account.providerAccountId ?? user?.id;
      }
      return token;
    },
    async session({ session, token }) {
      const providerAccountId = (token.providerAccountId as string | undefined) ?? token.sub ?? "";
      const provider = (token.provider as string | undefined) ?? "unknown";

      // Mints a second, small, plainly-verifiable JWT for FastAPI — see
      // backend/app/core/security.py for the matching verifier. NextAuth's
      // own session cookie is an internal JWE we deliberately don't expose.
      const backendToken = await new SignJWT({
        email: token.email,
        name: token.name,
        picture: token.picture as string | undefined,
        provider,
      })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject(providerAccountId)
        .setIssuedAt()
        .setExpirationTime("7d")
        .sign(secret);

      session.backendToken = backendToken;
      if (session.user) session.user.id = providerAccountId;
      return session;
    },
  },
});
