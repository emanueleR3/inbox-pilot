'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { motion, AnimatePresence } from 'motion/react'
import {
  MessageCircle,
  Sparkles,
  Trash2,
  Minimize2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { backendService } from '@/lib/api/backend-service'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { toast } from 'sonner'
import { Chat } from '@/components/ui/chat'
import { Message } from '@/components/ui/chat-message'

export function FloatingChat() {
  const { session } = useAuth()
  const { t } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [threadId, setThreadId] = useState<string | null>(null)

  // We can remove specific refs as Chat component handles scrolling

  const userId = session?.user?.id || ''

  // Load thread history if exists
  useEffect(() => {
    const savedThreadId = localStorage.getItem('jerry_thread_id')
    if (savedThreadId && userId) {
      setThreadId(savedThreadId)
      loadHistory(savedThreadId)
    } else {
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: t('chat.welcome'),
          createdAt: new Date(),
        }
      ])
    }
  }, [userId])

  const loadHistory = async (tid: string) => {
    try {
      const response = await backendService.getThreadHistory(tid)
      if (response.messages && response.messages.length > 0) {
        setMessages(
          response.messages
            .filter(m => m.role !== 'system')
            .map((m, i) => ({
              id: `history-${i}`,
              role: m.role as 'user' | 'assistant',
              content: m.content,
              createdAt: m.timestamp ? new Date(m.timestamp) : new Date(),
            }))
        )
      } else {
        setMessages([{
          id: 'welcome',
          role: 'assistant',
          content: t('chat.welcome'),
          createdAt: new Date(),
        }])
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
      // Thread might be expired, clear it
      localStorage.removeItem('jerry_thread_id')
      setThreadId(null)
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: t('chat.welcome'),
        createdAt: new Date(),
      }])
    }
  }

  const handleSubmit = async (e?: { preventDefault?: () => void }) => {
    e?.preventDefault?.()
    if (!input.trim() || isGenerating || !userId) return

    const userMessageContent = input.trim()

    // Optimistic User Message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userMessageContent,
      createdAt: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsGenerating(true)

    const assistantId = `assistant-${Date.now()}`

    try {
      let currentContent = ''
      let currentThreadId = threadId
      let assistantAdded = false

      for await (const chunk of backendService.streamMessage(userId, userMessageContent, threadId || undefined)) {
        if (chunk.thread_id && !currentThreadId) {
          currentThreadId = chunk.thread_id
          setThreadId(chunk.thread_id)
          localStorage.setItem('jerry_thread_id', chunk.thread_id)
        }

        if (chunk.content) {
          currentContent += chunk.content

          if (!assistantAdded) {
            assistantAdded = true
            setMessages(prev => [...prev, {
              id: assistantId,
              role: 'assistant',
              content: currentContent,
              createdAt: new Date(),
            }])
          } else {
            setMessages(prev => prev.map(m =>
              m.id === assistantId
                ? { ...m, content: currentContent }
                : m
            ))
          }
        }

        if (chunk.error) {
          throw new Error(chunk.error)
        }
      }

      if (!assistantAdded) {
        setMessages(prev => [...prev, {
          id: assistantId,
          role: 'assistant',
          content: '',
          createdAt: new Date(),
        }])
      }

      // No explicit "isStreaming" flag needed for Message type unless we extend it, 
      // but standard Chat component doesn't strictly require it for basic display.
      // If we wanted typing indicator for the *current* response, Chat handles `isGenerating` prop.

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to send message'
      toast.error(message)
      // Remove the empty assistant message if it failed completely
      setMessages(prev => prev.filter(m => m.id !== assistantId || m.content !== ''))
    } finally {
      setIsGenerating(false)
    }
  }

  const clearChat = async () => {
    if (threadId) {
      try {
        await backendService.deleteThread(threadId)
      } catch (error) {
        console.error('Failed to delete thread:', error)
      }
    }
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: t('chat.welcome'),
      createdAt: new Date(),
    }])
    setThreadId(null)
    localStorage.removeItem('jerry_thread_id')
    toast.success(t('chat.cleared'))
  }

  return (
    <>
      {/* Floating Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="fixed bottom-6 right-6 z-50"
          >
            <Button
              onClick={() => setIsOpen(true)}
              size="lg"
              className="h-14 w-14 rounded-full shadow-2xl bg-gradient-to-br from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 transition-all duration-300 hover:scale-110"
            >
              <MessageCircle className="h-6 w-6" />
              <span className="sr-only">{t('chat.open')}</span>
            </Button>

            {/* Pulse animation */}
            <span className="absolute -top-1 -right-1 flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary/60 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-4 w-4 bg-primary"></span>
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="fixed bottom-6 right-6 z-50 w-[400px] h-[600px] max-h-[80vh] max-w-[calc(100vw-3rem)] flex flex-col"
          >
            {/* Glass card container */}
            <div className="flex flex-col h-full rounded-2xl overflow-hidden backdrop-blur-xl bg-background/95 dark:bg-background/90 border border-white/20 dark:border-white/10 shadow-2xl shadow-black/20">

              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-gradient-to-r from-primary/10 to-primary/5 shrink-0">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Image
                      src="/corretto-avatar.png"
                      alt="Jerry"
                      width={40}
                      height={40}
                      className="rounded-xl"
                    />
                    <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75 animate-pulse"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm">Jerry</h3>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <Sparkles className="h-3 w-3" />
                      {t('chat.aiAssistant')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    onClick={clearChat}
                    title={t('chat.clear')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    onClick={() => setIsOpen(false)}
                  >
                    <Minimize2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Shared Chat Component */}
              <div className="flex-1 min-h-0">
                <Chat
                  className="h-full border-none shadow-none bg-transparent"
                  messages={messages}
                  handleSubmit={handleSubmit}
                  input={input}
                  handleInputChange={(e) => setInput(e.target.value)}
                  isGenerating={isGenerating}
                  stop={() => setIsGenerating(false)}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
