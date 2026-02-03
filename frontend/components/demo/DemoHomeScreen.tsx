"use client";

import Image from "next/image";
import { ArrowUp, Users, AlertCircle, BookOpen, Plus, Clock, ChevronDown } from "lucide-react";

const QUICK_ACTIONS = [
  { label: "Start huddle", icon: Users },
  { label: "Patients needing attention", icon: AlertCircle },
  { label: "Review research", icon: BookOpen },
];

interface DemoHomeScreenProps {
  inputText: string;
  submitted: boolean;
}

export function DemoHomeScreen({ inputText, submitted }: DemoHomeScreenProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 transition-all duration-700 ease-out ${
        submitted ? "opacity-0 scale-[0.97]" : "opacity-100 scale-100"
      }`}
    >
      {/* Avatar + Greeting */}
      <div className="flex flex-col items-center mb-8">
        <div className="mb-4 h-24 w-24 rounded-full overflow-hidden">
          <Image
            src="/brand/doctor-demo.png"
            alt="Dr. Chen"
            width={384}
            height={384}
            className="h-full w-full object-cover"
            unoptimized
          />
        </div>
        <div className="flex items-center gap-3">
          <Image src="/brand/mark-primary.svg" alt="" width={32} height={32} />
          <h2 className="text-2xl md:text-3xl font-light text-foreground">
            Good morning, <span className="font-normal">Dr. Chen</span>
          </h2>
        </div>
      </div>

      {/* Input card */}
      <div className="w-full max-w-xl bg-card rounded-2xl border border-border shadow-sm">
        <div className="px-4 py-4">
          <div className="min-h-[24px] text-foreground whitespace-pre-wrap">
            {inputText || (
              <span className="text-muted-foreground">
                What can I help you with today?
              </span>
            )}
            {inputText && (
              <span className="inline-block w-0.5 h-4 bg-foreground/60 align-text-bottom ml-0.5 animate-pulse" />
            )}
          </div>
        </div>
        <div className="flex items-center justify-between px-4 pb-4">
          <div className="flex items-center gap-1">
            <span className="p-2 rounded-lg text-muted-foreground">
              <Plus className="h-5 w-5" />
            </span>
            <span className="p-2 rounded-lg text-muted-foreground">
              <Clock className="h-5 w-5" />
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-sm text-muted-foreground px-2 py-1">
              GPT-4o
              <ChevronDown className="h-3 w-3" />
            </span>
            <span
              className={`inline-flex items-center justify-center h-8 w-8 rounded-lg transition-colors ${
                inputText
                  ? "bg-primary text-primary-foreground"
                  : "bg-primary/50 text-primary-foreground/50"
              }`}
            >
              <ArrowUp className="h-4 w-4" />
            </span>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap justify-center gap-2 mt-6">
        {QUICK_ACTIONS.map(({ label, icon: Icon }) => (
          <span
            key={label}
            className="flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm text-muted-foreground"
          >
            <Icon className="h-4 w-4" />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
