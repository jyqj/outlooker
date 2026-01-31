import { createContext, useContext, useEffect, useState, useCallback } from "react"

export type Theme = "dark" | "light" | "system"

type ThemeProviderProps = {
    children: React.ReactNode
    defaultTheme?: Theme
    storageKey?: string
}

type ThemeProviderState = {
    theme: Theme
    resolvedTheme: "light" | "dark"
    setTheme: (theme: Theme) => void
}

const getSystemTheme = (): "light" | "dark" => {
    if (typeof window === "undefined") return "light"
    return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
}

const initialState: ThemeProviderState = {
    theme: "system",
    resolvedTheme: "light",
    setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
    children,
    defaultTheme = "system",
    storageKey = "vite-ui-theme",
}: ThemeProviderProps) {
    const [theme, setThemeState] = useState<Theme>(
        () => (localStorage.getItem(storageKey) as Theme) || defaultTheme
    )
    const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">(() => {
        const storedTheme = localStorage.getItem(storageKey) as Theme
        const currentTheme = storedTheme || defaultTheme
        return currentTheme === "system" ? getSystemTheme() : currentTheme
    })

    const applyTheme = useCallback((newTheme: "light" | "dark") => {
        const root = window.document.documentElement
        
        // Add transitioning class for smooth theme switch animation
        root.classList.add("theme-transitioning")
        
        root.classList.remove("light", "dark")
        root.classList.add(newTheme)
        setResolvedTheme(newTheme)
        
        // Remove transitioning class after animation completes
        const timer = setTimeout(() => {
            root.classList.remove("theme-transitioning")
        }, 200)
        
        return () => clearTimeout(timer)
    }, [])

    useEffect(() => {
        if (theme === "system") {
            const systemTheme = getSystemTheme()
            const cleanup = applyTheme(systemTheme)

            // Listen for system theme changes
            const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
            let themeCleanup: (() => void) | undefined
            const handleChange = (e: MediaQueryListEvent) => {
                themeCleanup?.()
                themeCleanup = applyTheme(e.matches ? "dark" : "light")
            }

            mediaQuery.addEventListener("change", handleChange)
            return () => {
                cleanup()
                themeCleanup?.()
                mediaQuery.removeEventListener("change", handleChange)
            }
        }

        const cleanup = applyTheme(theme)
        return cleanup
    }, [theme, applyTheme])

    const setTheme = useCallback((newTheme: Theme) => {
        localStorage.setItem(storageKey, newTheme)
        setThemeState(newTheme)
    }, [storageKey])

    const value = {
        theme,
        resolvedTheme,
        setTheme,
    }

    return (
        <ThemeProviderContext.Provider value={value}>
            {children}
        </ThemeProviderContext.Provider>
    )
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}
