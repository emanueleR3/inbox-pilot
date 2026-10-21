'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useSetup } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService } from '@/lib/api/backend-service'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { Loader2, Check } from 'lucide-react'
import confetti from 'canvas-confetti'

const INDUSTRIES = [
    'Technology',
    'Marketing',
    'Finance',
    'Healthcare',
    'Real Estate',
    'Legal',
    'Education',
    'Manufacturing',
    'Retail',
    'Consulting',
    'Other'
]

const TONES_OF_VOICE = [
    'Professional',
    'Friendly',
    'Formal',
    'Casual',
    'Direct',
    'Empathetic'
]

export function StepProfile() {
    const router = useRouter()
    const { } = useSetup()
    const { currentSubscription, markSubscriptionConfigured } = useAuth()
    const { } = useLanguage()

    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    // Form State
    const [industry, setIndustry] = useState('')
    const [productsServices, setProductsServices] = useState('')
    const [toneOfVoice, setToneOfVoice] = useState('')
    const [signature, setSignature] = useState('')
    const [markdown, setMarkdown] = useState('') // Store existing markdown to preserve it locally if needed

    useEffect(() => {
        const fetchProfile = async () => {
            if (!currentSubscription?.subscription_id) return

            try {
                const serviceData = await backendService.getSubscriptionService(currentSubscription.subscription_id)
                const service = Array.isArray(serviceData) ? serviceData[0] : serviceData

                if (service && service.information) {
                    let infoString = ''

                    if (typeof service.information === 'string') {
                        infoString = service.information
                    } else if (typeof service.information === 'object' && (service.information as any).markdown) { // eslint-disable-line @typescript-eslint/no-explicit-any
                        // Handle legacy/corrupted JSON case
                        infoString = (service.information as any).markdown // eslint-disable-line @typescript-eslint/no-explicit-any
                    } else if (typeof service.information === 'object') {
                        // Fallback for object without markdown property (stringify it?)
                        // better to just ignore or start empty to avoid [object Object]
                        console.warn('Unknown information format:', service.information)
                    }

                    if (infoString) {
                        setMarkdown(infoString)

                        // Try to parse out the profile fields from the markdown string
                        const industryMatch = infoString.match(/\*\*Industry\*\*:\s*(.*)/)
                        if (industryMatch && industryMatch[1]) setIndustry(industryMatch[1].trim())

                        const toneMatch = infoString.match(/\*\*Tone of Voice\*\*:\s*(.*)/)
                        if (toneMatch && toneMatch[1]) setToneOfVoice(toneMatch[1].trim())

                        const productsMatch = infoString.split('**Products & Services**:')[1]
                        if (productsMatch) {
                            const content = productsMatch.split('**')[0]
                            setProductsServices(content.trim())
                        }

                        const sigMatch = infoString.match(/`{3}\n([\s\S]*?)\n`{3}/)
                        if (sigMatch && sigMatch[1]) setSignature(sigMatch[1].trim())
                    }
                }
            } catch (error) {
                console.error('Failed to fetch profile:', error)
                toast.error('Failed to load existing profile')
            } finally {
                setIsLoading(false)
            }
        }

        fetchProfile()
    }, [currentSubscription])

    const handleSave = async () => {
        setIsSaving(true)
        try {
            if (!currentSubscription?.subscription_id) {
                throw new Error('No subscription')
            }

            // We need the email to save
            const serviceData = await backendService.getSubscriptionService(currentSubscription.subscription_id)
            const service = Array.isArray(serviceData) ? serviceData[0] : serviceData

            if (!service?.email) {
                throw new Error('No service email found')
            }

            // Format data as Markdown
            let newMarkdown = markdown

            // Clean up previous profile section if it exists (basic implementation)
            const profileHeader = '\n\n## Business Profile'
            if (newMarkdown.includes(profileHeader)) {
                newMarkdown = newMarkdown.split(profileHeader)[0]
            }

            const profileSection = `\n\n## Business Profile
**Industry**: ${industry}
**Products & Services**:
${productsServices}

**Tone of Voice**: ${toneOfVoice}

**Email Signature**:
\`\`\`
${signature}
\`\`\`
`
            const finalMarkdown = newMarkdown + profileSection

            // Use the new updateInformation endpoint directly
            await backendService.updateInformation(service.email, finalMarkdown, currentSubscription.subscription_id)

            // markStepComplete('profile')
            markSubscriptionConfigured()

            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            })

            toast.success('Setup complete!')
            setTimeout(() => {
                router.push('/dashboard')
            }, 1500)
        } catch (error) {
            console.error('Failed to save profile:', error)
            toast.error('Failed to save profile')
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">Business Profile</h2>
                <p className="text-muted-foreground text-sm">
                    Refine your company details for better AI responses
                </p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">Company Details</CardTitle>
                    <CardDescription>
                        These details help Corretto generate more accurate emails.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">

                    {/* Industry */}
                    <div className="space-y-2">
                        <Label htmlFor="industry">Industry</Label>
                        <Select value={industry} onValueChange={setIndustry}>
                            <SelectTrigger id="industry">
                                <SelectValue placeholder="Select your industry" />
                            </SelectTrigger>
                            <SelectContent>
                                {INDUSTRIES.map((ind) => (
                                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Products / Services */}
                    <div className="space-y-2">
                        <Label htmlFor="products">Products & Services</Label>
                        <Textarea
                            id="products"
                            placeholder="List your main products or services..."
                            value={productsServices}
                            onChange={(e) => setProductsServices(e.target.value)}
                            className="min-h-[100px]"
                        />
                        <p className="text-xs text-muted-foreground">
                            Tip: Enter this as a bullet list or comma-separated values.
                        </p>
                    </div>

                    {/* Tone of Voice */}
                    <div className="space-y-2">
                        <Label htmlFor="tone">Tone of Voice</Label>
                        <Select value={toneOfVoice} onValueChange={setToneOfVoice}>
                            <SelectTrigger id="tone">
                                <SelectValue placeholder="Select tone of voice" />
                            </SelectTrigger>
                            <SelectContent>
                                {TONES_OF_VOICE.map((tone) => (
                                    <SelectItem key={tone} value={tone}>{tone}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Signature */}
                    <div className="space-y-2">
                        <Label htmlFor="signature">Email Signature</Label>
                        <Textarea
                            id="signature"
                            placeholder="Best regards,&#10;[Name]&#10;[Company]"
                            value={signature}
                            onChange={(e) => setSignature(e.target.value)}
                            className="min-h-[100px] font-mono text-sm"
                        />
                    </div>

                    <div className="pt-4 flex justify-end">
                        <Button
                            onClick={handleSave}
                            disabled={isSaving}
                            size="lg"
                            className="min-w-[150px]"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Check className="mr-2 h-4 w-4" />
                                    Save & Finish
                                </>
                            )}
                        </Button>
                    </div>

                </CardContent>
            </Card>
        </div>
    )
}
