import { redirect } from "next/navigation";

/**
 * Root page - redirects to the chat interface.
 *
 * The chat page is the primary entry point for the application.
 */
export default function Home() {
  redirect("/chat");
}
