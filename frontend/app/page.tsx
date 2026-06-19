import { redirect } from "next/navigation";

export default function Home() {
  // The dashboard layout gates auth and bounces logged-out users to /login.
  redirect("/dashboard");
}
