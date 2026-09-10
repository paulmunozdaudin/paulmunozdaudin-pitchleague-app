import "next-auth";

declare module "next-auth" {
  interface Session {
    backendToken?: string;
    user?: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}
