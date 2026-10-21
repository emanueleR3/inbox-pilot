import { Dot } from "lucide-react"

export function TypingIndicator() {
  return (
    <div className="justify-left flex space-x-1">
      <div className="rounded-lg bg-muted p-3">
        <div className="flex -space-x-2.5">
          <Dot className="h-5 w-5 animate-typing-dot-bounce" style={{ animationDelay: "0ms" }} />
          <Dot className="h-5 w-5 animate-typing-dot-bounce" style={{ animationDelay: "300ms" }} />
          <Dot className="h-5 w-5 animate-typing-dot-bounce" style={{ animationDelay: "600ms" }} />
        </div>
      </div>
    </div>
  )
}
