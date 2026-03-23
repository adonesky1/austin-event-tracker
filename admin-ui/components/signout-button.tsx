import { signOut } from "@/auth";

export function SignOutButton() {
  return (
    <form
      action={async () => {
        "use server";
        await signOut({ redirectTo: "/signin" });
      }}
    >
      <button className="secondary-button" type="submit">
        Sign out
      </button>
    </form>
  );
}
