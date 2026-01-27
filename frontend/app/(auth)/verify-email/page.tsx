"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { authClient } from "@/lib/auth-client";
import {
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading"
  );

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }

    authClient
      .verifyEmail({ query: { token } })
      .then(({ error }) => {
        setStatus(error ? "error" : "success");
      })
      .catch(() => {
        setStatus("error");
      });
  }, [token]);

  return (
    <>
      <CardHeader className="text-center">
        <CardTitle className="text-xl">
          {status === "loading" && "Verifying..."}
          {status === "success" && "Email verified"}
          {status === "error" && "Verification failed"}
        </CardTitle>
        <CardDescription>
          {status === "loading" && "Please wait while we verify your email."}
          {status === "success" &&
            "Your email has been verified. You can now sign in."}
          {status === "error" &&
            "This verification link is invalid or has expired."}
        </CardDescription>
      </CardHeader>
      {status !== "loading" && (
        <CardFooter className="justify-center">
          <Link href="/login" className="text-sm text-foreground hover:underline">
            Go to sign in
          </Link>
        </CardFooter>
      )}
    </>
  );
}
