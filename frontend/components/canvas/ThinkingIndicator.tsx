"use client";

import dynamic from "next/dynamic";
import { useThinkingAnimation } from "@/lib/hooks/use-thinking-animation";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

interface ThinkingIndicatorProps {
  lottieData: object | null;
}

export function ThinkingIndicator({ lottieData }: ThinkingIndicatorProps) {
  const thinkingVerb = useThinkingAnimation(true);

  return (
    <div className="mb-8 space-y-3">
      <div className="bg-muted/50 rounded-xl px-4 py-3 w-fit">
        <span className="text-sm text-muted-foreground animate-pulse">
          {thinkingVerb}...
        </span>
      </div>
      {lottieData && (
        <div className="w-10 h-10">
          <Lottie
            animationData={lottieData}
            loop={true}
            style={{ width: "100%", height: "100%" }}
          />
        </div>
      )}
    </div>
  );
}
