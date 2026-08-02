import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const MONTH_NAMES: Record<string, string> = {
  "01": "January", "02": "February", "03": "March",
  "04": "April", "05": "May", "06": "June",
  "07": "July", "08": "August", "09": "September",
  "10": "October", "11": "November", "12": "December",
}

export function formatMonthYear(monthYear: string): string {
  const parts = monthYear.split("-")
  if (parts.length !== 2) return monthYear
  const [year, month] = parts
  const monthName = MONTH_NAMES[month] || month
  return `${monthName} ${year}`
}

const STATE_NAMES: Record<string, string> = {
  "AC": "Acre",
  "AL": "Alagoas",
  "AP": "Amapá",
  "AM": "Amazonas",
  "BA": "Bahia",
  "CE": "Ceará",
  "DF": "Distrito Federal",
  "ES": "Espírito Santo",
  "GO": "Goiás",
  "MA": "Maranhão",
  "MT": "Mato Grosso",
  "MS": "Mato Grosso do Sul",
  "MG": "Minas Gerais",
  "PA": "Pará",
  "PB": "Paraíba",
  "PR": "Paraná",
  "PE": "Pernambuco",
  "PI": "Piauí",
  "RJ": "Rio de Janeiro",
  "RN": "Rio Grande do Norte",
  "RS": "Rio Grande do Sul",
  "RO": "Rondônia",
  "RR": "Roraima",
  "SC": "Santa Catarina",
  "SP": "São Paulo",
  "SE": "Sergipe",
  "TO": "Tocantins",
}

export function formatStateName(code: string): string {
  return STATE_NAMES[code] || code
}

const SEGMENT_LABELS: Record<string, string> = {
  new: "New Customers",
  repeat: "Repeat Buyers",
  vip: "VIP (High LTV)",
}

export function formatCategoryName(cat: string): string {
  return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

export function getMonthLabel(value: string | null, allLabel = "All Time"): string {
  if (!value || value === "all" || value === "all_time") return allLabel
  return formatMonthYear(value)
}

export function getStateLabel(value: string | null, allLabel = "All States"): string {
  if (!value || value === "all") return allLabel
  return `${formatStateName(value)} (${value})`
}

export function getCategoryLabel(value: string | null, allLabel = "All Categories"): string {
  if (!value || value === "all") return allLabel
  return formatCategoryName(value)
}

export function getSegmentLabel(value: string | null, allLabel = "All Segments"): string {
  if (!value || value === "all") return allLabel
  return SEGMENT_LABELS[value] || value
}

/**
 * Format a number as Brazilian Real (BRL) currency.
 * Uses the `R$` prefix with proper locale formatting.
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "R$ 0,00"
  return `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * Format a number as a compact currency string (e.g. R$ 1,5M, R$ 500k).
 */
export function formatCurrencyCompact(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "R$ 0"
  if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })}M`
  if (value >= 1_000) return `R$ ${(value / 1_000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}k`
  return `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/**
 * Format a number with locale-aware separators (e.g. 1.234, 1.234.567).
 */
export function formatNumber(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "0"
  return value.toLocaleString("pt-BR")
}
