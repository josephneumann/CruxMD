import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CruxMD",
  description: "Clinical intelligence for physicians",
  manifest: "/manifest.webmanifest",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#CC785C" },
    { media: "(prefers-color-scheme: dark)", color: "#191919" },
  ],
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-48x48.png", sizes: "48x48", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
    other: [
      {
        rel: "mask-icon",
        url: "/safari-pinned-tab.svg",
        color: "#CC785C",
      },
    ],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "CruxMD",
  },
  openGraph: {
    type: "website",
    siteName: "CruxMD",
    title: "CruxMD",
    description: "Clinical intelligence for physicians",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "CruxMD - Clinical Intelligence",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "CruxMD",
    description: "Clinical intelligence for physicians",
    images: ["/og-image-twitter.png"],
  },
  other: {
    "msapplication-TileColor": "#CC785C",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
