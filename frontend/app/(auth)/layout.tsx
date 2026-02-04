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
        <div className="relative overflow-hidden rounded-xl border shadow-sm">
          {/* Forest background */}
          <Image
            src="/brand/backgrounds/forest-login.png"
            alt=""
            fill
            className="object-cover object-center"
            priority
          />
          <div className="absolute inset-0 bg-card/85 dark:bg-card/90" />

          {/* Content */}
          <div className="relative z-10 flex flex-col gap-6 py-6 text-card-foreground">
            <div className="flex justify-center pt-6">
              <Link href="/">
                <Image
                  src="/brand/logos/mark-primary.svg"
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
    </div>
  );
}
