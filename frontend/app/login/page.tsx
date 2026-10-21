"use client"

import { Suspense, useState, useEffect } from "react"
import Image from "next/image"
import { useSearchParams } from "next/navigation"
import { useTheme } from "next-themes"
import { motion, AnimatePresence } from "motion/react"
import { TextGenerateEffect } from "@/components/ui/text-generate-effect"
import { TextAnimate } from "@/components/ui/text-animate"
import { ThemeLanguageSwitcher } from "@/components/theme-language-switcher"
import { BackToHome } from "@/components/back-to-home"
import { Skeleton } from "@/components/ui/skeleton"

import { LoginForm, ForgotPasswordForm } from "@/components/login-form"
import { RegisterForm } from "@/components/register-form"
import { cn } from "@/lib/utils"

type FormMode = "login" | "register" | "forgot-password"

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-svh items-center justify-center">
        <Skeleton className="h-[400px] w-full max-w-sm rounded-xl" />
      </div>
    }>
      <LoginPageContent />
    </Suspense>
  )
}

function LoginPageContent() {
  const searchParams = useSearchParams()
  const initialMode = (searchParams.get("mode") === "register" ? "register" : "login") as FormMode
  const [mode, setMode] = useState<FormMode>(initialMode)
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  // Corretto Logo
  const currentLogo = "/corretto-avatar.png"

  const handleForgotPassword = () => {
    setMode("forgot-password")
  }

  const handleBackToLogin = () => {
    setMode("login")
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-2 relative bg-background text-foreground">
      {/* Absolute positioned UI elements for the page */}
      <div className="absolute left-4 top-4 z-50">
        <BackToHome />
      </div>
      <div className="absolute right-4 top-4 z-50 md:right-8 md:top-8">
        <ThemeLanguageSwitcher />
      </div>

      {/* Left side - Form */}
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex flex-1 flex-col items-center justify-center -mt-12">
          {/* Logo */}
          <div className="mb-6">
            <Image src={currentLogo} alt="Corretto" width={120} height={120} className="object-contain" priority />
          </div>

          {/* Toggle Switch - hide when in forgot-password mode */}
          {mode !== "forgot-password" && (
            <div className="mb-8 flex bg-muted p-1 rounded-full border">
              <button
                onClick={() => setMode("login")}
                className={cn(
                  "px-6 py-2 rounded-full text-sm font-medium transition-all duration-300",
                  mode === "login"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
                )}
              >
                Accedi
              </button>
              <button
                onClick={() => setMode("register")}
                className={cn(
                  "px-6 py-2 rounded-full text-sm font-medium transition-all duration-300",
                  mode === "register"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-background/50 hover:text-foreground"
                )}
              >
                Registrati
              </button>
            </div>
          )}

          {/* Form Container */}
          <div className={cn("w-full transition-all duration-300", mode === "login" ? "max-w-xs" : "max-w-sm")}>
            <AnimatePresence mode="wait">
              {mode === "login" && (
                <motion.div
                  key="login"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.3 }}
                >
                  <LoginForm onForgotPassword={handleForgotPassword} />
                </motion.div>
              )}
              {mode === "register" && (
                <motion.div
                  key="register"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <RegisterForm />
                </motion.div>
              )}
              {mode === "forgot-password" && (
                <motion.div
                  key="forgot-password"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ForgotPasswordForm onBack={handleBackToLogin} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Right side - Minimal Animated Panel */}
      <div className="bg-muted relative hidden lg:block overflow-hidden">
        {/* Gradient Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-chart-2/10 via-transparent to-chart-2/5" />

        {/* Central Content */}
        <div className="relative z-10 flex h-full flex-col items-center justify-center px-8">
          {/* Animated Main Title */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
          >
            <TextGenerateEffect
              words="Corretto"
              className="text-5xl md:text-6xl lg:text-7xl font-heading font-bold tracking-tight text-foreground/90"
              duration={1.5}
            />
          </motion.div>

          {/* Animated Tagline */}
          <div className="mt-6 text-center text-lg text-muted-foreground max-w-md font-light tracking-wide">
            <TextAnimate animation="blurInUp" by="character" once delay={0.5} duration={0.6}>
              Riprenditi il tuo tempo
            </TextAnimate>
          </div>

          {/* Animated Decorative Line */}
          <motion.div
            className="mt-8 h-px w-24 bg-gradient-to-r from-transparent via-chart-2/50 to-transparent"
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ delay: 1, duration: 0.8 }}
          />
        </div>

        {/* Subtle Grid Pattern */}
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `linear-gradient(to right, currentColor 1px, transparent 1px),
                              linear-gradient(to bottom, currentColor 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
          }}
        />
      </div>
    </div>
  )
}
