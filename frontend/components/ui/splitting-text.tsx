"use client"

import { motion } from "motion/react"

interface SplittingTextProps {
    text: string
    className?: string
    delay?: number
    type?: "chars" | "words"
    motionVariants?: any
}

export function SplittingText({
    text,
    className,
    delay = 0,
    type = "chars",
    motionVariants,
}: SplittingTextProps) {
    const items = type === "chars" ? text.split("") : text.split(" ")

    const container = {
        hidden: { opacity: 0 },
        visible: (i = 1) => ({
            opacity: 1,
            transition: { staggerChildren: 0.05, delayChildren: delay / 1000 * i },
        }),
    }

    const defaultChild = {
        visible: {
            opacity: 1,
            x: 0,
            y: 0,
            transition: {
                type: "spring",
                damping: 12,
                stiffness: 100,
            },
        },
        hidden: {
            opacity: 0,
            x: -20,
            y: 10,
            transition: {
                type: "spring",
                damping: 12,
                stiffness: 100,
            },
        },
    }

    return (
        <motion.div
            style={{ overflow: "hidden", display: "flex", flexWrap: "wrap", justifyContent: "center" }}
            variants={container}
            initial="hidden"
            animate="visible"
            className={className}
        >
            {items.map((item, index) => (
                <motion.span
                    variants={motionVariants || defaultChild}
                    style={{ marginRight: type === "words" ? "0.25em" : "0px" }}
                    key={index}
                >
                    {item === " " ? "\u00A0" : item}
                </motion.span>
            ))}
        </motion.div>
    )
}
