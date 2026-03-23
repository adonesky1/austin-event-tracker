import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

const allowedEmails = new Set(
  (process.env.ADMIN_ALLOWED_EMAILS ?? "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean)
);

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  session: { strategy: "jwt" },
  pages: { signIn: "/signin" },
  providers: [
    Google({
      allowDangerousEmailAccountLinking: false,
    }),
  ],
  callbacks: {
    async signIn({ profile }) {
      const email = profile?.email?.toLowerCase();
      const emailVerified = profile?.email_verified ?? true;
      if (!email || !emailVerified) {
        return false;
      }
      return allowedEmails.size === 0 || allowedEmails.has(email);
    },
  },
});
