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
  const popupRadius = radius === 'xl' ? '' : ''
  const itemRadius = radius === 'xl' ? '' : ''

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
          'inline-flex w-full min-w-0 items-center justify-between gap-2 border border-line bg-surface px-3 py-2.5 text-left text-[14px] font-medium normal-case tracking-normal text-ink outline-none transition hover:border-accent-line focus-visible:border-accent focus-visible:ring-4 focus-visible:ring-line-soft data-popup-open:border-accent data-popup-open:ring-4 data-popup-open:ring-line-soft disabled:opacity-60',
          radius === 'xl' ? '' : '',
          className,
        )}
      >
        <BaseSelect.Value className="min-w-0 truncate" />
        <BaseSelect.Icon className="flex shrink-0 text-muted transition-transform data-popup-open:rotate-180">
          <ChevronDown className="size-4" />
        </BaseSelect.Icon>
      </BaseSelect.Trigger>
      <BaseSelect.Portal>
        <BaseSelect.Positioner className="z-50 outline-none" sideOffset={6} alignItemWithTrigger={false}>
          <BaseSelect.Popup
            className={cn(
              'w-[var(--anchor-width)] origin-[var(--transform-origin)] overflow-hidden border border-line bg-surface p-1 shadow-[0_10px_30px_rgba(43,55,51,0.14)] outline-none',
              popupRadius,
            )}
          >
            <BaseSelect.List className="flex flex-col gap-0.5">
              {options.map((option) => (
                <BaseSelect.Item
                  key={option.value}
                  value={option.value}
                  className={cn(
                    'flex min-h-9 cursor-default items-center px-3 text-[14px] text-ink outline-none select-none data-highlighted:bg-accent-soft data-highlighted:text-accent-dark data-selected:font-semibold data-selected:text-accent-dark',
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
