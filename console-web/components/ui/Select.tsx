'use client'

import { Select as BaseSelect } from '@base-ui/react/select'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectOption<T extends string> {
  value: T
  label: string
}

/**
 * Custom select so the menu can match the trigger radius. Native <select>
 * paints a square OS popup that we cannot style.
 */
export function Select<T extends string>({
  value,
  onChange,
  options,
  'aria-label': ariaLabel,
  className,
  disabled,
  radius = 'lg',
}: {
  value: T
  onChange: (value: T) => void
  options: ReadonlyArray<SelectOption<T>>
  'aria-label'?: string
  className?: string
  disabled?: boolean
  radius?: 'lg' | 'xl'
}) {
  // `radius` se conserva por compatibilidad de la API; el diseño usa un solo radio corto.
  void radius
  const popupRadius = 'rounded-[var(--radius-ui)]'
  const itemRadius = 'rounded-[var(--radius-ui)]'

  return (
    <BaseSelect.Root
      value={value}
      onValueChange={(next) => {
        if (next == null) return
        onChange(next as T)
      }}
      items={options}
      disabled={disabled}
      modal={false}
    >
      <BaseSelect.Trigger
        aria-label={ariaLabel}
        className={cn(
          'inline-flex h-9 w-full min-w-0 items-center justify-between gap-2 rounded-[var(--radius-ui)] border border-line bg-surface px-2.5 text-left text-[13px] font-normal normal-case tracking-normal text-ink outline-none transition hover:border-faint focus-visible:border-accent data-popup-open:border-accent disabled:opacity-60',
          className,
        )}
      >
        <BaseSelect.Value className="min-w-0 truncate" />
        <BaseSelect.Icon className="flex shrink-0 text-faint transition-transform data-popup-open:rotate-180">
          <ChevronDown className="size-3.5" />
        </BaseSelect.Icon>
      </BaseSelect.Trigger>
      <BaseSelect.Portal>
        <BaseSelect.Positioner className="z-50 outline-none" sideOffset={6} alignItemWithTrigger={false}>
          <BaseSelect.Popup
            className={cn(
              'w-[var(--anchor-width)] origin-[var(--transform-origin)] overflow-hidden border border-line bg-surface p-1 outline-none',
              popupRadius,
            )}
          >
            <BaseSelect.List className="flex flex-col gap-0.5">
              {options.map((option) => (
                <BaseSelect.Item
                  key={option.value}
                  value={option.value}
                  className={cn(
                    'flex min-h-8 cursor-default items-center px-2.5 text-[13px] text-ink outline-none select-none data-highlighted:bg-raised data-selected:font-semibold',
                    itemRadius,
                  )}
                >
                  <BaseSelect.ItemText>{option.label}</BaseSelect.ItemText>
                </BaseSelect.Item>
              ))}
            </BaseSelect.List>
          </BaseSelect.Popup>
        </BaseSelect.Positioner>
      </BaseSelect.Portal>
    </BaseSelect.Root>
  )
}
