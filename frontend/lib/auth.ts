import { betterAuth } from "better-auth";
import { bearer } from "better-auth/plugins";
import { Pool } from "pg";
import { Resend } from "resend";

const resend = process.env.RESEND_API_KEY
  ? new Resend(process.env.RESEND_API_KEY)
  : null;

const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

export const auth = betterAuth({
  baseURL: appUrl,
  trustedOrigins: [appUrl],
  database: new Pool({
    connectionString: process.env.DATABASE_URL_SYNC,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  }),
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: true,
    sendResetPassword: async ({ user, url }) => {
      if (resend) {
        await resend.emails.send({
          from: "CruxMD <noreply@cruxmd.com>",
          to: user.email,
          subject: "Reset your CruxMD password",
          html: `<p>Click <a href="${url}">here</a> to reset your password.</p>`,
        });
      } else {
        console.log(`[Auth] Password reset requested for ${user.email} (configure RESEND_API_KEY to send)`);
      }
    },
  },
  emailVerification: {
    sendOnSignUp: true,
    sendVerificationEmail: async ({ user, url }) => {
      if (resend) {
        await resend.emails.send({
          from: "CruxMD <noreply@cruxmd.com>",
          to: user.email,
          subject: "Verify your CruxMD email",
          html: `<p>Click <a href="${url}">here</a> to verify your email address.</p>`,
        });
      } else {
        console.log(`[Auth] Verification email for ${user.email} (configure RESEND_API_KEY to send)`);
      }
    },
  },
  plugins: [bearer()],
});
