import NextAuth from "next-auth";
import Discord from "next-auth/providers/discord";
import Google from "next-auth/providers/google";
import { SignJWT } from "jose";

const secret = new TextEncoder().encode(process.env.NEXTAUTH_SECRET ?? "dev-secret-change-me");

// Optional: only wired in if APPLE_CLIENT_ID/SECRET are set — Apple Sign In
// requires a paid Apple Developer account and a generated JWT client
// secret, so it's off by default. See docs/ARCHITECTURE.md#auth.
const providers = [
  Google({ clientId: process.env.GOOGLE_CLIENT_ID, clientSecret: process.env.GOOGLE_CLIENT_SECRET }),
  Discord({ clientId: process.env.DISCORD_CLIENT_ID, clientSecret: process.env.DISCORD_CLIENT_SECRET }),
];

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers,
  session: { strategy: "jwt" },
  pages: { signIn: "/" },
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.provider = account.provider;
        token.providerAccountId = account.providerAccountId;
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
