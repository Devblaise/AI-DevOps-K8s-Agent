export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="w-full max-w-xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight">
          AI Kubernetes Agent
        </h1>
        <p className="mt-3 text-lg text-gray-600">
          On-demand AI troubleshooting for your clusters.
        </p>

        <button
          type="button"
          disabled
          className="mt-8 cursor-not-allowed rounded-md bg-gray-300 px-5 py-2.5 font-medium text-gray-600"
        >
          Investigate Cluster
        </button>

        <p className="mt-6 text-sm text-gray-500">System Status: Ready</p>
      </div>
    </main>
  );
}
