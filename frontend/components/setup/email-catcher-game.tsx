'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Mail, Trophy, RotateCcw, Heart } from 'lucide-react'
import { cn } from '@/lib/utils'

const GAME_WIDTH = 280
const GAME_HEIGHT = 220
const BASKET_WIDTH = 48
const BASKET_HEIGHT = 20
const EMAIL_SIZE = 22
const WIN_SCORE = 10
const MAX_MISSES = 3
const INITIAL_SPEED = 1.8
const SPEED_INCREMENT = 0.15
const SPAWN_INTERVAL = 1200

interface FallingEmail {
    id: number
    x: number
    y: number
    speed: number
}

interface SplashParticle {
    id: number
    x: number
    y: number
    dx: number
    dy: number
}

type GameState = 'ready' | 'playing' | 'won' | 'lost'

export function EmailCatcherGame() {
    const { t } = useLanguage()
    const canvasRef = useRef<HTMLDivElement>(null)
    const animationRef = useRef<number>(0)
    const emailsRef = useRef<FallingEmail[]>([])
    const basketXRef = useRef(GAME_WIDTH / 2 - BASKET_WIDTH / 2)
    const scoreRef = useRef(0)
    const missesRef = useRef(0)
    const nextIdRef = useRef(0)
    const lastSpawnRef = useRef(0)
    const isDraggingRef = useRef(false)
    const dragOffsetRef = useRef(0)

    const [score, setScore] = useState(0)
    const [misses, setMisses] = useState(0)
    const [gameState, setGameState] = useState<GameState>('ready')
    const [basketX, setBasketX] = useState(GAME_WIDTH / 2 - BASKET_WIDTH / 2)
    const [emails, setEmails] = useState<FallingEmail[]>([])
    const [splashes, setSplashes] = useState<SplashParticle[]>([])
    const splashIdRef = useRef(0)

    const resetGame = useCallback(() => {
        emailsRef.current = []
        basketXRef.current = GAME_WIDTH / 2 - BASKET_WIDTH / 2
        scoreRef.current = 0
        missesRef.current = 0
        nextIdRef.current = 0
        lastSpawnRef.current = 0

        setScore(0)
        setMisses(0)
        setBasketX(GAME_WIDTH / 2 - BASKET_WIDTH / 2)
        setEmails([])
        setSplashes([])
        setGameState('ready')
    }, [])

    const startGame = useCallback(() => {
        resetGame()
        // Use setTimeout so state from resetGame settles first
        setTimeout(() => {
            setGameState('playing')
            lastSpawnRef.current = performance.now()
        }, 50)
    }, [resetGame])

    // Game loop
    const gameLoop = useCallback((timestamp: number) => {
        if (scoreRef.current >= WIN_SCORE) {
            setGameState('won')
            return
        }
        if (missesRef.current >= MAX_MISSES) {
            setGameState('lost')
            return
        }

        // Spawn new emails
        if (timestamp - lastSpawnRef.current > SPAWN_INTERVAL) {
            const newEmail: FallingEmail = {
                id: nextIdRef.current++,
                x: Math.random() * (GAME_WIDTH - EMAIL_SIZE),
                y: -EMAIL_SIZE,
                speed: INITIAL_SPEED + scoreRef.current * SPEED_INCREMENT,
            }
            emailsRef.current = [...emailsRef.current, newEmail]
            lastSpawnRef.current = timestamp
        }

        // Update positions
        const bx = basketXRef.current
        const basketTop = GAME_HEIGHT - BASKET_HEIGHT
        let caughtX: number | null = null
        let missed = false

        const updated = emailsRef.current
            .map((email) => ({ ...email, y: email.y + email.speed }))
            .filter((email) => {
                // Check catch
                if (
                    email.y + EMAIL_SIZE >= basketTop &&
                    email.y + EMAIL_SIZE <= basketTop + BASKET_HEIGHT + 5 &&
                    email.x + EMAIL_SIZE > bx &&
                    email.x < bx + BASKET_WIDTH
                ) {
                    caughtX = email.x + EMAIL_SIZE / 2
                    return false
                }
                // Check miss (fell below)
                if (email.y > GAME_HEIGHT) {
                    missed = true
                    return false
                }
                return true
            })

        if (caughtX !== null) {
            scoreRef.current++
            setScore(scoreRef.current)

            // Spawn splash particles
            const newSplashes: SplashParticle[] = Array.from({ length: 5 }, () => ({
                id: splashIdRef.current++,
                x: caughtX!,
                y: basketTop,
                dx: (Math.random() - 0.5) * 24,
                dy: -(Math.random() * 16 + 8),
            }))
            setSplashes(prev => [...prev, ...newSplashes])
            // Auto-remove after animation
            setTimeout(() => {
                setSplashes(prev => prev.filter(s => !newSplashes.some(ns => ns.id === s.id)))
            }, 400)
        }
        if (missed) {
            missesRef.current++
            setMisses(missesRef.current)
        }

        emailsRef.current = updated
        setEmails([...updated])

        animationRef.current = requestAnimationFrame(gameLoop)
    }, [])

    // Start/stop game loop
    useEffect(() => {
        if (gameState === 'playing') {
            animationRef.current = requestAnimationFrame(gameLoop)
        }
        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current)
            }
        }
    }, [gameState, gameLoop])

    // Mouse/touch handling for basket
    const handlePointerDown = useCallback(
        (e: React.PointerEvent) => {
            if (gameState !== 'playing') return
            const rect = canvasRef.current?.getBoundingClientRect()
            if (!rect) return
            const x = e.clientX - rect.left
            isDraggingRef.current = true
            dragOffsetRef.current = x - basketXRef.current
                ; (e.target as HTMLElement).setPointerCapture(e.pointerId)
        },
        [gameState]
    )

    const handlePointerMove = useCallback(
        (e: React.PointerEvent) => {
            if (!isDraggingRef.current || gameState !== 'playing') return
            const rect = canvasRef.current?.getBoundingClientRect()
            if (!rect) return
            let newX = e.clientX - rect.left - dragOffsetRef.current
            newX = Math.max(0, Math.min(GAME_WIDTH - BASKET_WIDTH, newX))
            basketXRef.current = newX
            setBasketX(newX)
        },
        [gameState]
    )

    const handlePointerUp = useCallback(() => {
        isDraggingRef.current = false
    }, [])

    // Keyboard controls
    useEffect(() => {
        if (gameState !== 'playing') return
        const handleKeyDown = (e: KeyboardEvent) => {
            const step = 18
            if (e.key === 'ArrowLeft' || e.key === 'a') {
                basketXRef.current = Math.max(0, basketXRef.current - step)
                setBasketX(basketXRef.current)
            } else if (e.key === 'ArrowRight' || e.key === 'd') {
                basketXRef.current = Math.min(GAME_WIDTH - BASKET_WIDTH, basketXRef.current + step)
                setBasketX(basketXRef.current)
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [gameState])

    const lives = MAX_MISSES - misses

    return (
        <div className="flex flex-col items-center gap-2 select-none">
            {/* HUD */}
            <div className="flex items-center justify-between w-full px-1" style={{ maxWidth: GAME_WIDTH }}>
                <div className="flex items-center gap-1.5">
                    <Trophy className="h-3.5 w-3.5 text-yellow-500" />
                    <span className="text-xs font-semibold tabular-nums">{score}/{WIN_SCORE}</span>
                </div>
                <div className="flex items-center gap-0.5">
                    {Array.from({ length: MAX_MISSES }).map((_, i) => (
                        <Heart
                            key={i}
                            className={cn(
                                'h-3.5 w-3.5 transition-colors',
                                i < lives ? 'text-red-500 fill-red-500' : 'text-muted-foreground/30'
                            )}
                        />
                    ))}
                </div>
            </div>

            {/* Game Area */}
            <div
                ref={canvasRef}
                className="relative overflow-hidden rounded-xl border border-border/50 bg-gradient-to-b from-background to-muted/30 cursor-grab active:cursor-grabbing"
                style={{ width: GAME_WIDTH, height: GAME_HEIGHT, touchAction: 'none' }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerLeave={handlePointerUp}
            >
                {/* Ready / Won / Lost overlays */}
                {gameState === 'ready' && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm">
                        <Mail className="h-8 w-8 text-primary animate-bounce" />
                        <p className="text-xs font-medium text-center px-4">{t('game.catchEmails')}</p>
                        <Button size="sm" onClick={startGame} className="text-xs h-7 px-4">
                            {t('game.play')}
                        </Button>
                    </div>
                )}

                {gameState === 'won' && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-background/80 backdrop-blur-sm">
                        <Trophy className="h-8 w-8 text-yellow-500" />
                        <p className="text-sm font-bold text-green-600 dark:text-green-400">{t('game.youWin')}</p>
                        <p className="text-[10px] text-muted-foreground">{t('game.winMessage')}</p>
                        <Button size="sm" variant="outline" onClick={startGame} className="text-xs h-7 px-3 gap-1.5 mt-1">
                            <RotateCcw className="h-3 w-3" />
                            {t('game.playAgain')}
                        </Button>
                    </div>
                )}

                {gameState === 'lost' && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-background/80 backdrop-blur-sm">
                        <Mail className="h-8 w-8 text-destructive" />
                        <p className="text-sm font-bold text-destructive">{t('game.gameOver')}</p>
                        <p className="text-[10px] text-muted-foreground">
                            {t('game.score')}: {score}/{WIN_SCORE}
                        </p>
                        <Button size="sm" variant="outline" onClick={startGame} className="text-xs h-7 px-3 gap-1.5 mt-1">
                            <RotateCcw className="h-3 w-3" />
                            {t('game.retry')}
                        </Button>
                    </div>
                )}

                {/* Falling Emails */}
                {gameState === 'playing' &&
                    emails.map((email) => (
                        <div
                            key={email.id}
                            className="absolute flex items-center justify-center drop-shadow-sm"
                            style={{
                                left: email.x,
                                top: email.y,
                                width: EMAIL_SIZE,
                                height: EMAIL_SIZE,
                                transition: 'none',
                            }}
                        >
                            <Mail className="h-full w-full text-primary" />
                        </div>
                    ))}

                {/* Splash particles */}
                {splashes.map((p) => (
                    <div
                        key={p.id}
                        className="absolute rounded-full bg-primary pointer-events-none animate-[splash_400ms_ease-out_forwards]"
                        style={{
                            width: 6,
                            height: 6,
                            left: p.x - 3,
                            top: p.y - 3,
                            '--splash-dx': `${p.dx}px`,
                            '--splash-dy': `${p.dy}px`,
                        } as React.CSSProperties}
                    />
                ))}

                {/* Basket */}
                {gameState === 'playing' && (
                    <div
                        className="absolute rounded-t-lg bg-primary shadow-lg shadow-primary/30 flex items-center justify-center"
                        style={{
                            left: basketX,
                            top: GAME_HEIGHT - BASKET_HEIGHT,
                            width: BASKET_WIDTH,
                            height: BASKET_HEIGHT,
                        }}
                    >
                        <div className="w-3/4 h-1 rounded-full bg-primary-foreground/30" />
                    </div>
                )}
            </div>

            {/* Hint text */}
            {gameState === 'playing' && (
                <p className="text-[10px] text-muted-foreground/70 text-center">
                    {t('game.dragHint')}
                </p>
            )}
        </div>
    )
}
