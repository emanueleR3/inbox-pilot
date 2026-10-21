import { TopNavigation } from "@/components/layout/top-navigation"
import { FloatingChat } from "@/components/chatbot/floating-chat"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopNavigation />
      <main className="flex-1 container mx-auto max-w-7xl">
        {children}
      </main>
      <FloatingChat />
    </div>
  )
}
