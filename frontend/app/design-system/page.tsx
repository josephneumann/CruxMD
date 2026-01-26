import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Design System | CruxMD",
  description: "CruxMD Design System - Colors, components, and brand guidelines",
};

export default function DesignSystemPage() {
  const figmaUrl =
    "https://www.figma.com/embed?embed_host=share&url=https%3A%2F%2Fwww.figma.com%2Fproto%2FPUCf3fGsi7gFBUbSDQupsF%2FCruxMD-Design-System%3Fnode-id%3D1-2";

  return (
    <div className="h-screen w-full">
      <iframe
        src={figmaUrl}
        className="h-full w-full border-0"
        allowFullScreen
      />
    </div>
  );
}
