import Link from "next/link";
import Image from "next/image";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm">
        <div className="bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm">
          <div className="flex justify-center pt-6">
            <Link href="/">
              <Image
                src="/brand/mark-primary.svg"
                alt="CruxMD"
                width={48}
                height={48}
                priority
              />
            </Link>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
