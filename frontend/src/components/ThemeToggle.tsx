import { Moon, Sun, Monitor } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { useTheme, type Theme } from "@/components/ThemeProvider"

const themeOrder: Theme[] = ["light", "dark", "system"]

const getNextTheme = (current: Theme): Theme => {
    const currentIndex = themeOrder.indexOf(current)
    return themeOrder[(currentIndex + 1) % themeOrder.length]
}

const getIcon = (theme: Theme) => {
    switch (theme) {
        case "light":
            return Sun
        case "dark":
            return Moon
        case "system":
            return Monitor
    }
}

const getLabel = (theme: Theme): string => {
    switch (theme) {
        case "light":
            return "浅色模式"
        case "dark":
            return "深色模式"
        case "system":
            return "跟随系统"
    }
}

export function ThemeToggle() {
    const { setTheme, theme } = useTheme()
    const Icon = getIcon(theme)
    const label = getLabel(theme)
    const nextTheme = getNextTheme(theme)
    const nextLabel = getLabel(nextTheme)

    return (
        <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(nextTheme)}
            className="rounded-full w-9 h-9"
            title={`${label} - 点击切换至${nextLabel}`}
            aria-label={`当前: ${label}, 点击切换至${nextLabel}`}
        >
            <Icon className="h-[1.2rem] w-[1.2rem] transition-all" />
            <span className="sr-only">{label}</span>
        </Button>
    )
}
