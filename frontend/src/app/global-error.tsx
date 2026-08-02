"use client";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground font-sans antialiased">
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="max-w-md w-full glass-card border border-destructive/30 rounded-2xl p-8 text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h1 className="text-xl font-outfit font-bold mb-2">Unexpected application error</h1>
            <p className="text-sm text-muted-foreground mb-6">
              The application hit a critical error. Please reload to continue.
            </p>
            <button
              onClick={() => reset()}
              className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground px-5 py-2.5 text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              Reload Application
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
