/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { Suspense } from "react"
import Markdown from "react-markdown"
import { cn } from "@/lib/utils"
import { CopyButton } from "@/components/ui/copy-button"

interface MarkdownRendererProps {
  children?: string | null
}

export function MarkdownRenderer({ children }: MarkdownRendererProps) {
  if (!children) return null

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      <Markdown components={COMPONENTS}>
        {children}
      </Markdown>
    </div>
  )
}

// Helper to extract text from children
function getChildrenText(element: any): string {
  if (typeof element === "string") return element
  if (Array.isArray(element)) return element.map(getChildrenText).join("")
  if (element?.props?.children) return getChildrenText(element.props.children)
  return ""
}

const HighlightedPre = React.memo(({ children, language, className, ...props }: any) => {
  const [tokens, setTokens] = React.useState<any[][] | null>(null)

  React.useEffect(() => {
    let mounted = true

    async function highlight() {
      try {
        const { codeToTokens, bundledLanguages } = await import("shiki")
        if (!(language in bundledLanguages)) {
          if (mounted) setTokens(null)
          return
        }

        const { tokens: newTokens } = await codeToTokens(children, {
          lang: language as any,
          defaultColor: false,
          themes: { light: "github-light", dark: "github-dark" },
        })

        if (mounted) setTokens(newTokens)
      } catch (e) {
        console.error("Failed to highlight code", e)
      }
    }

    highlight()
    return () => { mounted = false }
  }, [children, language])

  if (!tokens) {
    return <pre className={className} {...props}>{children}</pre>
  }

  return (
    <pre className={className} {...props}>
      <code>
        {tokens.map((line, i) => (
          <React.Fragment key={i}>
            <span>
              {line.map((token, j) => (
                <span
                  key={j}
                  className="text-shiki-light bg-shiki-light-bg dark:text-shiki-dark dark:bg-shiki-dark-bg"
                  style={token.htmlStyle as any}
                >
                  {token.content}
                </span>
              ))}
            </span>
            {i !== tokens.length - 1 && "\n"}
          </React.Fragment>
        ))}
      </code>
    </pre>
  )
})
HighlightedPre.displayName = "HighlightedPre"

const CodeBlock = ({ children, className, language, ...props }: any) => {
  const code = getChildrenText(children)
  const preClass = cn(
    "overflow-x-scroll rounded-md border bg-background/50 p-4 font-mono text-sm [scrollbar-width:none]",
    className
  )

  return (
    <div className="group/code relative mb-4">
      <Suspense fallback={<pre className={preClass} {...props}>{children}</pre>}>
        <HighlightedPre language={language} className={preClass} {...props}>
          {code}
        </HighlightedPre>
      </Suspense>
      <div className="invisible absolute right-2 top-2 flex space-x-1 rounded-lg p-1 opacity-0 transition-all duration-200 group-hover/code:visible group-hover/code:opacity-100">
        <CopyButton content={code} copyMessage="Copied code to clipboard" />
      </div>
    </div>
  )
}

const COMPONENTS: any = {
  h1: ({ className, ...props }: any) => (
    <h1 className={cn("text-2xl font-semibold tracking-tight pb-2 border-b scroll-m-20 first:mt-0", className)} {...props} />
  ),
  h2: ({ className, ...props }: any) => (
    <h2 className={cn("text-xl font-semibold tracking-tight pb-1 scroll-m-20 first:mt-0", className)} {...props} />
  ),
  h3: ({ className, ...props }: any) => (
    <h3 className={cn("text-lg font-semibold tracking-tight scroll-m-20", className)} {...props} />
  ),
  h4: ({ className, ...props }: any) => (
    <h4 className={cn("text-base font-semibold tracking-tight scroll-m-20", className)} {...props} />
  ),
  h5: ({ className, ...props }: any) => (
    <h5 className={cn("text-sm font-semibold scroll-m-20", className)} {...props} />
  ),
  h6: ({ className, ...props }: any) => (
    <h6 className={cn("text-sm font-semibold text-muted-foreground scroll-m-20", className)} {...props} />
  ),
  p: ({ className, ...props }: any) => (
    <p className={cn("leading-7 [&:not(:first-child)]:mt-6", className)} {...props} />
  ),
  ul: ({ className, ...props }: any) => (
    <ul className={cn("my-6 ml-6 list-disc [&>li]:mt-2", className)} {...props} />
  ),
  ol: ({ className, ...props }: any) => (
    <ol className={cn("my-6 ml-6 list-decimal [&>li]:mt-2", className)} {...props} />
  ),
  li: ({ className, ...props }: any) => (
    <li className={cn("", className)} {...props} />
  ),
  blockquote: ({ className, ...props }: any) => (
    <blockquote className={cn("border-l-2 border-primary pl-4 italic text-muted-foreground", className)} {...props} />
  ),
  img: ({ className, alt, ...props }: any) => (
    <img className={cn("rounded-lg border bg-muted", className)} alt={alt || ""} {...props} />
  ),
  hr: ({ className, ...props }: any) => (
    <hr className={cn("my-4 border-muted", className)} {...props} />
  ),
  table: ({ className, ...props }: any) => (
    <div className="my-6 w-full overflow-y-auto">
      <table className={cn("w-full", className)} {...props} />
    </div>
  ),
  tr: ({ className, ...props }: any) => (
    <tr className={cn("m-0 border-t p-0 even:bg-muted/30 hover:bg-muted/20 transition-colors", className)} {...props} />
  ),
  th: ({ className, ...props }: any) => (
    <th className={cn("border px-4 py-2 text-left font-bold [&[align=center]]:text-center [&[align=right]]:text-right bg-muted/50", className)} {...props} />
  ),
  td: ({ className, ...props }: any) => (
    <td className={cn("border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right", className)} {...props} />
  ),
  a: ({ className, ...props }: any) => (
    <a className={cn("font-medium text-primary underline underline-offset-4 hover:no-underline", className)} {...props} />
  ),
  pre: ({ children }: any) => children,
  code: ({ className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || "")
    if (match) {
      return <CodeBlock language={match[1]} className={className} {...props}>{children}</CodeBlock>
    }
    return (
      <code className={cn("relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold text-foreground", className)} {...props}>
        {children}
      </code>
    )
  },
}

export default MarkdownRenderer
