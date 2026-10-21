import { SignupForm } from "@/components/signup-form"
import { ThemeLanguageSwitcher } from "@/components/theme-language-switcher"
import { BackToHome } from "@/components/back-to-home"

export default function Page() {
  return (
    <div className="min-h-svh w-full bg-background text-foreground flex items-center justify-center">
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <BackToHome />
        <ThemeLanguageSwitcher />
        <div className="w-full max-w-sm">
          <SignupForm />
        </div>
      </div>
    </div>
  )
}
