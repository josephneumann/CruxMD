"use client";

import { useState } from "react";
import Link from "next/link";
import { signUp } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function RegisterPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const { error: signUpError } = await signUp.email({
      name: `${firstName} ${lastName}`.trim(),
      email,
      password,
    });

    if (signUpError) {
      setError(signUpError.message || "Registration failed");
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  };

  if (success) {
    return (
      <>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Check your email</CardTitle>
          <CardDescription>
            We sent a verification link to <strong>{email}</strong>. Click it to
            activate your account.
          </CardDescription>
        </CardHeader>
        <CardFooter className="justify-center">
          <Link href="/login" className="text-sm text-foreground hover:underline">
            Back to sign in
          </Link>
        </CardFooter>
      </>
    );
  }

  return (
    <>
      <CardHeader className="text-center">
        <CardTitle className="text-xl">Create an account</CardTitle>
        <CardDescription>Get started with CruxMD</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">First name</Label>
              <Input
                id="firstName"
                type="text"
                placeholder="Jane"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                autoComplete="given-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last name</Label>
              <Input
                id="lastName"
                type="text"
                placeholder="Smith"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                autoComplete="family-name"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Creating account..." : "Create account"}
          </Button>
          <p className="text-sm text-muted-foreground text-center">
            Already have an account?{" "}
            <Link href="/login" className="text-foreground hover:underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </>
  );
}
