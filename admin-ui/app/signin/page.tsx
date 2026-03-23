import { signIn } from "@/auth";

export default function SignInPage() {
  return (
    <section className="signin-card">
      <p className="eyebrow">Austin Event Tracker</p>
      <h1>Admin sign-in</h1>
      <p className="helper-text">
        Use an approved Google account. Access is limited to emails listed in the Vercel
        environment.
      </p>
      <form
        action={async () => {
          "use server";
          await signIn("google", { redirectTo: "/" });
        }}
      >
        <button className="primary-button" type="submit">
          Continue with Google
        </button>
      </form>
    </section>
  );
}
