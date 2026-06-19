import { createClient } from "@insforge/sdk";

const baseUrl = process.env.NEXT_PUBLIC_INSFORGE_URL ?? "";
const anonKey = process.env.NEXT_PUBLIC_INSFORGE_ANON_KEY ?? "";

// The anon key is optional: the base URL identifies the project, and authenticated
// database operations use the logged-in user's session. We only pass a key when it is
// a real, non-placeholder value — never ship a privileged key to the browser.
const isRealKey = anonKey.length > 0 && !anonKey.includes("xxxx");

export const insforge = createClient(
  isRealKey ? { baseUrl, anonKey } : { baseUrl },
);

export const insforgeConfigured = baseUrl.length > 0;
