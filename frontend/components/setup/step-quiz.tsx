'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSetup } from '@/lib/context/setup-context'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Check, AlertCircle, Loader2, Save, Undo } from 'lucide-react'
import { cn } from '@/lib/utils'
import { backendService, BulletItem } from '@/lib/api/backend-service'
import { toast } from 'sonner'
import { Chat } from '@/components/ui/chat'
import { Message } from '@/components/ui/chat-message'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import { SaveProgressIndicator } from '@/components/setup/save-progress-indicator'

export function StepQuiz() {
  const {
    goToNextStep,
    goToPreviousStep,
    markStepComplete,
    markStepIncomplete,
    connectedEmail,
    websiteUrl,
    isLoading: isGlobalLoading
  } = useSetup()
  const { t } = useLanguage()

  // Local state
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [hasError, setHasError] = useState(false)

  // Quiz state
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [bulletList, setBulletList] = useState<BulletItem[]>([])
  const [isQuizDone, setIsQuizDone] = useState(false)
  const [isReviewing, setIsReviewing] = useState(false)
  const [markdownContent, setMarkdownContent] = useState('')
  const [originalMarkdown, setOriginalMarkdown] = useState('')

  // Save progress state
  const [showSaveProgress, setShowSaveProgress] = useState(false)
  const [saveEmail, setSaveEmail] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  // Tab state
  const [activeTab, setActiveTab] = useState<"chat" | "info" | "review">("chat")

  useEffect(() => {
    // Focus logic handled by Chat component usually, but we can keep this for edge cases
  }, [messages, isQuizDone, isTyping, isReviewing])

  /**
   * Handle quiz response processing
   */
  const handleQuizResponse = useCallback((response: unknown) => {
    const data = response as {
      session_id?: string
      question?: string
      bullet_list?: BulletItem[]
      extracted_markdown?: string
      done?: boolean
      save_started?: boolean
      email?: string
    }

    if (data.session_id) {
      setSessionId(data.session_id)
    }

    // Store email for save status polling
    if (data.email) {
      setSaveEmail(data.email)
    }

    if (data.question) {
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1]
        // Deduplicate logic
        if (lastMsg?.role === 'assistant' && lastMsg.content === data.question) {
          return prev
        }
        return [...prev, {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.question!,
          createdAt: new Date()
        }]
      })
    }

    setBulletList(data.bullet_list || [])

    if (data.extracted_markdown) {
      const cleaned = data.extracted_markdown.replace(/^```markdown\n?/, '').replace(/\n?```$/, '')
      setMarkdownContent(cleaned)
      setOriginalMarkdown(cleaned)
    }

    // Check if save pipeline started in background
    if (data.save_started) {
      setShowSaveProgress(true)
      // Navigate to next step since save runs in background
      setIsQuizDone(true)
      markStepComplete('quiz')
      goToNextStep()
      return
    }

    if (data.done) {
      setIsQuizDone(true)
      markStepComplete('quiz')
      goToNextStep()
    } else if (data.extracted_markdown) {
      setIsReviewing(true)
      setActiveTab('review')
    } else {
      markStepIncomplete('quiz')
    }
  }, [markStepComplete, markStepIncomplete, goToNextStep])

  /**
   * Initialize quiz
   */


  // Ref to prevent React Strict Mode double-invocation of initQuiz
  const initCalledRef = useRef(false)

  // Start or recover quiz on mount
  useEffect(() => {
    const initQuiz = async () => {
      if (!connectedEmail || sessionId || hasError) return
      // Guard against React Strict Mode double-invocation
      if (initCalledRef.current) return
      initCalledRef.current = true

      try {
        setIsStarting(true)

        // 1. Try to recover existing session by email using the dedicated endpoint
        try {
          console.log('[SETUP DEBUG] step-quiz → GET /quiz/sessions (recover)', { email: connectedEmail })
          const sessionsResponse = await backendService.getQuizSessionByEmail(connectedEmail)
          console.log('[SETUP DEBUG] step-quiz → GET /quiz/sessions RESPONSE', sessionsResponse)
          // Response is an array, find the first active (not done) session
          const sessions = Array.isArray(sessionsResponse) ? sessionsResponse : (sessionsResponse ? [sessionsResponse] : [])
          const existingSession = sessions.find(s => s && !s.is_done)

          if (existingSession && existingSession.session_id) {
            // Use session data directly from the response (no need to call getQuizState)
            setSessionId(existingSession.session_id)
            setSaveEmail(connectedEmail)
            // Handle bullet_list which might be an array of objects or strings
            if (existingSession.bullet_list && Array.isArray(existingSession.bullet_list)) {
              setBulletList(existingSession.bullet_list as BulletItem[])
            }

            if (existingSession.final_markdown) {
              const cleaned = existingSession.final_markdown.replace(/^```markdown\n?/, '').replace(/\n?```$/, '')
              setMarkdownContent(cleaned)
              setOriginalMarkdown(cleaned)
              setIsReviewing(true)
            } else if (existingSession.is_done) {
              setIsQuizDone(true)
              markStepComplete('quiz')
            } else {
              // Session is active - show the last question if available, otherwise welcome back
              const lastQuestion = existingSession.question || existingSession.last_question
              setMessages([{
                id: 'welcome-back',
                role: 'assistant',
                content: lastQuestion || t('setup.quizResumeMessage'),
                createdAt: new Date()
              }])
            }
            // Session data restored
            return
          }
        } catch (err) {
        }

        // 2. Start new quiz if no existing session
        console.log('[SETUP DEBUG] step-quiz → POST /quiz/start', { email: connectedEmail })
        const response = await backendService.startQuiz({ email: connectedEmail })
        console.log('[SETUP DEBUG] step-quiz → POST /quiz/start RESPONSE', response)
        handleQuizResponse(response)

      } catch (error: unknown) {
        const errMessage = (error as Error)?.message || ''
        // Check for the specific "duplicate key" constraint error (code 23505)
        if (errMessage.includes('23505') || errMessage.includes('one_active_quiz_per_service')) {
          console.warn('[Quiz] Session already exists for this service, attempting recovery...')
          // Try to fetch the existing session one more time
          try {
            console.log('[SETUP DEBUG] step-quiz → GET /quiz/sessions (recovery retry)', { email: connectedEmail })
            const sessionsResponse = await backendService.getQuizSessionByEmail(connectedEmail)
            console.log('[SETUP DEBUG] step-quiz → GET /quiz/sessions (recovery retry) RESPONSE', sessionsResponse)
            // Response is an array, find the first session
            const sessions = Array.isArray(sessionsResponse) ? sessionsResponse : (sessionsResponse ? [sessionsResponse] : [])
            const existingSession = sessions.find(s => s && s.session_id)
            if (existingSession && existingSession.session_id) {
              // Use session data directly from the response
              setSessionId(existingSession.session_id)
              setSaveEmail(connectedEmail)
              // Handle bullet_list which might be an array of objects or strings
              if (existingSession.bullet_list && Array.isArray(existingSession.bullet_list)) {
                setBulletList(existingSession.bullet_list as BulletItem[])
              }
              if (existingSession.final_markdown) {
                const cleaned = existingSession.final_markdown.replace(/^```markdown\n?/, '').replace(/\n?```$/, '')
                setMarkdownContent(cleaned)
                setOriginalMarkdown(cleaned)
                setIsReviewing(true)
                setActiveTab('review')
              } else if (existingSession.is_done) {
                setIsQuizDone(true)
                markStepComplete('quiz')
              } else {
                // Session is active - show the last question if available, otherwise welcome back
                const lastQuestion = existingSession.question || existingSession.last_question
                setMessages([{
                  id: 'recovered',
                  role: 'assistant',
                  content: lastQuestion || t('setup.quizResumeMessage'),
                  createdAt: new Date()
                }])
              }
              // Session data restored
              return // Successfully recovered
            }
          } catch (recoveryErr) {
            console.error('[Quiz] Failed to recover session:', recoveryErr)
          }
          // If recovery failed, show specific error
          setHasError(true)
          toast.error(t('setup.quizSessionExists'))
        } else {
          console.error('Failed to initialize quiz:', error)
          setHasError(true)
          toast.error(t('setup.quizLoadError'))
        }
      } finally {
        setIsStarting(false)
      }
    }

    initQuiz()

    // Cleanup: reset the ref if React unmounts (but only matters for dev strict mode)
    return () => {
      // Don't reset - we want to prevent re-initialization
    }
  }, [connectedEmail, sessionId, hasError, handleQuizResponse, t, markStepComplete])


  /**
   * Submit answer
   */
  const handleSubmit = async (e?: { preventDefault?: () => void }) => {
    e?.preventDefault?.()
    if (!inputValue.trim() || !sessionId || isTyping) return

    const userMsg = inputValue.trim()
    setInputValue('')

    const userMessageId = Date.now().toString()
    setMessages(prev => [...prev, {
      id: userMessageId,
      role: 'user',
      content: userMsg,
      createdAt: new Date()
    }])
    setIsTyping(true)

    try {
      const answerPayload = { session_id: sessionId, answer: userMsg }
      console.log('[SETUP DEBUG] step-quiz → POST /quiz/answer', answerPayload)
      const response = await backendService.answerQuiz(answerPayload)
      console.log('[SETUP DEBUG] step-quiz → POST /quiz/answer RESPONSE', response)

      handleQuizResponse(response)

      const responseData = response as { done?: boolean; extracted_markdown?: string }

      if (responseData.done && !responseData.extracted_markdown) {
        toast.success(t('setup.quizCompletedSuccess'))
      }

    } catch (error) {
      console.error('Failed to send answer:', error)
      toast.error(t('setup.quizAnswerError'))
    } finally {
      setIsTyping(false)
    }
  }

  const handleSaveMarkdown = async () => {
    if (!sessionId || !markdownContent) return

    try {
      setIsTyping(true)
      // Only save, do not complete step yet
      const markdownPayload = {
        session_id: sessionId,
        final_markdown: `\`\`\`markdown\n${markdownContent}\n\`\`\``
      }
      console.log('[SETUP DEBUG] step-quiz → PATCH /quiz/update-final-markdown', { session_id: sessionId, final_markdown: '(content omitted)' })
      await backendService.updateFinalMarkdown(markdownPayload)
      console.log('[SETUP DEBUG] step-quiz → PATCH /quiz/update-final-markdown DONE')

      setOriginalMarkdown(markdownContent)
      toast.success(t('setup.profileSavedSuccess'))
    } catch (error) {
      console.error('Failed to save profile:', error)
      toast.error(t('setup.profileSaveError'))
    } finally {
      setIsTyping(false)
    }
  }

  const handleComplete = async () => {
    if (!sessionId || !markdownContent || isSaving) return

    try {
      setIsSaving(true)

      // First save the final markdown
      console.log('[SETUP DEBUG] step-quiz (handleComplete) → PATCH /quiz/update-final-markdown', { session_id: sessionId })
      await backendService.updateFinalMarkdown({
        session_id: sessionId,
        final_markdown: `\`\`\`markdown\n${markdownContent}\n\`\`\``
      })
      console.log('[SETUP DEBUG] step-quiz (handleComplete) → PATCH /quiz/update-final-markdown DONE')

      // If no website was inserted, only save the markdown (skip DB save pipeline)
      if (!websiteUrl) {
        setOriginalMarkdown(markdownContent)
        setIsReviewing(false)
        setIsQuizDone(true)
        markStepComplete('quiz')
        goToNextStep()
        toast.success(t('setup.profileSavedSuccess'))
        return
      }

      // Then call the save endpoint to start the background save pipeline
      console.log('[SETUP DEBUG] step-quiz → POST /quiz/save', { session_id: sessionId })
      const saveResponse = await backendService.saveQuiz({
        session_id: sessionId
      })
      console.log('[SETUP DEBUG] step-quiz → POST /quiz/save RESPONSE', saveResponse)

      if (saveResponse.started) {
        // Store email for progress tracking
        setSaveEmail(saveResponse.email)
        setShowSaveProgress(true)

        // Navigate immediately since save runs in background
        setIsReviewing(false)
        setActiveTab('chat')
        setIsQuizDone(true)
        markStepComplete('quiz')
        goToNextStep()

        toast.success(t('setup.quizSaveStarted') || 'Saving your profile...')
      } else if (saveResponse.error) {
        throw new Error(saveResponse.error)
      }

    } catch (error) {
      console.error('Failed to complete quiz:', error)
      toast.error(t('setup.quizCompletionError') || 'Failed to complete quiz')
    } finally {
      setIsSaving(false)
    }
  }

  if (!connectedEmail && !isGlobalLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground min-h-[400px]">
        <AlertCircle className="w-12 h-12 mb-4" />
        <p>{t('setup.connectEmailFirst')}</p>
        <Button variant="outline" onClick={goToPreviousStep} className="mt-4">
          {t('setup.goBack')}
        </Button>
      </div>
    )
  }

  if (isGlobalLoading || (isStarting && messages.length === 0)) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground min-h-[400px]">
        <Loader2 className="w-8 h-8 mb-4 animate-spin text-primary" />
        <p>{t('setup.startingSetup')}</p>
      </div>
    )
  }

  return (
    <>
      {/* Save Progress Indicator (floating, top-left) */}
      {showSaveProgress && sessionId && (saveEmail || connectedEmail) && (
        <SaveProgressIndicator
          sessionId={sessionId}
          email={saveEmail || connectedEmail!}
          onError={(err) => toast.error(`Save error: ${err}`)}
        />
      )}

      <div className="h-[calc(100vh-16rem)] min-h-[500px] w-full flex flex-col gap-4 pb-4">
        <Tabs
          value={activeTab}
          onValueChange={(v) => {
            const newTab = v as "chat" | "info" | "review";
            setActiveTab(newTab);
            if (newTab === "review") {
              setIsReviewing(true);
            } else {
              setIsReviewing(false);
            }
          }}
          className="flex-1 flex flex-col min-h-0 w-full overflow-hidden"
        >

          <div className="flex items-center justify-between mb-2 shrink-0">
            <TabsList className="bg-muted/50 w-full justify-start h-10 p-1">
              <TabsTrigger value="chat" className="text-xs px-4 h-8">{t('setup.quizChat') || 'Chat'}</TabsTrigger>
              {bulletList.length > 0 && <TabsTrigger value="info" className="text-xs px-4 h-8">{t('setup.quizInfoGathered')} <span className="ml-2 bg-primary/10 text-primary px-1.5 rounded-md">{bulletList.length}</span></TabsTrigger>}
              {isReviewing && <TabsTrigger value="review" className="text-xs px-4 h-8">{t('setup.quizReviewTitle')}</TabsTrigger>}
            </TabsList>
          </div>

          <div className="flex-1 min-h-0 relative border rounded-2xl shadow-sm bg-background/50 backdrop-blur-xl overflow-hidden glassmorphism-styles">
            <TabsContent value="chat" className="h-full m-0 p-0 border-none data-[state=active]:flex flex-col">
              <Chat
                className="h-full border-none rounded-none shadow-none bg-transparent"
                messages={messages}
                handleSubmit={handleSubmit}
                input={inputValue}
                handleInputChange={(e) => setInputValue(e.target.value)}
                isGenerating={isTyping}
                stop={() => setIsTyping(false)}
              />
            </TabsContent>

            <TabsContent value="info" className="h-full m-0 p-0 overflow-y-auto data-[state=active]:block bg-transparent custom-scrollbar">
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-sm text-foreground/80 uppercase tracking-wider">
                    {t('setup.quizInfoGathered')}
                  </h3>
                  <Button variant="outline" size="sm" onClick={goToPreviousStep} className="h-8 text-xs">
                    <ArrowLeft className="w-3 h-3 mr-2" />
                    {t('setup.back')}
                  </Button>
                </div>
                <div className="space-y-4">
                  {bulletList.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-sm animate-in fade-in slide-in-from-left-2 duration-300" style={{ animationDelay: `${idx * 100}ms` }}>
                      <div className={cn(
                        "mt-0.5 w-5 h-5 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300",
                        item.completed
                          ? "bg-primary border-primary text-primary-foreground shadow-sm shadow-primary/20"
                          : "border-muted-foreground/30 text-transparent"
                      )}>
                        {item.completed && <Check className="w-3 h-3" />}
                      </div>
                      <div className="flex-1 space-y-1">
                        <span className={cn(
                          "block font-medium transition-colors",
                          item.completed ? "text-foreground" : "text-muted-foreground"
                        )}>
                          {item.name}
                        </span>
                        {item.info && (
                          <span className="block text-xs text-muted-foreground/80">
                            {item.info}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="review" className="h-full m-0 p-0 flex flex-col data-[state=active]:flex !mt-0 bg-transparent">
              <div className="flex-1 min-h-0 relative w-full border-b border-border/50">
                <Tabs defaultValue="edit" className="flex-1 flex flex-col h-full min-h-0 w-full">
                  <div className="h-12 px-4 bg-muted/30 flex items-center justify-between shrink-0">
                    <p className="text-xs text-muted-foreground">{t('setup.quizReviewSubtitle')}</p>
                    <TabsList className="h-8">
                      <TabsTrigger value="edit" className="text-xs h-7 px-3">{t('common.edit') || 'Edit'}</TabsTrigger>
                      <TabsTrigger value="preview" className="text-xs h-7 px-3">{t('common.preview') || 'Preview'}</TabsTrigger>
                    </TabsList>
                  </div>

                  <div className="flex-1 min-h-0 relative">
                    <TabsContent value="edit" className="h-full m-0 p-0 border-none data-[state=active]:flex flex-col !mt-0">
                      <textarea
                        value={markdownContent}
                        onChange={(e) => setMarkdownContent(e.target.value)}
                        className="w-full h-full resize-none p-4 font-mono text-sm leading-relaxed border-0 focus:outline-none focus:ring-0 rounded-none bg-transparent overflow-y-auto custom-scrollbar"
                        placeholder={t('setup.quizReviewPlaceholder')}
                      />
                    </TabsContent>
                    <TabsContent value="preview" className="h-full m-0 p-4 border-none data-[state=active]:block !mt-0 overflow-y-auto bg-card rounded-b-xl custom-scrollbar">
                      <div className="w-full max-w-none break-words prose prose-sm dark:prose-invert">
                        <MarkdownRenderer>{markdownContent}</MarkdownRenderer>
                      </div>
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
              <div className="h-16 px-6 bg-background/80 backdrop-blur-md flex justify-between items-center shrink-0 mt-auto">
                <Button variant="ghost" size="sm" onClick={() => {
                  setIsReviewing(false);
                  setActiveTab('chat');
                }} disabled={isTyping} className="text-muted-foreground h-9">
                  <Undo className="w-4 h-4 mr-2" />
                  {t('setup.backToChat')}
                </Button>
                <div className="flex gap-3">
                  <Button onClick={handleSaveMarkdown} disabled={isTyping || markdownContent === originalMarkdown} variant="secondary" size="sm" className="h-9">
                    {isTyping ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    {t('setup.saveProfile') || 'Save'}
                  </Button>
                  <Button onClick={handleComplete} disabled={isTyping || isSaving} size="sm" className="h-9 bg-primary text-primary-foreground hover:bg-primary/90">
                    {isSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
                    {t('setup.complete')}
                  </Button>
                </div>
              </div>
            </TabsContent>

          </div>
        </Tabs>
      </div>
    </>
  )
}
