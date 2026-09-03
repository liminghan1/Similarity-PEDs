"use client";

export default function ErrorPage({ error }: { error: Error & { status?: number } }) {
  return (
    <div className="mx-auto max-w-2xl px-4 py-16 text-center">
      <h1 className="text-xl font-semibold text-slate-900">Could not load this page</h1>
      <p className="mt-3 text-slate-600">{error.message}</p>
      <p className="mt-4 text-sm text-slate-500">
        If this mentions the backend API, start it with{" "}
        <code className="rounded bg-slate-100 px-1 py-0.5">make api</code> from the project root
        (requires <code className="rounded bg-slate-100 px-1 py-0.5">make db-up</code> and the
        research pipeline having been run first).
      </p>
    </div>
  );
}
